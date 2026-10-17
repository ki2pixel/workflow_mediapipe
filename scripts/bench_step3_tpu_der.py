#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Harnais de benchmark DER/JER de la STEP3 (diarisation audio Coral TPU).

Muxe les WAV VoxConverse en conteneurs sans perte (MKV/PCM), lance
``workflow_scripts/step3/run_audio_diarization_tpu.py`` via ``coral_env`` puis
évalue les JSON produits avec ``bench_step3_der_eval.py`` exécuté dans
``audio_env`` (pyannote.metrics). Les artefacts sont isolés dans
``scratch/bench_step3_der/<horodatage>/`` (rapport Markdown/JSON + timings).

Exemples :
    python3 scripts/fetch_voxconverse_dev.py
    python3 scripts/bench_step3_tpu_der.py --limit 5 --out scratch/bench_step3_der/baseline
    python3 scripts/bench_step3_tpu_der.py --limit 5 --baseline scratch/bench_step3_der/baseline/der_report.json
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORPUS = PROJECT_ROOT / "scratch" / "bench_step3_der" / "voxconverse"
DEFAULT_BENCH_ROOT = PROJECT_ROOT / "scratch" / "bench_step3_der"
STEP3_SCRIPT = PROJECT_ROOT / "workflow_scripts" / "step3" / "run_audio_diarization_tpu.py"
EVAL_SCRIPT = PROJECT_ROOT / "scripts" / "bench_step3_der_eval.py"
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
STAGE_TIMING_PATTERN = re.compile(r"STAGE_TIMING:\s*(\w+)=([0-9.]+)ms(?:\s+video=(\S+))?")
SEGMENT_PATTERN = re.compile(r"VAD:\s*(\d+)\s+segments")
EMBEDDING_PATTERN = re.compile(r"extraction de (\d+) d-vectors")
SUCCESS_PATTERN = re.compile(r"Succès:\s*(.*?)(?:_audio\.json)?\s+créé")


def parse_env_file(path: Path) -> dict:
    values = {}
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return values
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def build_environment(env_file: Path, overrides: dict) -> dict:
    environment = dict(os.environ)
    for key, value in parse_env_file(env_file).items():
        environment.setdefault(key, value)
    environment.update(overrides)
    delegate_dir = PROJECT_ROOT / "tmp_lib" / "usr" / "lib" / "x86_64-linux-gnu"
    if delegate_dir.is_dir():
        existing = environment.get("LD_LIBRARY_PATH", "")
        paths = [str(delegate_dir)] + [item for item in existing.split(":") if item]
        environment["LD_LIBRARY_PATH"] = ":".join(dict.fromkeys(paths))
    return environment


def resolve_coral_python(explicit: str = None) -> Path:
    if explicit:
        return Path(explicit)
    candidate = PROJECT_ROOT / "coral_env" / "bin" / "python"
    return candidate if candidate.exists() else Path(sys.executable)


def resolve_audio_python(env_values: dict, explicit: str = None) -> Path:
    if explicit:
        return Path(explicit)
    candidates = []
    venv_base = env_values.get("VENV_BASE_DIR")
    if venv_base:
        candidates.append(Path(venv_base) / "audio_env" / "bin" / "python")
    candidates.append(Path("/mnt/venv_ext4/audio_env/bin/python"))
    candidates.append(PROJECT_ROOT / "audio_env" / "bin" / "python")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def active_tpu_consumers() -> list:
    consumers = []
    try:
        result = subprocess.run(
            ["pgrep", "-af", "workflow_scripts/step"],
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return consumers
    own_pid = str(os.getpid())
    for line in result.stdout.splitlines():
        if own_pid in line.split()[:1]:
            continue
        if "bench_step3_tpu_der.py" in line:
            continue
        consumers.append(line.strip())
    return consumers


def load_stems_from_clips_file(path: Path) -> list:
    stems = []
    content = path.read_text(encoding="utf-8")
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        stem = Path(line).stem
        if stem not in stems:
            stems.append(stem)
    return stems


def load_stems_from_manifest(path: Path) -> list:
    stems = []
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("clips", data) if isinstance(data, dict) else data
        if isinstance(items, list):
            for item in items:
                if isinstance(item, str):
                    stems.append(Path(item).stem)
                elif isinstance(item, dict):
                    stem = item.get("stem") or item.get("id") or item.get("name") or item.get("video")
                    if stem:
                        stems.append(Path(str(stem)).stem)
    elif path.suffix.lower() in (".csv", ".tsv"):
        import csv
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        with open(path, "r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, delimiter=delimiter)
            for row in reader:
                stem = row.get("stem") or row.get("id") or row.get("name") or row.get("filename") or row.get("video")
                if stem:
                    stems.append(Path(str(stem)).stem)
    return list(dict.fromkeys(stems))


def select_clips(corpus: Path, limit: int = 0, stems_filter: list = None) -> list:
    rttm_dir = corpus / "rttm"
    wav_dir = corpus / "wav"
    available = {}
    for rttm_path in sorted(rttm_dir.glob("*.rttm")):
        wav_path = wav_dir / f"{rttm_path.stem}.wav"
        if wav_path.exists():
            available[rttm_path.stem] = (rttm_path.stem, wav_path, rttm_path)

    if stems_filter is not None:
        clips = []
        for stem in stems_filter:
            if stem in available:
                clips.append(available[stem])
            else:
                print(f"Avertissement: extrait '{stem}' introuvable dans {corpus}", file=sys.stderr)
    else:
        clips = [available[k] for k in sorted(available.keys())]

    return clips[:limit] if limit else clips



def mux_clips(clips: list, clips_dir: Path) -> None:
    clips_dir.mkdir(parents=True, exist_ok=True)
    for stem, wav_path, _ in clips:
        target = clips_dir / f"{stem}.mkv"
        command = [
            "ffmpeg", "-y", "-i", str(wav_path),
            "-vn", "-c:a", "pcm_s16le", str(target),
        ]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  {wav_path.name} -> {target.name}")


def run_step3(clips_dir: Path, run_dir: Path, python_exe: Path, environment: dict,
              script: Path = None) -> tuple:
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "run.log"
    command = [
        str(python_exe), str(script or STEP3_SCRIPT),
        "--log_dir", str(logs_dir),
    ]
    started = time.time()
    with open(log_path, "w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            command, cwd=str(clips_dir), env=environment,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        for line in process.stdout:
            log_file.write(line)
            stripped = line.rstrip("\n")
            if "PROCESSING_VIDEO" in stripped or "Succès" in stripped or "CRITICAL" in stripped:
                print(f"    {stripped}", flush=True)
        return_code = process.wait()
    return return_code, round(time.time() - started, 2), log_path


def collect_outputs(clips_dir: Path, outputs_dir: Path) -> list:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    produced = sorted(clips_dir.glob("*_audio.json"))
    if produced:
        for stale in outputs_dir.glob("*_audio.json"):
            stale.unlink()
        for path in produced:
            shutil.copy2(path, outputs_dir / path.name)
        return [path.name for path in produced]
    return [path.name for path in sorted(outputs_dir.glob("*_audio.json"))]


def parse_run_log(log_path: Path) -> dict:
    stage_totals = {}
    segments = {}
    embeddings = {}
    video_durations = {}
    current_video = None
    current_start = None
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            timestamp = datetime.strptime(line[:23], "%Y-%m-%d %H:%M:%S,%f")
        except ValueError:
            timestamp = None
        if timestamp is not None and "PROCESSING_VIDEO:" in line:
            current_video = line.split("PROCESSING_VIDEO:", 1)[1].strip()
            current_start = timestamp
        elif timestamp is not None and "Succès:" in line and current_video and current_start:
            video_durations[current_video] = round((timestamp - current_start).total_seconds(), 2)
            current_video, current_start = None, None
        match = STAGE_TIMING_PATTERN.search(line)
        if match:
            stage, elapsed_ms, _video = match.groups()
            entry = stage_totals.setdefault(stage, {"count": 0, "total_ms": 0.0})
            entry["count"] += 1
            entry["total_ms"] += float(elapsed_ms)
        match = SEGMENT_PATTERN.search(line)
        if match:
            video = line.split(" - ")[-1].strip() if " - " in line else "?"
            segments[video] = int(match.group(1))
        match = EMBEDDING_PATTERN.search(line)
        if match:
            embeddings["last"] = int(match.group(1))
    for entry in stage_totals.values():
        entry["mean_ms"] = round(entry["total_ms"] / entry["count"], 2) if entry["count"] else None
        entry["total_ms"] = round(entry["total_ms"], 2)
    return {
        "stages": stage_totals,
        "segments": segments,
        "embeddings": embeddings,
        "video_durations": video_durations,
        "total_video_seconds": round(sum(video_durations.values()), 2),
    }


def evaluate(reference_dir: Path, hypothesis_dir: Path, run_dir: Path, python_exe: Path,
             baseline: str = None, require_parity: bool = False,
             clips_file: str = None, manifest: str = None) -> tuple:
    report_path = run_dir / "der_report.json"
    command = [
        str(python_exe), str(EVAL_SCRIPT),
        "--reference-dir", str(reference_dir),
        "--hypothesis-dir", str(hypothesis_dir),
        "--output", str(report_path),
    ]
    if baseline:
        command.extend(["--baseline", str(Path(baseline).resolve())])
    if require_parity:
        command.append("--require-parity")
    if clips_file:
        command.extend(["--clips-file", str(Path(clips_file).resolve())])
    if manifest:
        command.extend(["--manifest", str(Path(manifest).resolve())])
    process = subprocess.run(command, text=True)
    return process.returncode, report_path


def render_markdown(run_meta: dict, timings: dict, der_report: dict) -> str:
    lines = [
        "# Benchmark STEP3 — DER/JER et timings",
        "",
        f"- Corpus : `{run_meta['corpus']}`",
        f"- Extraits : {run_meta['clips_count']} | code retour STEP3 : {run_meta['return_code']}",
        f"- Durée STEP3 : {run_meta['wall_seconds']} s | somme durées vidéo : {timings.get('total_video_seconds', 0)} s",
        f"- Python Coral : `{run_meta['python_coral']}`",
        f"- Python audio : `{run_meta['python_audio']}`",
        "",
        "## Timings par étage",
        "",
        "| étage | count | total ms | moyenne ms |",
        "|---|---|---|---|",
    ]
    for stage, entry in sorted(timings["stages"].items(), key=lambda item: item[1]["total_ms"], reverse=True):
        lines.append(f"| {stage} | {entry['count']} | {entry['total_ms']} | {entry['mean_ms']} |")

    summary = (der_report or {}).get("summary", {})
    video_durations = timings.get("video_durations") or {}
    if video_durations:
        lines += [
            "",
            "## Durée par extrait",
            "",
            "| extrait | durée s |",
            "|---|---|",
        ]
        for name, duration in sorted(video_durations.items()):
            lines.append(f"| {name} | {duration} |")

    if summary:
        lines += [
            "",
            "## Métriques acoustiques",
            "",
            "| collar | DER % | JER % | Missed % | False Alarm % | Confusion % |",
            "|---|---|---|---|---|---|",
        ]
        for collar, entry in summary.items():
            lines.append(
                f"| {collar} | {entry['DER_pct']} | {entry['JER_pct']} | {entry['Missed_Speech_pct']} | "
                f"{entry['False_Alarm_pct']} | {entry['Speaker_Confusion_pct']} |"
            )

    check = (der_report or {}).get("regression_check")
    if check:
        lines += [
            "",
            "## Contrôle de non-régression",
            "",
            f"- ΔDER : {check['delta_der_pct']:+.4f} points (limite {check['max_delta_pct']})",
            f"- ΔJER : {check['delta_jer_pct']:+.4f} points",
            f"- Parité stricte : {'PASS' if check['parity_passed'] else 'FAIL'}",
            f"- Statut : {'PASS' if check['passed'] else 'FAIL'}",
        ]

    files = (der_report or {}).get("files", {})
    if files:
        lines += [
            "",
            "## Par extrait (collar 0.00 s)",
            "",
            "| extrait | DER % | JER % | Confusion % |",
            "|---|---|---|---|",
        ]
        for name, entry in sorted(files.items()):
            strict = entry["collar_0.00s"]
            lines.append(f"| {name} | {strict['DER_pct']} | {strict['JER_pct']} | {strict['Speaker_Confusion_pct']} |")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark DER/JER de la STEP3 audio TPU")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS), help="Corpus (wav/ + rttm/)")
    parser.add_argument("--out", default=None, help="Répertoire de sortie (défaut: horodaté)")
    parser.add_argument("--limit", type=int, default=None, help="Nombre d'extraits (défaut: 5 sans clips-file/manifest, sinon tous)")
    parser.add_argument("--clips-file", default=None, help="Fichier texte listant les stems des extraits à évaluer")
    parser.add_argument("--manifest", default=None, help="Fichier CSV ou JSON décrivant les extraits à évaluer")
    parser.add_argument("--baseline", default=None, help="Rapport DER de référence pour le contrôle ΔDER")
    parser.add_argument("--require-parity", action="store_true",
                        help="Interdire aussi les améliorations (|ΔDER| ≤ limite)")
    parser.add_argument("--script", default=str(STEP3_SCRIPT), help="Script STEP3 à benchmarker")
    parser.add_argument("--python-coral", default=None, help="Interpréteur coral_env")
    parser.add_argument("--python-audio", default=None, help="Interpréteur audio_env")
    parser.add_argument("--env", action="append", default=[], metavar="KEY=VALUE", help="Surcharge d'environnement")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="Fichier .env de référence")
    parser.add_argument("--skip-run", action="store_true", help="Réutiliser les sorties existantes")
    parser.add_argument("--force", action="store_true", help="Lancer malgré un consommateur TPU actif")
    args = parser.parse_args()

    env_values = parse_env_file(Path(args.env_file))
    overrides = {}
    for item in args.env:
        if "=" not in item:
            parser.error(f"--env attend KEY=VALUE, reçu: {item}")
        key, _, value = item.partition("=")
        overrides[key.strip()] = value

    corpus = Path(args.corpus).resolve()
    if not (corpus / "wav").is_dir() or not (corpus / "rttm").is_dir():
        print(f"Corpus incomplet dans {corpus} (attendu: wav/ et rttm/).", file=sys.stderr)
        print("Lancer d'abord: python3 scripts/fetch_voxconverse_dev.py", file=sys.stderr)
        return 2

    stems_filter = None
    if args.clips_file:
        clips_file_path = Path(args.clips_file).resolve()
        if not clips_file_path.exists():
            print(f"Fichier de clips introuvable : {clips_file_path}", file=sys.stderr)
            return 2
        stems_filter = load_stems_from_clips_file(clips_file_path)
    elif args.manifest:
        manifest_path = Path(args.manifest).resolve()
        if not manifest_path.exists():
            print(f"Fichier manifest introuvable : {manifest_path}", file=sys.stderr)
            return 2
        stems_filter = load_stems_from_manifest(manifest_path)

    effective_limit = args.limit if args.limit is not None else (0 if stems_filter is not None else 5)
    clips = select_clips(corpus, effective_limit, stems_filter)
    if not clips:
        print("Aucun couple WAV/RTTM trouvé.", file=sys.stderr)
        return 2

    consumers = active_tpu_consumers()
    if consumers and not args.force:
        print("Consommateur TPU actif détecté — arrêt avant de perturber les mesures :", file=sys.stderr)
        for line in consumers:
            print(f"  {line}", file=sys.stderr)
        print("(relancer avec --force pour passer outre)", file=sys.stderr)
        return 3

    if args.out:
        run_dir = Path(args.out).resolve()
    else:
        run_dir = DEFAULT_BENCH_ROOT / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_step3_der"
    clips_dir = run_dir / "clips"
    outputs_dir = run_dir / "outputs"
    run_dir.mkdir(parents=True, exist_ok=True)

    python_coral = resolve_coral_python(args.python_coral)
    python_audio = resolve_audio_python(env_values, args.python_audio)
    script = Path(args.script).resolve()
    if not python_coral.exists() or not python_audio.exists():
        print(f"Interpréteur introuvable (coral={python_coral}, audio={python_audio})", file=sys.stderr)
        return 2
    if not script.exists():
        print(f"Script STEP3 introuvable: {script}", file=sys.stderr)
        return 2

    print(f"{len(clips)} extrait(s) | coral: {python_coral} | audio: {python_audio}")
    print(f"Répertoire: {run_dir}")

    for stale in clips_dir.glob("*_audio.json"):
        stale.unlink()
    if not args.skip_run:
        print("Préparation des clips (MKV/PCM sans perte)...")
        mux_clips(clips, clips_dir)

    return_code = 0
    wall_seconds = 0.0
    log_path = run_dir / "run.log"
    if not args.skip_run:
        print("Exécution de la STEP3...")
        environment = build_environment(Path(args.env_file), overrides)
        return_code, wall_seconds, log_path = run_step3(clips_dir, run_dir, python_coral, environment, script)
        print(f"  terminé en {wall_seconds} s (code {return_code})")
    else:
        print("--skip-run : réutilisation des clips déjà présents")

    outputs = collect_outputs(clips_dir, outputs_dir)
    print(f"{len(outputs)} JSON audio collecté(s)")

    timings = parse_run_log(log_path) if log_path.exists() else {"stages": {}, "segments": {}, "embeddings": {}}
    eval_code, der_report_path = evaluate(
        corpus / "rttm", outputs_dir, run_dir, python_audio, args.baseline, args.require_parity,
        clips_file=args.clips_file, manifest=args.manifest,
    )
    der_report = {}
    if der_report_path.exists():
        der_report = json.loads(der_report_path.read_text(encoding="utf-8"))

    run_meta = {
        "corpus": str(corpus),
        "clips_count": len(clips),
        "clips": [stem for stem, _, _ in clips],
        "clips_file": str(args.clips_file) if args.clips_file else None,
        "manifest": str(args.manifest) if args.manifest else None,
        "return_code": return_code,
        "wall_seconds": wall_seconds,
        "python_coral": str(python_coral),
        "python_audio": str(python_audio),
        "script": str(script),
        "outputs": outputs,
        "overrides": overrides,
        "eval_return_code": eval_code,
    }
    (run_dir / "run_meta.json").write_text(json.dumps(run_meta, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "timings.json").write_text(json.dumps(timings, indent=2, ensure_ascii=False), encoding="utf-8")
    (run_dir / "report.md").write_text(render_markdown(run_meta, timings, der_report), encoding="utf-8")

    print(f"Rapport : {run_dir / 'report.md'}")
    if der_report.get("summary"):
        strict = der_report["summary"].get("collar_0.00s", {})
        print(f"DER strict : {strict.get('DER_pct')} % | JER : {strict.get('JER_pct')} %")
    if der_report.get("regression_check"):
        check = der_report["regression_check"]
        print(f"Non-régression : {'PASS' if check['passed'] else 'FAIL'} (ΔDER {check['delta_der_pct']:+.4f} pts)")
        if not check.get("parity_passed", True):
            print(f"Parité stricte : FAIL (ΔDER {check['delta_der_pct']:+.4f} pts)")

    if return_code != 0:
        return return_code
    return eval_code


if __name__ == "__main__":
    sys.exit(main())
