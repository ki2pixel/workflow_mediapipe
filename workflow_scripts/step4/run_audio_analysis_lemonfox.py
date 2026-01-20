#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import importlib.util
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _configure_file_logger(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"audio_analysis_lemonfox_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)


def _find_videos_for_audio_analysis(work_dir: Path) -> list[Path]:
    video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.webm')
    videos_to_process: list[Path] = []

    all_videos = [p for ext in video_extensions for p in work_dir.rglob(f'*{ext}')]

    for video_path in all_videos:
        if video_path.suffix.lower() == '.mov':
            continue

        output_json_path = video_path.with_name(f"{video_path.stem}_audio.json")
        if not output_json_path.exists():
            videos_to_process.append(video_path)

    return videos_to_process


def _resolve_project_and_video_name(work_dir: Path, video_path: Path) -> tuple[str, str]:
    rel = video_path.relative_to(work_dir)
    parts = rel.parts
    if len(parts) < 2:
        raise ValueError(f"Video path is not inside a project folder: {rel}")
    project_name = parts[0]
    video_name = str(Path(*parts[1:]))
    return project_name, video_name


def _ensure_repo_root_on_sys_path() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)


def _import_lemonfox_audio_service():
    _ensure_repo_root_on_sys_path()

    repo_root = Path(__file__).resolve().parents[2]
    service_path = repo_root / "services" / "lemonfox_audio_service.py"
    spec = importlib.util.spec_from_file_location("lemonfox_audio_service", service_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load Lemonfox service module from {service_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.LemonfoxAudioService


def _run_pyannote_fallback(log_dir: Path) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    original_script = repo_root / "workflow_scripts" / "step4" / "run_audio_analysis.py"

    cmd = [
        sys.executable,
        str(original_script),
        "--log_dir",
        str(log_dir),
    ]

    logging.error("Fallback STEP4: exécution de la méthode originale (Pyannote) suite à une erreur Lemonfox")
    completed = subprocess.run(cmd)
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--log_dir", type=str, required=True)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    log_dir = Path(args.log_dir)
    _configure_file_logger(log_dir)

    work_dir = Path(os.getcwd())

    try:
        lemonfox_service = _import_lemonfox_audio_service()
    except Exception as e:
        logging.error(f"Impossible d'importer LemonfoxAudioService: {e}")
        return _run_pyannote_fallback(log_dir)

    videos_to_process = _find_videos_for_audio_analysis(work_dir)
    logging.info(f"TOTAL_AUDIO_TO_ANALYZE: {len(videos_to_process)}")

    if not videos_to_process:
        logging.info("Aucune vidéo à analyser (tous les _audio.json existent déjà).")
        return 0

    for idx, video_path in enumerate(videos_to_process, start=1):
        logging.info(f"ANALYZING_AUDIO: {idx}/{len(videos_to_process)}: {video_path.name}")

        try:
            project_name, video_name = _resolve_project_and_video_name(work_dir, video_path)
        except Exception as e:
            logging.error(f"Erreur résolution projet/vidéo pour {video_path}: {e}")
            return _run_pyannote_fallback(log_dir)

        try:
            duration_sec = lemonfox_service._get_video_duration_ffprobe(video_path)
            fps = 25.0
            total_frames = int(round((duration_sec or 0.0) * fps))
            if total_frames > 0:
                logging.info(f"INTERNAL_PROGRESS: 0/{total_frames} frames (0%) - Lemonfox API call")

            result = lemonfox_service.process_video_with_lemonfox(
                project_name=project_name,
                video_name=video_name,
            )

            if not result.success:
                logging.error(f"Erreur Lemonfox pour {video_path.name}: {result.error}")
                return _run_pyannote_fallback(log_dir)

            if result.total_frames > 0:
                logging.info(
                    f"INTERNAL_PROGRESS: {result.total_frames}/{result.total_frames} frames (100%) - Lemonfox done"
                )

            logging.info(f"Succès: analyse audio terminée pour {video_path.name}")

        except Exception as e:
            logging.error(f"Erreur inattendue Lemonfox pour {video_path.name}: {e}", exc_info=True)
            return _run_pyannote_fallback(log_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
