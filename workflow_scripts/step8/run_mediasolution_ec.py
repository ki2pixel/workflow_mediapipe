#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Étape 8 — Media Solution (EffectCraft).

Génère les projets EffectCraft `<video>_9x16.ecproj` en pilotant le panel
`scripts/MediaSolution-EC/MediaSolution.jsx` en headless via `effectcraft-cli script`.

- Source des dossiers : manifeste `logs/step7/finalized_projects_*.json` écrit par l'étape 7
  (dossiers publiés par le run courant), ou l'option `--folder` pour un usage manuel.
- Mode « Tout exécuter » uniquement : un seul appel `runBatch(..., maxUnits=0)` synchrone traite
  tous les dossiers d'affilée (le mode « Pas-à-pas » du panel est réservé à l'UI interactive).
- Les lignes du panel sont relayées telles quelles vers stdout et doublées de lignes normalisées
  `MS_BATCH_*` lues par le parseur de progression du backend (workflow_executor).
"""

import argparse
import json
import logging
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import config  # noqa: E402

LOG_DIR = ROOT_DIR / "logs" / "step8"
DRIVERS_DIR = LOG_DIR / "drivers"
STEP7_LOG_DIR = ROOT_DIR / "logs" / "step7"
MANIFEST_GLOB = "finalized_projects_*.json"

DEFAULT_PANEL_JSX = ROOT_DIR / "scripts" / "MediaSolution-EC" / "MediaSolution.jsx"
INSTALLED_PANEL_JSX = Path.home() / ".config" / "effectcraft" / "Scripts" / "ScriptUI Panels" / "MediaSolution.jsx"

MAX_DRIVERS_KEPT = 10
DEFAULT_BRIDGE_PORT = 9877

RE_TOTAL = re.compile(r"Batch démarré\s*:\s*(\d+)\s+projet\(s\)")
RE_PROGRESS = re.compile(r"---\s*(\d+)/(\d+)\s*:\s*(.+?)\s*$")
RE_SAVED = re.compile(r"Projet enregistré\s*:\s*(.+?)\s*\(")
RE_UNIT_ERROR = re.compile(r"Erreur sur\s+(.+?)\s*:")
RE_BATCH_END = re.compile(r"Batch terminé\s*:\s*(.+?)\s*$")
RE_RESULT = re.compile(r"MS_BATCH_RESULT:\s*(\{.*\})\s*$")


def setup_logging() -> Path:
    """Configure le logger (fichier horodaté dans logs/step8 + stdout du process)."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"mediasolution_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return log_file


def latest_manifest(log_dir: Optional[Path] = None) -> Optional[Path]:
    """Retourne le manifeste de l'étape 7 le plus récent (mtime), ou None."""
    log_dir = log_dir or STEP7_LOG_DIR
    if not log_dir.is_dir():
        return None
    candidates = [p for p in log_dir.glob(MANIFEST_GLOB) if p.is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def load_manifest(path: Path) -> Dict:
    """Charge et valide le manifeste écrit par l'étape 7."""
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Manifeste invalide (objet JSON attendu) : {path}")
    return data


def manifest_project_count(manifest: Optional[Dict]) -> int:
    """Nombre de projets listés dans le manifeste."""
    if not manifest:
        return 0
    projects = manifest.get("projects")
    return len(projects) if isinstance(projects, list) else 0


def select_folders(
    manifest: Optional[Dict],
    manual_folders: List[str],
    docs_subfolder: str,
) -> List[str]:
    """Détermine les dossiers projet à traiter (manifeste ou --folder), avec validation."""
    candidates: List[Path] = []
    if manual_folders:
        candidates = [Path(p).expanduser() for p in manual_folders]
    elif manifest:
        for entry in manifest.get("projects", []):
            if isinstance(entry, dict) and entry.get("path"):
                candidates.append(Path(entry["path"]))

    folders: List[str] = []
    seen = set()
    for candidate in candidates:
        if not candidate.is_dir():
            logging.warning("Dossier ignoré (introuvable) : %s", candidate)
            continue
        if not (candidate / docs_subfolder).is_dir():
            logging.warning("Dossier ignoré (pas de '%s') : %s", docs_subfolder, candidate)
            continue
        resolved = str(candidate.resolve())
        if resolved in seen:
            logging.warning("Dossier ignoré (doublon) : %s", resolved)
            continue
        seen.add(resolved)
        folders.append(resolved)
    return folders


def load_panel_config(config_path: Optional[Path]) -> Tuple[Optional[str], str]:
    """Lit le fichier de configuration du panel (JSON), retourne (contenu JSON, docsSubFolderName)."""
    if config_path is None or not config_path.is_file():
        return None, "docs"
    try:
        with config_path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logging.warning("Config panel illisible '%s' (%s) — valeurs par défaut du script.", config_path, exc)
        return None, "docs"
    docs_subfolder = data.get("docsSubFolderName") or "docs"
    logging.info("Config panel chargée : %s", config_path)
    return json.dumps(data, ensure_ascii=False), str(docs_subfolder)


def resolve_panel_jsx(candidate: Optional[str]) -> Optional[Path]:
    """Résout le chemin du panel MediaSolution.jsx (dépôt, puis copie installée)."""
    for path in (candidate, str(DEFAULT_PANEL_JSX), str(INSTALLED_PANEL_JSX)):
        if path:
            resolved = Path(path).expanduser()
            if resolved.is_file():
                return resolved
    return None


def resolve_cli(candidate: str) -> Optional[str]:
    """Résout l'exécutable effectcraft-cli (nom dans le PATH ou chemin explicite)."""
    if not candidate:
        return None
    path = Path(candidate).expanduser()
    if path.is_absolute() or os.sep in candidate:
        return str(path) if path.is_file() else None
    return shutil.which(candidate)


def cli_version(cli_path: str) -> Optional[str]:
    """`effectcraft-cli --version` → version ('0.8.0'), ou None si indéterminable."""
    try:
        completed = subprocess.run(
            [cli_path, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"\d+\.\d+(?:\.\d+)?", completed.stdout or "")
    return match.group(0) if match else None


def version_tuple(version: str) -> Tuple[int, ...]:
    """'0.8.1' → (0, 8, 1) ; '0.7' → (0, 7, 0)."""
    numbers = [int(part) for part in re.findall(r"\d+", version)]
    return tuple((numbers + [0, 0, 0])[:3])


def headless_scripts_blocked(version: Optional[str]) -> bool:
    """0.8.0 interdit à un script de s'octroyer la permission d'écriture : le headless pur est bloqué."""
    return version is not None and version_tuple(version) >= (0, 8, 0)


def resolve_execution_mode(forced: str, cli_path: str) -> Tuple[str, Optional[str]]:
    """Retourne (mode d'exécution, version du CLI) ; mode ∈ {'headless', 'bridge'}."""
    version = cli_version(cli_path)
    forced_mode = (forced or "auto").strip().lower()
    if forced_mode in ("headless", "bridge"):
        return forced_mode, version
    if headless_scripts_blocked(version):
        return "bridge", version
    return "headless", version


def bridge_port_open(port: int, timeout: float = 2.0) -> bool:
    """Vrai si une instance EffectCraft écoute sur 127.0.0.1:<port>."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return True
    except OSError:
        return False


def activate_scripting_preference(cli_path: str, bridge_port: int) -> bool:
    """Active Allow Scripts to Write Files dans l'app ouverte (commande hors contexte script)."""
    payload = json.dumps({"key": "scripting.allowScriptsWriteFiles", "value": True})
    try:
        completed = subprocess.run(
            [cli_path, "exec", "prefs.set", "--params", payload, "--bridge", str(bridge_port)],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logging.warning("Pré-vol bridge (prefs.set) impossible : %s", exc)
        return False
    if completed.returncode != 0:
        logging.warning(
            "Pré-vol bridge (prefs.set) refusé (code %s) : %s",
            completed.returncode,
            (completed.stderr or completed.stdout or "").strip(),
        )
        return False
    logging.info("Pré-vol bridge : scripting.allowScriptsWriteFiles activé dans l'application.")
    return True


def launch_app(app_path: str, bridge_port: int, log_path: Path, timeout: float = 60.0) -> bool:
    """Lance l'application avec son control channel et attend qu'elle réponde.

    L'application est détachée du wrapper : elle reste ouverte après le batch (retouche manuelle).
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        log_file = open(log_path, "w", encoding="utf-8")
    except OSError as exc:
        logging.warning("Log de lancement indisponible (%s) : %s", log_path, exc)
        log_file = None
    try:
        process = subprocess.Popen(
            [app_path, "--control", str(bridge_port), "--empty"],
            stdout=log_file or subprocess.DEVNULL,
            stderr=subprocess.STDOUT if log_file else subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        logging.error("Lancement d'EffectCraft impossible : %s", exc)
        if log_file:
            log_file.close()
        return False
    if log_file:
        log_file.close()

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if bridge_port_open(bridge_port, timeout=1.0):
            logging.info("Application EffectCraft prête (control channel sur 127.0.0.1:%s).", bridge_port)
            return True
        if process.poll() is not None:
            logging.error(
                "EffectCraft s'est arrêté au démarrage (code %s). Voir %s.",
                process.returncode,
                log_path,
            )
            return False
        time.sleep(0.5)
    logging.error(
        "EffectCraft n'a pas ouvert son control channel sur 127.0.0.1:%s après %.0f s. Voir %s.",
        bridge_port,
        timeout,
        log_path,
    )
    return False


def build_driver_js(panel_js: str, folders: List[str], config_json: Optional[str]) -> str:
    """Concatène le panel et un driver headless (les scripts EffectCraft ne s'incluent pas entre eux)."""
    lines = [
        panel_js.rstrip(),
        "",
        "// ---------------------------------------------------------------------------",
        "// Driver headless généré par l'étape 8 du workflow (mode « Tout exécuter »).",
        "// ---------------------------------------------------------------------------",
        'app.run("prefs.set", { key: "scripting.allowScriptsWriteFiles", value: true });',
        "",
    ]
    if config_json:
        lines.append(f"mediasolutionEC.applyConfig({json.dumps(config_json)});")
        lines.append("")
    lines.extend(
        [
            f"var MS_FOLDERS = {json.dumps(folders)};",
            'var msResult = JSON.parse(mediasolutionEC.runBatch(JSON.stringify(MS_FOLDERS), null, 0));',
            'writeLn("MS_BATCH_RESULT: " + JSON.stringify(msResult));',
            'if (!msResult.ok || (msResult.errors && msResult.errors.length > 0)) {',
            '  throw new Error("Batch Media Solution en échec");',
            '}',
            '"step8-ok";',
        ]
    )
    return "\n".join(lines) + "\n"


def parse_panel_line(line: str) -> List[str]:
    """Traduit une ligne du panel en lignes normalisées MS_BATCH_* (0..n) pour le backend."""
    emitted: List[str] = []

    match = RE_TOTAL.search(line)
    if match:
        emitted.append(f"MS_BATCH_TOTAL: {match.group(1)}")

    match = RE_PROGRESS.search(line)
    if match:
        emitted.append(f"MS_BATCH_PROGRESS: {match.group(1)}/{match.group(2)} - {match.group(3)}")

    match = RE_SAVED.search(line)
    if match:
        emitted.append(f"MS_BATCH_OK: {match.group(1)}")

    match = RE_UNIT_ERROR.search(line)
    if match:
        emitted.append(f"MS_BATCH_FAIL: {match.group(1)}")

    match = RE_BATCH_END.search(line)
    if match:
        emitted.append(f"MS_BATCH_END: {match.group(1)}")

    return emitted


def evaluate_result(result: Optional[Dict]) -> bool:
    """Détermine le succès du batch à partir du résultat MS_BATCH_RESULT."""
    return bool(
        result is not None
        and result.get("ok") is True
        and not result.get("errors")
    )


def run_cli(
    cli_path: str,
    driver_path: Path,
    cwd: Path,
    mode: str = "headless",
    bridge_port: Optional[int] = None,
) -> Tuple[int, Optional[Dict]]:
    """Exécute `effectcraft-cli script <driver>` (headless ou via l'app, `--bridge`), relaie chaque ligne et capture MS_BATCH_RESULT.

    SIGTERM/SIGINT (bouton « Annuler ») terminent d'abord le process EffectCraft enfant.
    """
    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    env["TERM"] = "dumb"

    command = [cli_path, "script", str(driver_path)]
    if mode == "bridge":
        command += ["--bridge", str(bridge_port)]

    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=env,
    )

    def _forward_signal(signum, _frame):
        logging.warning("Signal %s reçu — arrêt du batch EffectCraft en cours...", signum)
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        sys.exit(143)

    previous_term = signal.signal(signal.SIGTERM, _forward_signal)
    previous_int = signal.signal(signal.SIGINT, _forward_signal)

    result: Optional[Dict] = None
    try:
        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.rstrip("\n")
            print(line, flush=True)
            for normalized in parse_panel_line(line):
                print(normalized, flush=True)
            match = RE_RESULT.search(line)
            if match:
                try:
                    result = json.loads(match.group(1))
                except json.JSONDecodeError:
                    logging.error("Ligne MS_BATCH_RESULT illisible : %s", line)
    finally:
        signal.signal(signal.SIGTERM, previous_term)
        signal.signal(signal.SIGINT, previous_int)
        return_code = process.wait()

    return return_code, result


def cleanup_drivers(drivers_dir: Path, keep: int = MAX_DRIVERS_KEPT) -> None:
    """Ne conserve que les `keep` drivers les plus récents."""
    try:
        drivers = sorted(
            (p for p in drivers_dir.glob("step8_driver_*.jsx") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for stale in drivers[keep:]:
            stale.unlink(missing_ok=True)
    except OSError as exc:
        logging.warning("Nettoyage des drivers impossible : %s", exc)


def write_report(report: Dict, log_dir: Path = LOG_DIR) -> Path:
    """Écrit le rapport JSON du run (écriture atomique)."""
    log_dir.mkdir(parents=True, exist_ok=True)
    report_path = log_dir / f"step8_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    tmp_path = report_path.with_suffix(".json.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    os.replace(tmp_path, report_path)
    return report_path


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Étape 8 — Media Solution (EffectCraft) : génère les projets <video>_9x16.ecproj."
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default=None,
        help="Manifeste de l'étape 7 (défaut : logs/step7/finalized_projects_*.json le plus récent).",
    )
    parser.add_argument(
        "--folder",
        action="append",
        default=[],
        dest="folders",
        help="Dossier projet à traiter (répétable ; court-circuite le manifeste).",
    )
    parser.add_argument(
        "--cli",
        type=str,
        default=None,
        help="Exécutable effectcraft-cli (défaut : config STEP8_EFFECTCRAFT_CLI).",
    )
    parser.add_argument(
        "--panel-jsx",
        type=str,
        default=None,
        help="Chemin du panel MediaSolution.jsx (défaut : version du dépôt).",
    )
    parser.add_argument(
        "--config-json",
        type=str,
        default=None,
        help="Fichier mediasolution_ec.json (défaut : <output_dir du manifeste>/mediasolution_ec.json).",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "headless", "bridge"],
        default=None,
        help="Mode d'exécution : auto (défaut), headless (0.7.0) ou bridge (app ouverte, 0.8.0+).",
    )
    parser.add_argument(
        "--bridge-port",
        type=int,
        default=None,
        help="Port du control channel de l'application (défaut : config STEP8_BRIDGE_PORT ou 9877).",
    )
    parser.add_argument(
        "--no-launch-app",
        action="store_true",
        help="En mode bridge, ne pas lancer l'application absente (erreur explicite à la place).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche dossiers, config et driver généré sans exécuter EffectCraft.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    log_file = setup_logging()
    started_at = time.time()

    logging.info("--- Démarrage de l'étape 8 : Media Solution (EffectCraft) ---")
    logging.info("Log : %s", log_file)

    manifest_path: Optional[Path] = None
    manifest: Optional[Dict] = None
    if args.folders:
        if args.manifest:
            manifest_path = Path(args.manifest).expanduser()
    else:
        manifest_path = Path(args.manifest).expanduser() if args.manifest else latest_manifest()
        if manifest_path is None:
            logging.error(
                "Aucun manifeste de l'étape 7 trouvé dans '%s' "
                "(lancez d'abord l'étape 7, ou passez --folder).",
                STEP7_LOG_DIR,
            )
            return 1
        if not manifest_path.is_file():
            logging.error("Manifeste introuvable : %s", manifest_path)
            return 1

    if manifest_path is not None and manifest_path.is_file():
        try:
            manifest = load_manifest(manifest_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            logging.error("Manifeste illisible '%s' : %s", manifest_path, exc)
            return 1
        logging.info(
            "Manifeste : %s (%d projet(s), output_dir=%s)",
            manifest_path,
            manifest_project_count(manifest),
            manifest.get("output_dir", "?"),
        )

    config_path: Optional[Path] = None
    if args.config_json:
        config_path = Path(args.config_json).expanduser()
    elif getattr(config, "STEP8_PANEL_CONFIG", ""):
        config_path = Path(config.STEP8_PANEL_CONFIG).expanduser()
    elif manifest and manifest.get("output_dir"):
        candidate = Path(manifest["output_dir"]) / "mediasolution_ec.json"
        if candidate.is_file():
            config_path = candidate
    config_json, docs_subfolder = load_panel_config(config_path)
    if config_json is None:
        docs_subfolder = "docs"

    candidate_count = len(args.folders) if args.folders else manifest_project_count(manifest)
    folders = select_folders(manifest, args.folders, docs_subfolder)
    if not folders:
        if candidate_count == 0:
            logging.info("Aucun projet à traiter. Fin du script.")
            return 0
        logging.error("Aucun dossier exploitable parmi les %d projet(s) listés.", candidate_count)
        return 1

    panel_jsx = resolve_panel_jsx(args.panel_jsx or getattr(config, "STEP8_PANEL_JSX", "") or None)
    if panel_jsx is None:
        logging.error("Panel MediaSolution.jsx introuvable (dépôt et copie installée).")
        return 1

    cli_candidate = args.cli or getattr(config, "STEP8_EFFECTCRAFT_CLI", "effectcraft-cli")
    cli_path = resolve_cli(cli_candidate)
    if cli_path is None:
        logging.error("Exécutable EffectCraft introuvable : %s", cli_candidate)
        return 1

    forced_mode = args.mode or getattr(config, "STEP8_MODE", "auto")
    bridge_port = args.bridge_port or getattr(config, "STEP8_BRIDGE_PORT", DEFAULT_BRIDGE_PORT)
    execution_mode, cli_version_detected = resolve_execution_mode(forced_mode, cli_path)
    logging.info(
        "Mode d'exécution : %s (effectcraft-cli %s)",
        execution_mode,
        cli_version_detected or "version inconnue",
    )

    logging.info("%d dossier(s) à traiter :", len(folders))
    for folder in folders:
        logging.info("  - %s", folder)
    logging.info("Panel : %s", panel_jsx)
    logging.info("CLI   : %s", cli_path)

    DRIVERS_DIR.mkdir(parents=True, exist_ok=True)
    driver_path = DRIVERS_DIR / f"step8_driver_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsx"
    driver_path.write_text(
        build_driver_js(panel_jsx.read_text(encoding="utf-8"), folders, config_json),
        encoding="utf-8",
    )
    logging.info("Driver généré : %s", driver_path)

    if args.dry_run:
        logging.info("--dry-run : exécution EffectCraft ignorée.")
        print(f"MS_BATCH_TOTAL: {len(folders)}")
        for index, folder in enumerate(folders, start=1):
            print(f"MS_BATCH_PROGRESS: {index}/{len(folders)} - {Path(folder).name}")
        return 0

    app_launched = False
    if execution_mode == "bridge":
        if not bridge_port_open(bridge_port):
            auto_launch = (not args.no_launch_app) and getattr(config, "STEP8_AUTO_LAUNCH_APP", True)
            if not auto_launch:
                logging.error(
                    "EffectCraft n'écoute pas sur 127.0.0.1:%s. Lancez l'application avec "
                    "`effectcraft --control %s` (préférence « Allow Scripts to Write Files » active), "
                    "puis relancez l'étape 8.",
                    bridge_port,
                    bridge_port,
                )
                return 1
            app_candidate = getattr(config, "STEP8_EFFECTCRAFT_APP", "effectcraft")
            app_path = resolve_cli(app_candidate)
            if app_path is None:
                logging.error("Exécutable de l'application EffectCraft introuvable : %s", app_candidate)
                return 1
            app_launch_timeout = getattr(config, "STEP8_APP_LAUNCH_TIMEOUT", 60)
            logging.info(
                "Aucune instance EffectCraft sur 127.0.0.1:%s : lancement de l'application (%s).",
                bridge_port,
                app_path,
            )
            launch_log = LOG_DIR / f"app_launch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            if not launch_app(app_path, bridge_port, launch_log, timeout=app_launch_timeout):
                return 1
            app_launched = True
        activate_scripting_preference(cli_path, bridge_port)

    return_code, result = run_cli(
        cli_path, driver_path, ROOT_DIR, mode=execution_mode, bridge_port=bridge_port
    )
    duration = time.time() - started_at

    success = evaluate_result(result)
    if result is None:
        logging.error("Aucun résultat MS_BATCH_RESULT reçu du CLI (code %s).", return_code)
    elif not result.get("ok"):
        logging.error("Batch en échec : %s", result.get("error", "erreur inconnue"))
    elif result.get("errors"):
        for error in result["errors"]:
            logging.error("Échec projet : %s", error)
    if success and return_code != 0:
        logging.warning("MS_BATCH_RESULT valide mais code de sortie CLI non nul (%s).", return_code)

    report = {
        "schema": 1,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "manifest": str(manifest_path) if manifest_path else None,
        "output_dir": manifest.get("output_dir") if manifest else None,
        "folders": folders,
        "panel_jsx": str(panel_jsx),
        "cli": cli_path,
        "mode": execution_mode,
        "bridge_port": bridge_port if execution_mode == "bridge" else None,
        "app_launched": app_launched,
        "cli_version": cli_version_detected,
        "driver": str(driver_path),
        "config_json": str(config_path) if config_json and config_path else None,
        "result": result,
        "cli_return_code": return_code,
        "duration_s": round(duration, 2),
        "success": success,
    }
    report_path = write_report(report)
    logging.info("Rapport écrit : %s", report_path)
    logging.info(
        "--- Étape 8 terminée : %s (%.1f s) ---",
        "succès" if success else "échec",
        duration,
    )

    cleanup_drivers(DRIVERS_DIR)
    return 0 if success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        logging.critical("Erreur critique non gérée dans le script Media Solution : %s", exc, exc_info=True)
        sys.exit(1)
