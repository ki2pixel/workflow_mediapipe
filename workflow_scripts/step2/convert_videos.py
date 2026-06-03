#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de conversion vidéo pour le workflow de traitement
Version Ubuntu - Étape 2 (Logique optimisée et parallèle - Passe unique)
"""

import os
import sys
import shutil
import subprocess
import json
import logging
from pathlib import Path
from datetime import datetime
import concurrent.futures
import threading

# --- Configuration ---
WORK_DIR = Path(os.getcwd())
TARGET_FPS = 25.0
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv')
MAX_GPU_WORKERS = 3
FFMPEG_PATH = "ffmpeg"
FFPROBE_PATH = "ffprobe"

PROGRESS_LOCK = threading.Lock()
COMPLETED_VIDEOS = 0
TOTAL_VIDEOS_COUNT = 0

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
LOG_DIR = BASE_DIR / "logs" / "step2"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"convert_videos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)


def _parse_ffprobe_fraction(value: str):
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
    except Exception:
        return None


def _parse_ffprobe_fps(payload: dict):
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
        except Exception:
            pass
            
        try:
            if duration_raw not in (None, "N/A", ""):
                duration = float(duration_raw)
        except Exception:
            pass

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
    except Exception:
        return None


def analyze_video(video_path: Path):
    """Analyse le framerate et le codec audio d'une vidéo."""
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
        
        audio_codec = None
        streams = payload.get("streams", [])
        for s in streams:
            if s.get("codec_type") == "audio":
                audio_codec = s.get("codec_name")
                break
                
        return {
            'path': video_path,
            'fps': fps,
            'audio_codec': audio_codec,
            'needs_fps_fix': fps is not None and abs(fps - TARGET_FPS) > 0.1,
            'error': None
        }
    except Exception as e:
        logging.exception(f"Impossible d'analyser {video_path.name}: {e}")
        return {
            'path': video_path,
            'fps': None,
            'audio_codec': None,
            'needs_fps_fix': False,
            'error': str(e)
        }


def find_and_analyze_videos():
    """Trouve et analyse toutes les vidéos à traiter dans le répertoire de travail en parallèle."""
    videos_to_check = []
    logging.info(f"Recherche de vidéos ({', '.join(VIDEO_EXTENSIONS)}) dans {WORK_DIR}...")

    for root, _, files in os.walk(WORK_DIR):
        for file in files:
            if "_temp_conversion" in file or "_converted" in file or ".temp_compress" in file:
                continue
            if file.lower().endswith(VIDEO_EXTENSIONS):
                videos_to_check.append(Path(root) / file)

    logging.info(f"{len(videos_to_check)} vidéo(s) trouvée(s). Analyse FFprobe en parallèle...")
    
    analyzed_videos = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(analyze_video, path): path for path in videos_to_check}
        for future in concurrent.futures.as_completed(futures):
            analyzed_videos.append(future.result())
            
    videos_to_process = [v for v in analyzed_videos if v['error'] is None]
    return videos_to_process


def process_single_video(video_info, use_gpu=True, is_fallback=False):
    """Convertit et compresse une seule vidéo en une seule passe."""
    global COMPLETED_VIDEOS
    
    video_path = video_info['path']
    needs_fps_fix = video_info['needs_fps_fix']
    audio_codec = video_info['audio_codec']
    
    worker_type = 'GPU' if use_gpu else 'CPU'
    
    if not is_fallback:
        with PROGRESS_LOCK:
            COMPLETED_VIDEOS += 1
            current_index = COMPLETED_VIDEOS
            msg = f"--- Traitement de la vidéo ({current_index}/{TOTAL_VIDEOS_COUNT}): {video_path.name} ---"
            logging.info(msg)
            print(msg)

    try:
        fps_str = f"{video_info['fps']:.2f}" if video_info['fps'] is not None else "Inconnu"
        logging.info(f"Traitement ({worker_type}) démarré pour {video_path.name} (FPS={fps_str}, Audio={audio_codec})")
        
        temp_output_path = video_path.with_suffix(f".temp_conversion.mp4")

        command = [FFMPEG_PATH, '-y', '-hide_banner']
        
        if use_gpu:
            command.extend(['-hwaccel', 'cuda'])
            
        command.extend(['-i', str(video_path)])

        if needs_fps_fix:
            command.extend(['-vf', f'fps={TARGET_FPS}'])

        if use_gpu:
            command.extend(['-c:v', 'h264_nvenc', '-preset', 'p5', '-tune', 'hq', '-cq', '28', '-pix_fmt', 'yuv420p'])
        else:
            command.extend(['-c:v', 'libx264', '-preset', 'medium', '-crf', '28', '-pix_fmt', 'yuv420p'])

        if audio_codec in ['aac', 'mp3', 'ac3']:
            command.extend(['-c:a', 'copy'])
        else:
            command.extend(['-c:a', 'aac', '-b:a', '192k'])

        command.append(str(temp_output_path))

        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8')

        if result.returncode != 0:
            logging.error(f"Erreur FFmpeg ({worker_type}) pour {video_path.name}.\nStderr: {result.stderr.strip()}")
            if temp_output_path.exists(): temp_output_path.unlink()
            return False

        final_dest = video_path.with_suffix('.mp4')
        if final_dest != video_path and video_path.exists():
            video_path.unlink()
            
        shutil.move(str(temp_output_path), str(final_dest))
        logging.info(f"Succès ({worker_type}): {video_path.name} a été traité (Compression + FPS si nécessaire).")
        return True

    except Exception as e:
        logging.error(f"Erreur inattendue dans le worker ({worker_type}) pour {video_path.name}: {e}")
        return False


def process_video_with_fallback(video_info):
    """Tente un traitement GPU. S'il échoue, tente un traitement CPU (Fallback)."""
    success = process_single_video(video_info, use_gpu=True, is_fallback=False)
    if not success:
        logging.warning(f"Fallback CPU déclenché pour {video_info['path'].name}")
        success = process_single_video(video_info, use_gpu=False, is_fallback=True)
    return success


def main():
    global TOTAL_VIDEOS_COUNT, COMPLETED_VIDEOS

    logging.info("--- Démarrage du script de conversion vidéo (Optimisé) ---")

    try:
        subprocess.run([FFMPEG_PATH, "-version"], capture_output=True, check=True)
        subprocess.run([FFPROBE_PATH, "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        logging.critical("ffmpeg ou ffprobe n'est pas installé ou non accessible dans le PATH. Arrêt.")
        sys.exit(1)

    videos = find_and_analyze_videos()
    total_videos = len(videos)
    TOTAL_VIDEOS_COUNT = total_videos
    COMPLETED_VIDEOS = 0

    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")
    print(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")

    if total_videos == 0:
        logging.info("Aucune vidéo à traiter. Fin du script.")
        return

    logging.info(f"Lancement du pool de traitement ({MAX_GPU_WORKERS} workers GPU max) pour {total_videos} vidéo(s).")
    
    total_successful = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_GPU_WORKERS) as executor:
        futures = [executor.submit(process_video_with_fallback, v) for v in videos]
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                total_successful += 1

    logging.info("--- Traitement de toutes les vidéos terminé ---")
    logging.info(f"Résumé: {total_successful}/{total_videos} traitement(s) réussi(s).")

    if total_successful < total_videos:
        sys.exit(1)


if __name__ == "__main__":
    main()