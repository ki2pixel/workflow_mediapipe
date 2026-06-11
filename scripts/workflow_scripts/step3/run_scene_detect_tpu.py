#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'analyse des transitions vidéo avec MobileNetV2 INT8 (Google Coral Edge TPU)
Version Ubuntu - Étape 3 (Alternative à TransNetV2)
"""

import os
import sys
import csv
import argparse
import logging
import json
import urllib.request
import subprocess
import numpy as np
from pathlib import Path
from datetime import datetime
import multiprocessing as mp

# Gestion des dépendances TPU
try:
    from pycoral.utils import edgetpu
    from pycoral.adapters import common
    import tflite_runtime.interpreter as tflite
except ImportError as e:
    logging.critical(f"ERREUR: Les bibliothèques Coral/TFLite ne sont pas installées dans coral_env: {e}")
    sys.exit(1)

# --- Configuration ---
WORK_DIR = Path(os.getcwd())
VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent

# --- Configuration du Logger ---
LOG_DIR = BASE_DIR / "logs" / "step3"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"tpu_scenedetect_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

MODEL_URL = "https://github.com/google-coral/edgetpu/raw/master/test_data/mobilenet_v2_1.0_224_quant_edgetpu.tflite"

def format_timecode(frame_num: int, fps: float) -> str:
    """Format frame number to HH:MM:SS:FF"""
    total_seconds = frame_num / fps
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    frames = int((total_seconds - int(total_seconds)) * fps)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"

def download_model_if_needed(model_path: Path):
    if not model_path.exists():
        logging.info(f"Téléchargement du modèle TPU ({model_path.name})...")
        model_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(MODEL_URL, str(model_path))
        logging.info("Téléchargement terminé.")

def compute_cosine_distance(v1, v2):
    """Calcul de distance cosinus vectorisée entre deux embeddings"""
    if np.all(v1 == 0) or np.all(v2 == 0):
        return 0.0
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    return 1.0 - (dot_product / (norm_v1 * norm_v2))

def temporal_smoothing(distances, window_size=3):
    """
    Lissage temporel personnalisé sur CPU.
    Applique un filtre médian glissant pour réduire le bruit (jittering INT8).
    """
    if len(distances) < window_size:
        return distances
    smoothed = np.copy(distances)
    pad = window_size // 2
    for i in range(pad, len(distances) - pad):
        smoothed[i] = np.median(distances[i - pad:i + pad + 1])
    return smoothed

def detect_scenes_tpu(video_path, interpreter, threshold, min_scene_len=12, fps=25.0):
    """
    Détecte les scènes en utilisant MobileNetV2 sur l'Edge TPU.
    Lit la vidéo via ffmpeg subprocess, effectue l'inférence frame par frame,
    calcule la distance cosinus et applique le lissage temporel.
    """
    try:
        # Configuration des entrées TFLite
        input_details = interpreter.get_input_details()[0]
        output_details = interpreter.get_output_details()[0]
        
        # Le MobileNetV2 EdgeTPU prend du 224x224 RGB
        _, height, width, _ = input_details['shape']
        
        # Lancement de ffmpeg pour extraire les frames 224x224 RGB à 25 FPS
        command = [
            'ffmpeg',
            '-i', str(video_path),
            '-f', 'image2pipe',
            '-pix_fmt', 'rgb24',
            '-s', f'{width}x{height}',
            '-r', str(fps),
            '-vcodec', 'rawvideo',
            '-loglevel', 'error',
            '-'
        ]
        
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10**8)
        
        frame_size = width * height * 3
        embeddings = []
        
        frame_idx = 0
        logging.info(f"Démarrage de l'inférence TPU pour {video_path.name}")
        
        while True:
            raw_image = process.stdout.read(frame_size)
            if len(raw_image) != frame_size:
                break
                
            image = np.frombuffer(raw_image, dtype=np.uint8).reshape((height, width, 3))
            
            # Inférence Edge TPU
            # MobileNetV2 quantizé attend du uint8 [1, 224, 224, 3]
            common.set_input(interpreter, image)
            interpreter.invoke()
            
            # Récupérer les logits (vecteur de 1000 features pour classification)
            # On utilise ça comme empreinte/embedding de la scène
            output = common.output_tensor(interpreter, 0).copy()
            
            # Cast en float32 pour le calcul de distance CPU
            embeddings.append(output.astype(np.float32))
            
            frame_idx += 1
            if frame_idx % 500 == 0:
                # Format requis pour le pattern interne "INTERNAL_PROGRESS: x batches - file"
                logging.info(f"INTERNAL_PROGRESS: {frame_idx} batches - {video_path.name}")
                print(f"INTERNAL_PROGRESS: {frame_idx} batches - {video_path.name}")
                
        process.stdout.close()
        process.wait()
        
        if not embeddings:
            logging.warning(f"Aucune frame lue pour {video_path.name}")
            return []
            
        total_frames = len(embeddings)
        logging.info(f"Extraction terminée pour {video_path.name}. Total frames: {total_frames}. Calcul des distances...")
        
        # Calcul des distances cosinus consécutives
        distances = np.zeros(total_frames)
        for i in range(1, total_frames):
            distances[i] = compute_cosine_distance(embeddings[i-1], embeddings[i])
            
        # Lissage temporel
        smoothed_distances = temporal_smoothing(distances, window_size=5)
        
        # Détection des pics (Cuts)
        cut_indices = []
        last_cut = 0
        
        for i in range(1, total_frames - 1):
            if smoothed_distances[i] > threshold:
                # Vérifier si c'est un pic local
                if smoothed_distances[i] > smoothed_distances[i-1] and smoothed_distances[i] > smoothed_distances[i+1]:
                    # Vérifier min_scene_len
                    if (i - last_cut) >= min_scene_len:
                        cut_indices.append(i)
                        last_cut = i
                        
        # Générer les couples [start_frame, end_frame]
        scenes = []
        current_start = 0
        for cut in cut_indices:
            scenes.append([current_start, cut])
            current_start = cut + 1
            
        if current_start < total_frames:
            scenes.append([current_start, total_frames - 1])
            
        return scenes
        
    except Exception as e:
        logging.exception(f"Erreur TPU sur {video_path.name}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Analyse des transitions vidéo Edge TPU (MobileNetV2 Siamois).")
    parser.add_argument("--config", type=str, help="Fichier de configuration JSON")
    args = parser.parse_args()

    # Paramètres par défaut
    threshold = 0.25 # Distance cosinus critique
    min_scene_len = 12 # 0.5s à 25fps

    if args.config and Path(args.config).exists():
        with open(args.config, 'r') as f:
            cfg = json.load(f)
            threshold = cfg.get("threshold", threshold)

    logging.info("--- Démarrage de l'analyse TPU (MobileNetV2 INT8 Siamois) ---")

    # Initialisation TPU
    model_path = BASE_DIR / "assets" / "mobilenet_v2_1.0_224_quant_edgetpu.tflite"
    download_model_if_needed(model_path)
    
    try:
        # Load the Edge TPU delegate
        delegate = edgetpu.load_delegate()
        interpreter = tflite.Interpreter(model_path=str(model_path), experimental_delegates=[delegate])
        interpreter.allocate_tensors()
        logging.info("Modèle Edge TPU chargé avec succès.")
    except Exception as e:
        logging.critical(f"Impossible d'initialiser l'Edge TPU. Vérifiez la connexion USB/PCIe et les permissions: {e}")
        sys.exit(1)

    videos = [p for ext in VIDEO_EXTENSIONS for p in WORK_DIR.rglob(f'*{ext}') if not p.with_suffix('.csv').exists()]
    total_videos = len(videos)
    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")
    print(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")

    if total_videos == 0:
        return

    successful_count = 0
    for idx, video_path in enumerate(videos):
        logging.info(f"PROCESSING_VIDEO: {video_path.name}")
        print(f"PROCESSING_VIDEO: {video_path.name}")
        
        scenes = detect_scenes_tpu(video_path, interpreter, threshold=threshold, min_scene_len=min_scene_len)
        
        if scenes is not None:
            # Écriture CSV
            output_csv_path = video_path.with_suffix('.csv')
            with open(output_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['No', 'Timecode In', 'Timecode Out', 'Frame In', 'Frame Out'])
                for j, (start, end) in enumerate(scenes):
                    tc_in = format_timecode(start, 25.0)
                    tc_out = format_timecode(end, 25.0)
                    writer.writerow([j + 1, tc_in, tc_out, start + 1, end + 1])
                    
            logging.info(f"Succès: {output_csv_path.name} créé avec {len(scenes)} scènes.")
            print(f"Succès: {output_csv_path.name} créé avec {len(scenes)} scènes.")
            successful_count += 1
        else:
            logging.error(f"Échec de l'analyse pour {video_path.name}")

    logging.info(f"--- Analyse terminée. {successful_count}/{total_videos} réussie(s). ---")
    if successful_count < total_videos:
        sys.exit(1)

if __name__ == "__main__":
    main()
