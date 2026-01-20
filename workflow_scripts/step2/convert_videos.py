#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de conversion vidéo pour le workflow de traitement
Version Ubuntu - Étape 2 (Logique optimisée et parallèle)
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
import queue
import time

# --- Configuration ---
WORK_DIR = Path(os.getcwd())
TARGET_FPS = 25.0
VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.wmv')
MAX_CPU_WORKERS = max(1, os.cpu_count() - 2)
FFMPEG_PATH = "ffmpeg"
FFPROBE_PATH = "ffprobe"

# GPU worker queue system for continuous processing
GPU_QUEUE = queue.Queue()
GPU_RESULTS_QUEUE = queue.Queue()
GPU_WORKER_SHUTDOWN = threading.Event()
PROGRESS_LOCK = threading.Lock()
COMPLETED_VIDEOS = 0
TOTAL_VIDEOS_COUNT = 0
COMPRESS_COMPLETED = 0
COMPRESS_TOTAL = 0

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
        stream = streams[0] or {}

        avg_fps = _parse_ffprobe_fraction(stream.get("avg_frame_rate"))
        r_fps = _parse_ffprobe_fraction(stream.get("r_frame_rate"))

        nb_frames_raw = stream.get("nb_frames")
        duration_raw = stream.get("duration")
        nb_frames = None
        duration = None
        try:
            if nb_frames_raw not in (None, "N/A", ""):
                nb_frames = int(float(nb_frames_raw))
        except Exception:
            nb_frames = None
        try:
            if duration_raw not in (None, "N/A", ""):
                duration = float(duration_raw)
        except Exception:
            duration = None

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


def get_video_framerate(video_path):
    """Récupère le framerate effectif d'une vidéo."""
    try:
        command = [
            FFPROBE_PATH, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=avg_frame_rate,r_frame_rate,nb_frames,duration",
            "-of", "json",
            str(video_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        payload = json.loads(result.stdout or "{}")
        fps = _parse_ffprobe_fps(payload)
        if fps is None:
            raise ValueError("ffprobe fps parse returned None")
        return fps
    except Exception as e:
        logging.error(f"Impossible de lire le framerate de {video_path.name}: {e}")
        return None


def find_videos_to_convert():
    """Trouve toutes les vidéos à convertir dans le répertoire de travail."""
    videos_to_check = []
    logging.info(f"Recherche de vidéos ({', '.join(VIDEO_EXTENSIONS)}) dans {WORK_DIR}...")

    for root, _, files in os.walk(WORK_DIR):
        for file in files:
            if "_temp_conversion" in file or "_converted" in file:
                continue
            if file.lower().endswith(VIDEO_EXTENSIONS):
                videos_to_check.append(Path(root) / file)

    logging.info(f"{len(videos_to_check)} vidéo(s) trouvée(s). Vérification du framerate...")

    videos_requiring_conversion = []
    for video_path in videos_to_check:
        current_fps = get_video_framerate(video_path)
        if current_fps is not None and abs(current_fps - TARGET_FPS) > 0.1:
            logging.info(f"Conversion requise pour {video_path.name} (FPS actuel: {current_fps:.2f})")
            videos_requiring_conversion.append(video_path)
        elif current_fps is not None:
            logging.info(f"Conversion non requise pour {video_path.name} (FPS actuel: {current_fps:.2f})")

    return videos_requiring_conversion


def find_mp4_videos():
    """Liste toutes les vidéos .mp4 à compresser (exclut les fichiers temporaires)."""
    mp4_videos = []
    logging.info(f"Recherche des vidéos .mp4 dans {WORK_DIR} pour compression…")

    for root, _, files in os.walk(WORK_DIR):
        for file in files:
            if "_temp_conversion" in file or "_converted" in file or ".temp_compress" in file:
                continue
            if file.lower().endswith('.mp4'):
                mp4_videos.append(Path(root) / file)

    logging.info(f"{len(mp4_videos)} fichier(s) .mp4 détecté(s) pour la compression.")
    return mp4_videos


def convert_single_video(video_path, use_gpu=False):
    """Convertit une seule vidéo avec l'encodeur spécifié."""
    worker_type = 'GPU' if use_gpu else 'CPU'

    try:
        logging.info(f"Conversion ({worker_type}) démarrée pour {video_path.name}")

        temp_output_path = video_path.with_suffix(f".temp_conversion{video_path.suffix}")

        command = [FFMPEG_PATH, '-y', '-hide_banner', '-i', str(video_path), '-vf', f'fps={TARGET_FPS}']

        if use_gpu:
            command.extend(['-c:v', 'h264_nvenc', '-preset', 'p5', '-tune', 'hq', '-cq', '23', '-pix_fmt', 'yuv420p'])
        else:
            command.extend(['-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-pix_fmt', 'yuv420p'])

        command_with_audio_copy = command + ['-c:a', 'copy', str(temp_output_path)]

        result = subprocess.run(command_with_audio_copy, capture_output=True, text=True, check=False, encoding='utf-8')

        if result.returncode != 0:
            logging.warning(f"La copie audio a échoué pour {video_path.name}, tentative de ré-encodage audio...")
            command_with_audio_reencode = command + ['-c:a', 'aac', '-b:a', '192k', str(temp_output_path)]
            result = subprocess.run(command_with_audio_reencode, capture_output=True, text=True, check=False,
                                    encoding='utf-8')

        if result.returncode != 0:
            logging.error(f"Erreur FFmpeg ({worker_type}) pour {video_path.name}.\nStderr: {result.stderr.strip()}")
            if temp_output_path.exists(): temp_output_path.unlink()
            return False

        shutil.move(str(temp_output_path), str(video_path))
        logging.info(f"Succès ({worker_type}): {video_path.name} a été converti et mis à jour.")
        return True

    except Exception as e:
        logging.error(f"Erreur inattendue dans le worker ({worker_type}) pour {video_path.name}: {e}")
        return False


def compress_single_video(video_path, use_gpu=False):
    """Compresse une vidéo .mp4 sans changer la résolution ni le framerate.

    Utilise des paramètres FFmpeg conservateurs pour réduire la taille tout en préservant la qualité visuelle.
    - GPU: h264_nvenc avec cq=28 (qualité élevée, réduction notable)
    - CPU: libx264 avec crf=28
    L'audio est copié si possible, sinon ré-encodé en AAC 192k.
    """
    worker_type = 'GPU' if use_gpu else 'CPU'

    try:
        logging.info(f"Compression ({worker_type}) démarrée pour {video_path.name}")

        temp_output_path = video_path.with_suffix(f".temp_compress{video_path.suffix}")

        command = [FFMPEG_PATH, '-y', '-hide_banner', '-i', str(video_path)]

        if use_gpu:
            command.extend(['-c:v', 'h264_nvenc', '-preset', 'p5', '-tune', 'hq', '-cq', '28', '-pix_fmt', 'yuv420p'])
        else:
            command.extend(['-c:v', 'libx264', '-preset', 'medium', '-crf', '28', '-pix_fmt', 'yuv420p'])

        command_with_audio_copy = command + ['-c:a', 'copy', str(temp_output_path)]
        result = subprocess.run(command_with_audio_copy, capture_output=True, text=True, check=False, encoding='utf-8')

        if result.returncode != 0:
            logging.warning(f"La copie audio a échoué pour {video_path.name}, tentative de ré-encodage audio…")
            command_with_audio_reencode = command + ['-c:a', 'aac', '-b:a', '192k', str(temp_output_path)]
            result = subprocess.run(command_with_audio_reencode, capture_output=True, text=True, check=False, encoding='utf-8')

        if result.returncode != 0:
            logging.error(f"Erreur FFmpeg ({worker_type}) lors de la compression de {video_path.name}.\nStderr: {result.stderr.strip()}")
            if temp_output_path.exists():
                try:
                    temp_output_path.unlink()
                except Exception:
                    pass
            return False

        shutil.move(str(temp_output_path), str(video_path))
        logging.info(f"Succès ({worker_type}): {video_path.name} a été compressé.")
        return True

    except Exception as e:
        logging.error(f"Erreur inattendue dans le worker ({worker_type}) pour {video_path.name} (compression): {e}")
        return False



def gpu_worker_thread():
    """Thread dédié pour le traitement GPU continu."""
    global COMPLETED_VIDEOS

    logging.info("GPU worker thread démarré")

    while not GPU_WORKER_SHUTDOWN.is_set():
        try:
            video_path = GPU_QUEUE.get(timeout=1.0)

            with PROGRESS_LOCK:
                current_index = COMPLETED_VIDEOS + 1
                logging.info(f"--- Traitement de la vidéo ({current_index}/{TOTAL_VIDEOS_COUNT}): {video_path.name} ---")
                print(f"--- Traitement de la vidéo ({current_index}/{TOTAL_VIDEOS_COUNT}): {video_path.name} ---")

            success = convert_single_video(video_path, use_gpu=True)

            GPU_RESULTS_QUEUE.put((success, video_path))

            with PROGRESS_LOCK:
                COMPLETED_VIDEOS += 1

            GPU_QUEUE.task_done()

        except queue.Empty:
            continue
        except Exception as e:
            logging.error(f"Erreur dans le GPU worker thread: {e}")
            try:
                GPU_QUEUE.task_done()
            except ValueError:
                pass

    logging.info("GPU worker thread terminé")


def gpu_compress_worker_thread():
    """Thread dédié pour la compression GPU séquentielle."""
    global COMPRESS_COMPLETED

    logging.info("GPU compression worker thread démarré")

    while not GPU_WORKER_SHUTDOWN.is_set():
        try:
            video_path = GPU_QUEUE.get(timeout=1.0)

            # Émission d'une ligne de progression compatible STEP2 avant traitement (compression)
            with PROGRESS_LOCK:
                current_index = COMPRESS_COMPLETED + 1
                logging.info(f"--- Traitement de la vidéo ({current_index}/{COMPRESS_TOTAL}): {video_path.name} ---")
                print(f"--- Traitement de la vidéo ({current_index}/{COMPRESS_TOTAL}): {video_path.name} ---")

            success = compress_single_video(video_path, use_gpu=True)

            GPU_RESULTS_QUEUE.put((success, video_path))

            with PROGRESS_LOCK:
                COMPRESS_COMPLETED += 1

            GPU_QUEUE.task_done()

        except queue.Empty:
            continue
        except Exception as e:
            logging.error(f"Erreur dans le GPU compression worker thread: {e}")
            try:
                GPU_QUEUE.task_done()
            except ValueError:
                pass

    logging.info("GPU compression worker thread terminé")




def main():
    global TOTAL_VIDEOS_COUNT, COMPLETED_VIDEOS, COMPRESS_TOTAL, COMPRESS_COMPLETED

    logging.info("--- Démarrage du script de conversion vidéo ---")

    try:
        subprocess.run([FFMPEG_PATH, "-version"], capture_output=True, check=True)
        subprocess.run([FFPROBE_PATH, "-version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        logging.critical("ffmpeg ou ffprobe n'est pas installé ou non accessible dans le PATH. Arrêt.")
        sys.exit(1)

    videos = find_videos_to_convert()
    total_videos = len(videos)
    TOTAL_VIDEOS_COUNT = total_videos
    COMPLETED_VIDEOS = 0

    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")
    print(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")

    if total_videos == 0:
        logging.info("Aucune vidéo à convertir. Passage direct à la compression.")

    total_successful = 0
    if total_videos > 0:
        gpu_videos = videos
        cpu_videos = []

        logging.info(f"Allocation GPU exclusive: {len(gpu_videos)} vidéo(s) pour traitement GPU séquentiel")

        logging.info(f"Lancement de la conversion avec 1 worker GPU dédié pour traitement séquentiel.")
        gpu_thread = threading.Thread(target=gpu_worker_thread, name='GPU-Worker', daemon=True)
        gpu_thread.start()

        for video in gpu_videos:
            GPU_QUEUE.put(video)

        GPU_QUEUE.join()

        gpu_successful_count = 0
        while not GPU_RESULTS_QUEUE.empty():
            try:
                success, video_path = GPU_RESULTS_QUEUE.get_nowait()
                if success:
                    gpu_successful_count += 1
            except queue.Empty:
                break

        GPU_WORKER_SHUTDOWN.set()
        gpu_thread.join(timeout=5.0)

        total_successful = gpu_successful_count

        logging.info("--- Conversion de toutes les vidéos terminée ---")
        logging.info(f"Résumé: {total_successful}/{total_videos} conversion(s) réussie(s) (traitement GPU exclusif).")

    mp4_videos = find_mp4_videos()
    COMPRESS_TOTAL = len(mp4_videos)
    COMPRESS_COMPLETED = 0

    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {COMPRESS_TOTAL} (compression)")
    print(f"TOTAL_VIDEOS_TO_PROCESS: {COMPRESS_TOTAL}")

    if COMPRESS_TOTAL == 0:
        logging.info("Aucune vidéo .mp4 à compresser. Fin du script.")
        if total_successful < total_videos:
            sys.exit(1)
        return

    GPU_WORKER_SHUTDOWN.clear()
    gpu_compress_thread = threading.Thread(target=gpu_compress_worker_thread, name='GPU-Compress-Worker', daemon=True)
    gpu_compress_thread.start()

    for video in mp4_videos:
        GPU_QUEUE.put(video)

    GPU_QUEUE.join()

    compress_successful_count = 0
    while not GPU_RESULTS_QUEUE.empty():
        try:
            success, video_path = GPU_RESULTS_QUEUE.get_nowait()
            if success:
                compress_successful_count += 1
        except queue.Empty:
            break

    GPU_WORKER_SHUTDOWN.set()
    gpu_compress_thread.join(timeout=5.0)

    logging.info("--- Compression de toutes les vidéos .mp4 terminée ---")
    logging.info(f"Résumé: {compress_successful_count}/{COMPRESS_TOTAL} compression(s) réussie(s) (GPU séquentiel).")

    if total_successful < total_videos:
        sys.exit(1)


if __name__ == "__main__":
    main()