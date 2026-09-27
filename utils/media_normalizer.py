#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalisation vidéo partagée du pipeline (extraction STEP1 et garde-fous aval).

Règle d'or du pipeline : toute vidéo doit être conforme au contrat
**MP4 / H.264 / 25 fps / yuv420p** avant l'analyse des transitions, car les
étapes aval (transitions, audio, tracking, réduction JSON, pré-traitement AE)
indexent leurs résultats par numéro de frame et calculent leurs timecodes sur
une base 25 fps codée en dur.

Ce module était auparavant le script `workflow_scripts/step2/convert_videos.py`.
Il est désormais :
- appelé par STEP1 après chaque extraction d'archive ;
- exposé via `--normalize-only` pour rattraper les projets extraits avant la
  suppression de l'étape de conversion ;
- importable par les étapes d'analyse pour vérifier le framerate des fichiers
  qu'elles découvrent (`analyze_video` / `is_conformant` n'ont aucune
  dépendance à `config.settings`).

Les fichiers `.mov` (logos animés à couche alpha, cf. `utils.media_filters`)
ne sont jamais touchés.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.media_filters import is_preserved_media, split_preserved_media

# --- Contrat vidéo ---
TARGET_FPS = 25.0
FPS_TOLERANCE = 0.1
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv')
CONFORMANT_VIDEO_CODECS = ('h264',)

# --- Encodage ---
QUALITY_CRF = 28
AUDIO_BITRATE = '192k'
AUDIO_COPY_CODECS = ('aac', 'mp3', 'ac3')

# --- Exécution ---
FFMPEG_PATH = "ffmpeg"
FFPROBE_PATH = "ffprobe"
MAX_GPU_WORKERS = 3
MAX_PROBE_WORKERS = 10
TEMP_SUFFIX = ".temp_normalize.mp4"
SKIP_NAME_TOKENS = ("_temp_conversion", "_converted", ".temp_compress", ".temp_normalize")

logger = logging.getLogger(__name__)


@dataclass
class NormalizationSummary:
    """Résultat d'une passe de normalisation sur un dossier."""
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0

    @property
    def is_success(self) -> bool:
        return self.failed == 0


def _setting(name: str, default: Any) -> Any:
    """Lit un réglage applicatif sans rendre `config.settings` obligatoire.

    Les étapes aval (venvs transnet/coral) importent ce module pour le seul
    garde-fou de framerate : l'absence de configuration ne doit pas les casser.
    """
    try:
        from config.settings import config as app_config
    except Exception as exc:
        logger.debug("config.settings indisponible (%s) : réglage '%s' par défaut", exc, name)
        return default
    return getattr(app_config, name, default)


def is_normalization_enabled() -> bool:
    """Indique si STEP1 doit normaliser les vidéos qu'il vient d'extraire."""
    return bool(_setting('STEP1_NORMALIZE_VIDEOS', True))


def _parse_ffprobe_fraction(value: str) -> Optional[float]:
    if not value:
        return None
    value = str(value).strip()
    if not value or value == "0/0":
        return None
    try:
        if "/" in value:
            num_str, den_str = value.split("/", 1)
            num = float(num_str)
            den = float(den_str)
            if den == 0:
                return None
            return num / den
        return float(value)
    except (TypeError, ValueError) as exc:
        logger.debug("Fraction ffprobe illisible (%r): %s", value, exc)
        return None


def _parse_ffprobe_fps(payload: dict) -> Optional[float]:
    """Déduit le framerate réel, en préférant comptage/durée aux taux nominaux."""
    try:
        streams = payload.get("streams") or []
        if not streams:
            return None

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
        if not video_stream:
            return None

        avg_fps = _parse_ffprobe_fraction(video_stream.get("avg_frame_rate"))
        r_fps = _parse_ffprobe_fraction(video_stream.get("r_frame_rate"))

        nb_frames_raw = video_stream.get("nb_frames")
        duration_raw = video_stream.get("duration")
        nb_frames = None
        duration = None

        try:
            if nb_frames_raw not in (None, "N/A", ""):
                nb_frames = int(float(nb_frames_raw))
        except (TypeError, ValueError) as exc:
            logger.debug("nb_frames illisible (%r): %s", nb_frames_raw, exc)

        try:
            if duration_raw not in (None, "N/A", ""):
                duration = float(duration_raw)
        except (TypeError, ValueError) as exc:
            logger.debug("duration illisible (%r): %s", duration_raw, exc)

        fps_from_counts = None
        if nb_frames and duration and duration > 0:
            fps_from_counts = float(nb_frames) / float(duration)

        for candidate in (fps_from_counts, avg_fps, r_fps):
            if candidate is None:
                continue
            if candidate <= 0 or candidate > 240:
                continue
            return float(candidate)
        return None
    except Exception as exc:
        logger.debug("Analyse ffprobe fps impossible: %s", exc)
        return None


def analyze_video(video_path: Path, target_fps: float = TARGET_FPS) -> Dict[str, Any]:
    """Analyse framerate, codecs vidéo/audio d'un fichier via ffprobe."""
    try:
        command = [
            FFPROBE_PATH, "-v", "error",
            "-show_entries", "stream=codec_type,codec_name,avg_frame_rate,r_frame_rate,nb_frames,duration",
            "-of", "json",
            str(video_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        payload = json.loads(result.stdout or "{}")

        fps = _parse_ffprobe_fps(payload)

        video_codec = None
        audio_codec = None
        for stream in payload.get("streams", []):
            if stream.get("codec_type") == "video" and video_codec is None:
                video_codec = stream.get("codec_name")
            elif stream.get("codec_type") == "audio" and audio_codec is None:
                audio_codec = stream.get("codec_name")

        return {
            'path': Path(video_path),
            'fps': fps,
            'video_codec': video_codec,
            'audio_codec': audio_codec,
            'needs_fps_fix': fps is not None and abs(fps - target_fps) > FPS_TOLERANCE,
            'error': None,
        }
    except Exception as exc:
        logger.exception("Impossible d'analyser %s: %s", Path(video_path).name, exc)
        return {
            'path': Path(video_path),
            'fps': None,
            'video_codec': None,
            'audio_codec': None,
            'needs_fps_fix': False,
            'error': str(exc),
        }


def is_conformant(video_info: Dict[str, Any], target_fps: float = TARGET_FPS) -> bool:
    """Vrai si le fichier respecte déjà le contrat MP4 / H.264 / <target_fps>."""
    if video_info.get('error'):
        return False

    video_path = Path(video_info['path'])
    if video_path.suffix.lower() != '.mp4':
        return False

    video_codec = (video_info.get('video_codec') or '').lower()
    if video_codec not in CONFORMANT_VIDEO_CODECS:
        return False

    fps = video_info.get('fps')
    if fps is None:
        return False

    return abs(float(fps) - float(target_fps)) <= FPS_TOLERANCE


def discover_videos(root: Path) -> Tuple[List[Path], List[Path]]:
    """Liste les vidéos candidates sous ``root``.

    Returns:
        ``(candidats, logos_mov_préservés)``
    """
    candidates: List[Path] = []
    for current_root, _, files in os.walk(root):
        for file_name in files:
            if any(token in file_name for token in SKIP_NAME_TOKENS):
                continue
            if file_name.lower().endswith(VIDEO_EXTENSIONS):
                candidates.append(Path(current_root) / file_name)

    return split_preserved_media(candidates)


def _analyze_many(paths: List[Path], target_fps: float) -> List[Dict[str, Any]]:
    if not paths:
        return []

    analyzed: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=MAX_PROBE_WORKERS) as executor:
        futures = {executor.submit(analyze_video, path, target_fps): path for path in paths}
        for future in as_completed(futures):
            analyzed.append(future.result())
    return analyzed


def normalize_video(
    video_info: Dict[str, Any],
    use_gpu: bool = True,
    target_fps: float = TARGET_FPS,
    quality_crf: int = QUALITY_CRF,
) -> bool:
    """Ré-encode une vidéo vers MP4 / H.264 / yuv420p / <target_fps> (passe unique)."""
    video_path = Path(video_info['path'])

    if video_info.get('error'):
        logger.error("Normalisation impossible pour %s: %s", video_path.name, video_info['error'])
        return False

    if is_preserved_media(video_path):
        logger.info("Logo .mov préservé ignoré par le worker: %s", video_path.name)
        return True

    worker_type = 'GPU' if use_gpu else 'CPU'
    temp_output_path = video_path.with_suffix(TEMP_SUFFIX)

    try:
        fps_str = f"{video_info['fps']:.2f}" if video_info.get('fps') is not None else "Inconnu"
        logger.info(
            "Normalisation (%s) démarrée pour %s (FPS=%s, Audio=%s)",
            worker_type, video_path.name, fps_str, video_info.get('audio_codec'),
        )

        command = [FFMPEG_PATH, '-y', '-hide_banner']
        if use_gpu:
            command.extend(['-hwaccel', 'cuda'])

        command.extend(['-i', str(video_path)])

        if video_info.get('needs_fps_fix'):
            command.extend(['-vf', f'fps={target_fps}'])

        if use_gpu:
            command.extend([
                '-c:v', 'h264_nvenc', '-preset', 'p5', '-tune', 'hq',
                '-cq', str(quality_crf), '-pix_fmt', 'yuv420p',
            ])
        else:
            command.extend([
                '-c:v', 'libx264', '-preset', 'medium',
                '-crf', str(quality_crf), '-pix_fmt', 'yuv420p',
            ])

        if video_info.get('audio_codec') in AUDIO_COPY_CODECS:
            command.extend(['-c:a', 'copy'])
        else:
            command.extend(['-c:a', 'aac', '-b:a', AUDIO_BITRATE])

        command.append(str(temp_output_path))

        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8')

        if result.returncode != 0:
            logger.error(
                "Erreur FFmpeg (%s) pour %s.\nStderr: %s",
                worker_type, video_path.name, result.stderr.strip(),
            )
            if temp_output_path.exists():
                temp_output_path.unlink()
            return False

        final_dest = video_path.with_suffix('.mp4')
        if final_dest != video_path and video_path.exists():
            video_path.unlink()

        shutil.move(str(temp_output_path), str(final_dest))
        logger.info("Succès (%s): %s normalisée (MP4/H.264/%s fps).", worker_type, video_path.name, target_fps)
        return True

    except Exception as exc:
        logger.exception("Erreur inattendue du worker (%s) pour %s: %s", worker_type, video_path.name, exc)
        if temp_output_path.exists():
            try:
                temp_output_path.unlink()
            except OSError as cleanup_error:
                logger.warning("Nettoyage impossible de %s: %s", temp_output_path, cleanup_error)
        return False


def normalize_video_with_fallback(
    video_info: Dict[str, Any],
    target_fps: float = TARGET_FPS,
    quality_crf: int = QUALITY_CRF,
    use_gpu: bool = True,
) -> bool:
    """Tente un encodage GPU, bascule sur CPU en cas d'échec."""
    if not use_gpu:
        return normalize_video(video_info, use_gpu=False, target_fps=target_fps, quality_crf=quality_crf)

    if normalize_video(video_info, use_gpu=True, target_fps=target_fps, quality_crf=quality_crf):
        return True

    logger.warning("Fallback CPU déclenché pour %s", Path(video_info['path']).name)
    return normalize_video(video_info, use_gpu=False, target_fps=target_fps, quality_crf=quality_crf)


def normalize_videos_in(root: Path, force: bool = False) -> NormalizationSummary:
    """Normalise toutes les vidéos d'un dossier selon le contrat du pipeline.

    Args:
        root: dossier racine à parcourir récursivement.
        force: ré-encode même les fichiers déjà conformes (sources brutes
            fraîchement extraites) ; sinon les fichiers conformes sont ignorés.
    """
    root = Path(root)
    target_fps = float(_setting('STEP1_FPS_TARGET', TARGET_FPS) or TARGET_FPS)
    quality_crf = int(_setting('STEP1_QUALITY_CRF', QUALITY_CRF) or QUALITY_CRF)
    use_gpu = bool(_setting('STEP1_USE_GPU', True))
    max_workers = max(1, int(_setting('STEP1_MAX_GPU_WORKERS', MAX_GPU_WORKERS) or MAX_GPU_WORKERS))

    logger.info("Recherche de vidéos (%s) dans %s...", ', '.join(VIDEO_EXTENSIONS), root)

    candidates, preserved_logos = discover_videos(root)
    for logo in preserved_logos:
        logger.info("--- Logo .mov préservé (non normalisé, alpha intact): %s ---", logo.name)
    if preserved_logos:
        logger.info(
            "%d .mov préservé(s) ignoré(s) par la normalisation (alpha conservé jusqu'à la finalisation).",
            len(preserved_logos),
        )

    analyzed = _analyze_many(candidates, target_fps)
    analysis_failures = [info for info in analyzed if info.get('error')]
    for info in analysis_failures:
        logger.error("Analyse impossible, fichier laissé en l'état: %s (%s)", info['path'].name, info['error'])

    usable = [info for info in analyzed if not info.get('error')]
    conformant: List[Dict[str, Any]] = []
    if not force:
        conformant = [info for info in usable if is_conformant(info, target_fps)]
        usable = [info for info in usable if not is_conformant(info, target_fps)]
        for info in conformant:
            logger.info("Déjà conforme, ignorée: %s", info['path'].name)

    total = len(usable)
    skipped = len(conformant) + len(preserved_logos)

    logger.info("TOTAL_VIDEOS_TO_PROCESS: %d", total)
    print(f"TOTAL_VIDEOS_TO_PROCESS: {total}")

    if total == 0:
        logger.info("Aucune vidéo à normaliser.")
        return NormalizationSummary(
            total=0, success=0, failed=len(analysis_failures), skipped=skipped,
        )

    logger.info("Lancement du pool de normalisation (%d workers max) pour %d vidéo(s).", max_workers, total)

    progress_lock = threading.Lock()
    progress_state = {'completed': 0}
    success_count = 0

    def _process(video_info: Dict[str, Any]) -> bool:
        with progress_lock:
            progress_state['completed'] += 1
            index = progress_state['completed']
        message = f"INTERNAL_PROGRESS: {index}/{total} vidéos ({int(index * 100 / total)}%) - {Path(video_info['path']).name}"
        logger.info("--- Normalisation (%d/%d): %s ---", index, total, Path(video_info['path']).name)
        print(message)
        return normalize_video_with_fallback(
            video_info, target_fps=target_fps, quality_crf=quality_crf, use_gpu=use_gpu,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for succeeded in executor.map(_process, usable):
            if succeeded:
                success_count += 1

    failures = len(analysis_failures) + (total - success_count)
    logger.info("--- Normalisation terminée : %d/%d réussie(s) ---", success_count, total)

    return NormalizationSummary(total=total, success=success_count, failed=failures, skipped=skipped)


def check_fps_conformance(video_path: Path, target_fps: float = TARGET_FPS) -> Optional[float]:
    """Retourne le framerate détecté s'il dévie du contrat, sinon None.

    Utilisé par les étapes d'analyse comme garde-fou non bloquant : un fichier
    non normalisé provoquerait une désynchronisation frame/timecode en aval.
    """
    info = analyze_video(video_path, target_fps)
    if info.get('error'):
        logger.warning("Framerate indéterminable pour %s: %s", Path(video_path).name, info['error'])
        return None

    fps = info.get('fps')
    if fps is None or abs(float(fps) - float(target_fps)) <= FPS_TOLERANCE:
        return None

    logger.warning(
        "Fichier non normalisé détecté: %s (%.2f fps au lieu de %.2f). "
        "Risque de désynchronisation frame/timecode en aval — lancer "
        "`extract_archives.py --normalize-only`.",
        Path(video_path).name, float(fps), float(target_fps),
    )
    return float(fps)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')

    parser = argparse.ArgumentParser(description="Normalisation vidéo autonome (MP4/H.264/25 fps).")
    parser.add_argument('root', type=str, help="Dossier à parcourir récursivement.")
    parser.add_argument('--force', action='store_true', help="Ré-encoder aussi les fichiers déjà conformes.")
    cli_args = parser.parse_args()

    summary = normalize_videos_in(Path(cli_args.root), force=cli_args.force)
    logging.info("Résumé: %s", summary)
    raise SystemExit(0 if summary.is_success else 1)
