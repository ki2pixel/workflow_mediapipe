#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Harnais de benchmark de la STEP4 tracking en mode Coral TPU.

Lance ``workflow_scripts/step4/run_tracking_tpu.py`` sur un lot de vidéos déjà
préparées (STEP1-3), récupère les rapports de profilage par étage, déplace les
JSON produits dans un répertoire de variante et génère un rapport
Markdown/CSV/JSON.

Le harnais n'utilise que la bibliothèque standard : l'exécution est déléguée au
venv Coral (``coral_env``) et les mesures viennent du script instrumenté
(``--profile-dir``). Chaque variante est isolée dans
``scratch/bench_step4_tpu/<horodatage>_<label>/`` afin de pouvoir comparer deux
exécutions sans écraser la référence.

Exemples :
    python3 scripts/bench_step4_tpu.py --variant baseline --root projets_extraits
    STEP4_TPU_FAST=2 python3 scripts/bench_step4_tpu.py --variant fast2 --root projets_extraits
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCH_ROOT = PROJECT_ROOT / "scratch" / "bench_step4_tpu"
DEFAULT_TRACKING_SCRIPT = PROJECT_ROOT / "workflow_scripts" / "step4" / "run_tracking_tpu.py"
DEFAULT_VIDEO_ROOT = PROJECT_ROOT / "projets_extraits"
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"
VIDEO_EXTENSIONS = (".mp4", ".avi", ".mov", ".mkv", ".webm")

# Rôles concurrents du pipeline : le débit est imposé par le plus lent.
ROLE_PREFIXES = {
    "acquisition": ("acq_",),
    "worker": ("worker_",),
    "parent": ("",),
}
PARENT_STAGES = ("tracking_serial", "json_write", "parent_total", "e2e_frame")
ROLE_TOTAL_STAGE = {
    "acquisition": None,
    "worker": "worker_worker_total",
    "parent": "parent_total",
}


def parse_env_file(path: Path) -> dict:
    """Lecture minimale d'un .env (KEY=VALUE, commentaires et guillemets ignorés)."""
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
    """Environnement du run : processus courant < .env < --env."""
    environment = dict(os.environ)
    for key, value in parse_env_file(env_file).items():
        environment.setdefault(key, value)
    environment.update(overrides)
    return environment


def resolve_python(explicit: str = None) -> Path:
    """Python du venv Coral, avec repli explicite si absent."""
    if explicit:
        return Path(explicit)
    candidate = PROJECT_ROOT / "coral_env" / "bin" / "python"
    if candidate.exists():
        return candidate
    return Path(sys.executable)


def collect_videos(root: Path, pattern: str, limit: int = None, filters: list = None) -> list:
    """Liste déterministe des vidéos à traiter (chemins résolus, triés)."""
    videos = [path for path in sorted(root.glob(pattern)) if path.is_file()]
    videos = [path for path in videos if path.suffix.lower() in VIDEO_EXTENSIONS]
    if filters:
        lowered = [item.lower() for item in filters]
        videos = [path for path in videos if any(item in path.name.lower() for item in lowered)]
    if limit:
        videos = videos[:limit]
    return [path.resolve() for path in videos]


def check_prerequisites(videos: list) -> list:
    """Vérifie la présence des artefacts STEP1-3 attendus par la STEP4."""
    warnings = []
    for video in videos:
        stem = video.with_suffix("")
        if not Path(f"{stem}.csv").exists():
            warnings.append(f"{video.name}: CSV de scènes (STEP2) absent")
        if not Path(f"{stem}_audio.json").exists():
            warnings.append(f"{video.name}: diarisation (STEP3) absente — détection d'élocution dégradée")
    return warnings


def active_tpu_consumers() -> list:
    """Détecte les autres consommateurs du TPU (un seul accès /dev/apex_0 possible)."""
    consumers = []
    try:
        result = subprocess.run(
            ["pgrep", "-af", "workflow_scripts/step"],
            capture_output=True, text=True, check=False
        )
    except OSError:
        return consumers

    own_pid = str(os.getpid())
    for line in result.stdout.splitlines():
        if own_pid in line.split()[:1]:
            continue
        if "bench_step4_tpu.py" in line:
            continue
        consumers.append(line.strip())
    return consumers


def run_variant(args, videos, run_dir: Path, environment: dict, python_exe: Path) -> dict:
    """Exécute une passe complète du script TPU sur le lot de vidéos."""
    profiling_dir = run_dir / "profiling"
    outputs_dir = run_dir / "outputs"
    profiling_dir.mkdir(parents=True, exist_ok=True)
    outputs_dir.mkdir(parents=True, exist_ok=True)

    videos_json = run_dir / "videos.json"
    videos_json.write_text(json.dumps([str(path) for path in videos], ensure_ascii=False, indent=2), encoding="utf-8")

    command = [
        str(python_exe),
        str(args.script),
        "--videos_json_path", str(videos_json),
        "--profile-dir", str(profiling_dir),
    ]
    if args.sequential:
        command.append("--sequential")

    log_path = run_dir / "run.log"
    started = time.time()
    with open(log_path, "w", encoding="utf-8") as log_file:
        process = subprocess.Popen(
            command,
            cwd=str(args.root),
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in process.stdout:
            log_file.write(line)
            stripped = line.rstrip("\n")
            if "PROCESSING_VIDEO" in stripped or "Succès" in stripped or "CRITICAL" in stripped or "Échec" in stripped:
                print(f"    {stripped}", flush=True)
        return_code = process.wait()
    wall_seconds = time.time() - started

    moved = []
    missing = []
    for video in videos:
        produced = video.with_suffix(".json")
        if produced.exists():
            destination = outputs_dir / produced.name
            shutil.move(str(produced), str(destination))
            moved.append(destination.name)
        else:
            missing.append(video.name)

    run_meta = {
        "command": command,
        "cwd": str(args.root),
        "return_code": return_code,
        "wall_seconds": round(wall_seconds, 2),
        "videos": [str(path) for path in videos],
        "outputs": moved,
        "missing_outputs": missing,
        "overrides": args.env_overrides,
        "python": str(python_exe),
    }
    (run_dir / "run_meta.json").write_text(json.dumps(run_meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return run_meta


def parse_run_log(log_path: Path) -> dict:
    """Durées par vidéo lues dans le log (mesure externe, indépendante du profilage)."""
    durations = {}
    current = None
    current_start = None

    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            timestamp = datetime.strptime(line[:23], "%Y-%m-%d %H:%M:%S,%f")
        except ValueError:
            continue
        if "PROCESSING_VIDEO:" in line:
            current = line.split("PROCESSING_VIDEO:", 1)[1].strip()
            current_start = timestamp
        elif "Succès:" in line and current and current_start:
            durations[Path(current).stem] = round((timestamp - current_start).total_seconds(), 2)
            current, current_start = None, None
    return durations


def load_reports(profiling_dir: Path) -> dict:
    """Charge les rapports de profilage par vidéo (ignore le fingerprint et les restes worker)."""
    reports = {}
    for path in sorted(profiling_dir.glob("*.json")):
        if path.name == "run_fingerprint.json" or ".worker." in path.name:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if "stages" in payload:
            reports[payload.get("video", path.stem)] = payload
    return reports


def stage_role(stage_name: str) -> str:
    if stage_name.startswith("worker_"):
        return "worker"
    if stage_name.startswith("acq_"):
        return "acquisition"
    return "parent"


def aggregate_reports(reports: dict, durations: dict) -> dict:
    """Agrège les rapports par vidéo en statistiques de variante."""
    stage_totals = {}
    per_video = []
    total_frames = 0
    total_wall = 0.0

    for label, report in sorted(reports.items()):
        frames = int(report.get("frames") or 0)
        if frames <= 0:
            continue
        wall_seconds = durations.get(label)
        if wall_seconds is None:
            wall_seconds = round(float(report.get("wall_ms") or 0.0) / 1000.0, 2)
        total_frames += frames
        total_wall += wall_seconds

        for stage, data in report.get("stages", {}).items():
            entry = stage_totals.setdefault(stage, {
                "role": stage_role(stage),
                "count": 0,
                "total_ms": 0.0,
                "p95_ms_max": 0.0,
                "p99_ms_max": 0.0,
                "max_ms": 0.0,
                "videos": 0,
            })
            entry["videos"] += 1
            entry["count"] += int(data.get("count_analyzed") or data.get("count") or 0)
            entry["total_ms"] += float(data.get("total_ms") or 0.0)
            entry["p95_ms_max"] = max(entry["p95_ms_max"], float(data.get("p95_ms") or 0.0))
            entry["p99_ms_max"] = max(entry["p99_ms_max"], float(data.get("p99_ms") or 0.0))
            entry["max_ms"] = max(entry["max_ms"], float(data.get("max_ms") or 0.0))

        per_video.append({
            "video": label,
            "frames": frames,
            "wall_s": wall_seconds,
            "fps": round(frames / wall_seconds, 2) if wall_seconds else None,
            "ms_per_frame": round(wall_seconds * 1000.0 / frames, 3) if frames else None,
            "worker_mean_ms": _stage_mean(report, "worker_worker_total"),
            "parent_mean_ms": _stage_mean(report, "parent_total"),
            "e2e_mean_ms": _stage_mean(report, "e2e_frame"),
            "queue_fill_mean": (((report.get("worker") or {}).get("gauges") or {}).get("queue_fill") or {}).get("mean"),
            "active_objects_mean": ((report.get("gauges") or {}).get("active_objects") or {}).get("mean"),
        })

    for stage, entry in stage_totals.items():
        entry["mean_ms"] = round(entry["total_ms"] / entry["count"], 4) if entry["count"] else None
        entry["total_ms"] = round(entry["total_ms"], 3)

    role_budgets = {}
    for role in ("worker", "acquisition", "parent"):
        total_stage = ROLE_TOTAL_STAGE.get(role)
        if total_stage and total_stage in stage_totals:
            role_budgets[role] = stage_totals[total_stage]["mean_ms"] or 0.0
            continue
        stage_names = PARENT_STAGES if role == "parent" else ()
        if role == "acquisition":
            stage_names = [name for name, data in stage_totals.items() if data["role"] == "acquisition"]
        role_budgets[role] = round(sum(
            (stage_totals[name]["mean_ms"] or 0.0) for name in stage_names if name in stage_totals
        ), 4)

    slowest_role = max(role_budgets, key=role_budgets.get) if role_budgets else None
    bottleneck = None
    if slowest_role:
        candidates = [
            (name, data) for name, data in stage_totals.items()
            if data["role"] == slowest_role and name != ROLE_TOTAL_STAGE.get(slowest_role)
        ]
        if candidates:
            name, data = max(candidates, key=lambda item: item[1]["mean_ms"] or 0.0)
            bottleneck = {"role": slowest_role, "stage": name, "mean_ms": data["mean_ms"]}

    return {
        "videos": len(per_video),
        "frames": total_frames,
        "wall_s": round(total_wall, 2),
        "fps": round(total_frames / total_wall, 2) if total_wall else None,
        "ms_per_frame": round(total_wall * 1000.0 / total_frames, 3) if total_frames else None,
        "role_budgets_ms": role_budgets,
        "bottleneck": bottleneck,
        "stages": stage_totals,
        "per_video": per_video,
    }


def _stage_mean(report: dict, stage: str):
    data = (report.get("stages") or {}).get(stage)
    return data.get("mean_ms") if data else None


def render_markdown(variant: str, run_meta: dict, aggregation: dict, fingerprint: dict) -> str:
    lines = [
        f"# Benchmark STEP4 TPU — variante `{variant}`",
        "",
        f"- Exécution : {run_meta['wall_seconds']} s (code retour {run_meta['return_code']})",
        f"- Vidéos : {aggregation['videos']} | frames : {aggregation['frames']}",
        f"- Débit global : **{aggregation['fps']} fps** ({aggregation['ms_per_frame']} ms/frame)",
        f"- Pipeline : {(fingerprint or {}).get('pipeline_mode')} | modèles co-compilés : {(fingerprint or {}).get('cocompiled_models')}",
        f"- Surcharges : {json.dumps(run_meta.get('overrides') or {}, ensure_ascii=False)}",
        "",
        "## Budget par rôle (concurrents, le plus lent impose le débit)",
        "",
        "| rôle | ms/frame | part du budget |",
        "|---|---|---|",
    ]
    budgets = aggregation["role_budgets_ms"]
    slowest = max(budgets, key=budgets.get) if budgets else None
    for role, value in sorted(budgets.items(), key=lambda item: item[1], reverse=True):
        share = (value / budgets[slowest] * 100.0) if slowest and budgets[slowest] else 0.0
        lines.append(f"| {role}{' (goulot)' if role == slowest else ''} | {value} | {share:.1f} % |")

    bottleneck = aggregation.get("bottleneck")
    if bottleneck:
        lines += [
            "",
            f"**Goulot identifié** : `{bottleneck['stage']}` ({bottleneck['mean_ms']} ms/frame, rôle {bottleneck['role']}).",
        ]

    lines += [
        "",
        "## Décomposition par étage",
        "",
        "| étage | rôle | count | mean ms | p95 ms | p99 ms | max ms | total ms |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, data in sorted(aggregation["stages"].items(), key=lambda item: item[1]["mean_ms"] or 0.0, reverse=True):
        lines.append(
            f"| {name} | {data['role']} | {data['count']} | {data['mean_ms']} | {data['p95_ms_max']} | "
            f"{data['p99_ms_max']} | {data['max_ms']} | {data['total_ms']} |"
        )

    lines += [
        "",
        "## Par vidéo",
        "",
        "| vidéo | frames | wall s | fps | ms/frame | worker ms | parent ms | e2e ms | queue |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in aggregation["per_video"]:
        lines.append(
            f"| {row['video']} | {row['frames']} | {row['wall_s']} | {row['fps']} | {row['ms_per_frame']} | "
            f"{row['worker_mean_ms']} | {row['parent_mean_ms']} | {row['e2e_mean_ms']} | {row['queue_fill_mean']} |"
        )

    if run_meta.get("missing_outputs"):
        lines += ["", "## Sorties manquantes", ""]
        lines += [f"- {name}" for name in run_meta["missing_outputs"]]

    lines.append("")
    return "\n".join(lines)


def write_summaries(run_dir: Path, variant: str, run_meta: dict, aggregation: dict, fingerprint: dict) -> None:
    (run_dir / "summary.json").write_text(
        json.dumps({
            "variant": variant,
            "run_meta": run_meta,
            "aggregation": aggregation,
            "fingerprint": fingerprint,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    header = "video,frames,wall_s,fps,ms_per_frame,worker_mean_ms,parent_mean_ms,e2e_mean_ms,queue_fill_mean"
    rows = [header]
    for row in aggregation["per_video"]:
        rows.append(",".join(str(row.get(key)) for key in (
            "video", "frames", "wall_s", "fps", "ms_per_frame",
            "worker_mean_ms", "parent_mean_ms", "e2e_mean_ms", "queue_fill_mean",
        )))
    (run_dir / "summary.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")

    (run_dir / "report.md").write_text(
        render_markdown(variant, run_meta, aggregation, fingerprint), encoding="utf-8"
    )


def publish_outputs(run_dir: Path, videos: list) -> int:
    """Recopie les JSON d'une variante à côté des vidéos (livraison finale)."""
    published = 0
    for source in (run_dir / "outputs").glob("*.json"):
        for video in videos:
            if video.with_suffix(".json").name == source.name:
                shutil.copy2(source, video.with_suffix(".json"))
                published += 1
                break
    return published


def main():
    parser = argparse.ArgumentParser(description="Benchmark de la STEP4 tracking TPU (profiling par étage)")
    parser.add_argument("--variant", required=True, help="Label de la variante (baseline, fast1, ...)")
    parser.add_argument("--root", default=str(DEFAULT_VIDEO_ROOT), help="Racine des vidéos")
    parser.add_argument("--pattern", default="**/*.mp4", help="Motif glob des vidéos à traiter")
    parser.add_argument("--videos", nargs="*", default=None, help="Filtres sur le nom de fichier")
    parser.add_argument("--limit", type=int, default=None, help="Limiter le nombre de vidéos")
    parser.add_argument("--repeat", type=int, default=1, help="Nombre de passes complètes")
    parser.add_argument("--warmup-frames", type=int, default=50, help="Frames exclues de l'agrégation par étage")
    parser.add_argument("--env", action="append", default=[], metavar="KEY=VALUE", help="Surcharge d'environnement")
    parser.add_argument("--script", default=str(DEFAULT_TRACKING_SCRIPT), help="Script de tracking à benchmarker")
    parser.add_argument("--python", default=None, help="Interpréteur Python (défaut: coral_env)")
    parser.add_argument("--bench-root", default=str(DEFAULT_BENCH_ROOT), help="Racine des artefacts de benchmark")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_FILE), help="Fichier .env de référence")
    parser.add_argument("--sequential", action="store_true", help="Utiliser le pipeline séquentiel")
    parser.add_argument("--publish", action="store_true", help="Recopier les JSON finaux à côté des vidéos")
    parser.add_argument("--force", action="store_true", help="Lancer même si un consommateur TPU est actif")
    args = parser.parse_args()

    args.env_overrides = {}
    for item in args.env:
        if "=" not in item:
            parser.error(f"--env attend KEY=VALUE, reçu: {item}")
        key, _, value = item.partition("=")
        args.env_overrides[key.strip()] = value

    args.root = Path(args.root).resolve()
    args.script = Path(args.script).resolve()

    if not args.root.exists():
        print(f"Racine introuvable: {args.root}", file=sys.stderr)
        return 2
    if not args.script.exists():
        print(f"Script introuvable: {args.script}", file=sys.stderr)
        return 2

    videos = collect_videos(args.root, args.pattern, args.limit, args.videos)
    if not videos:
        print("Aucune vidéo à traiter.", file=sys.stderr)
        return 2

    consumers = active_tpu_consumers()
    if consumers and not args.force:
        print("Consommateur TPU actif détecté — arrêt avant de perturber les mesures :", file=sys.stderr)
        for line in consumers:
            print(f"  {line}", file=sys.stderr)
        print("(relancer avec --force pour passer outre)", file=sys.stderr)
        return 3

    warnings = check_prerequisites(videos)
    for warning in warnings:
        print(f"  avertissement: {warning}", file=sys.stderr)

    python_exe = resolve_python(args.python)
    environment = build_environment(Path(args.env_file), args.env_overrides)
    environment["STEP4_TPU_PROFILE_WARMUP"] = str(args.warmup_frames)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    variant_dir = Path(args.bench_root) / f"{timestamp}_{args.variant}"
    variant_dir.mkdir(parents=True, exist_ok=True)

    print(f"Variante {args.variant} -> {variant_dir}")
    print(f"{len(videos)} vidéo(s) | python: {python_exe}")

    repeats = max(1, args.repeat)
    repeat_reports = []
    for index in range(repeats):
        run_dir = variant_dir if repeats == 1 else variant_dir / f"repeat_{index + 1}"
        run_dir.mkdir(parents=True, exist_ok=True)
        print(f"  passe {index + 1}/{repeats}...")
        run_meta = run_variant(args, videos, run_dir, environment, python_exe)

        reports = load_reports(run_dir / "profiling")
        durations = parse_run_log(run_dir / "run.log")
        fingerprint = {}
        fingerprint_path = run_dir / "profiling" / "run_fingerprint.json"
        if fingerprint_path.exists():
            fingerprint = json.loads(fingerprint_path.read_text(encoding="utf-8"))

        aggregation = aggregate_reports(reports, durations)
        write_summaries(run_dir, args.variant, run_meta, aggregation, fingerprint)
        repeat_reports.append({
            "run_dir": str(run_dir),
            "fps": aggregation["fps"],
            "ms_per_frame": aggregation["ms_per_frame"],
            "videos": aggregation["videos"],
            "frames": aggregation["frames"],
            "bottleneck": aggregation.get("bottleneck"),
        })
        print(f"    {aggregation['videos']} vidéo(s) mesurée(s) — {aggregation['fps']} fps ({aggregation['ms_per_frame']} ms/frame)")

    (variant_dir / "repeats.json").write_text(json.dumps(repeat_reports, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.publish:
        published = publish_outputs(variant_dir, videos)
        print(f"{published} JSON recopiés à côté des vidéos.")

    print(f"Rapport: {variant_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
