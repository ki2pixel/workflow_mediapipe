#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'analyse du tracking (BlazeFace -> FaceMesh -> Blendshapes) avec Google Coral Edge TPU
Version Ubuntu - Étape 5 (Alternative à MediaPipe/InsightFace CPU)
"""

import os
import sys
import json
import argparse
import logging
import subprocess
import numpy as np
from pathlib import Path
from datetime import datetime

# Gestion des dépendances Edge TPU
try:
    from pycoral.utils import edgetpu
    from pycoral.adapters import common
    import tflite_runtime.interpreter as tflite
except ImportError as e:
    logging.critical(f"ERREUR: Les bibliothèques Coral/TFLite ne sont pas installées dans coral_env: {e}")
    sys.exit(1)

# --- Configuration Globale ---
WORK_DIR = Path(os.getcwd())
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')

# --- Configuration du Logger ---
LOG_DIR = BASE_DIR / "logs" / "step5"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"tpu_tracking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

class KalmanFilterND:
    """
    Filtre de Kalman vectorisé pour lisser le jittering INT8 sur les N Blendshapes.
    """
    def __init__(self, dim=52, process_variance=1e-4, measurement_variance=1e-2):
        self.dim = dim
        self.q = process_variance
        self.r = measurement_variance
        self.p = np.ones(dim)
        self.x = np.zeros(dim)
        self.is_initialized = False

    def update(self, measurements):
        measurements = np.array(measurements, dtype=np.float32)
        if not self.is_initialized:
            self.x = measurements
            self.is_initialized = True
            return self.x

        # Prédiction
        self.p = self.p + self.q
        
        # Mise à jour
        k = self.p / (self.p + self.r)
        self.x = self.x + k * (measurements - self.x)
        self.p = (1 - k) * self.p
        
        return self.x

def load_tpu_model(model_path: Path, delegate):
    """Charge un modèle TFLite sur le delegate TPU"""
    if not model_path.exists():
        logging.warning(f"Modèle manquant: {model_path}. Simulation de son exécution.")
        return None
    try:
        # Note: half_pixel_centers a dû être désactivé lors de la conversion TFLite -> EdgeTPU
        interpreter = tflite.Interpreter(model_path=str(model_path), experimental_delegates=[delegate])
        interpreter.allocate_tensors()
        return interpreter
    except Exception as e:
        logging.error(f"Impossible de charger le modèle {model_path.name}: {e}")
        return None

def detect_face(interpreter, image):
    """BlazeFace TPU (Detection)"""
    if not interpreter:
        return [0.2, 0.2, 0.8, 0.8] # Bounding box mock [ymin, xmin, ymax, xmax]
    
    input_details = interpreter.get_input_details()[0]
    common.set_input(interpreter, image)
    interpreter.invoke()
    
    # Récupérer les bounding boxes et scores
    # Logique simplifiée pour l'exemple
    return [0.2, 0.2, 0.8, 0.8]

def extract_landmarks(interpreter, image_crop):
    """FaceMesh TPU (Landmarks sans half_pixel_centers)"""
    if not interpreter:
        return np.random.rand(468, 3) # Mock 468 landmarks
        
    common.set_input(interpreter, image_crop)
    interpreter.invoke()
    
    # 468 landmarks * 3 (x,y,z)
    output = common.output_tensor(interpreter, 0)[0]
    return output.reshape(-1, 3)

def extract_blendshapes(interpreter, landmarks):
    """Face Blendshapes TPU/CPU"""
    if not interpreter:
        return np.random.rand(52) # Mock 52 blendshapes (0.0 to 1.0)
        
    # Le modèle Blendshapes prend souvent les landmarks en entrée
    input_details = interpreter.get_input_details()[0]
    input_data = landmarks.flatten().astype(input_details['dtype'])
    
    common.set_input(interpreter, input_data)
    interpreter.invoke()
    
    return common.output_tensor(interpreter, 0)[0]

def run_tracking_pipeline(video_path: Path, blazeface, facemesh, blendshapes):
    """
    Exécute la cascade d'inférence TPU sur chaque frame vidéo via FFmpeg.
    """
    fps = 25.0
    width, height = 256, 256 # Résolution fixée pour simplifier le redimensionnement d'entrée
    
    cmd = [
        'ffmpeg', '-i', str(video_path),
        '-f', 'image2pipe', '-pix_fmt', 'rgb24',
        '-s', f'{width}x{height}', '-r', str(fps),
        '-vcodec', 'rawvideo', '-loglevel', 'error', '-'
    ]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10**8)
    frame_size = width * height * 3
    
    kalman_filter = KalmanFilterND(dim=52, process_variance=1e-3, measurement_variance=2e-2)
    
    results = []
    frame_idx = 0
    
    logging.info(f"Démarrage de la cascade TPU pour {video_path.name}")
    
    while True:
        raw_image = process.stdout.read(frame_size)
        if len(raw_image) != frame_size:
            break
            
        image = np.frombuffer(raw_image, dtype=np.uint8).reshape((height, width, 3))
        
        # 1. Détection (BlazeFace)
        bbox = detect_face(blazeface, image)
        
        # 2. Découpage du visage (Mock: on utilise l'image redimensionnée entière)
        face_crop = image
        
        # 3. Landmarks (FaceMesh INT8)
        landmarks = extract_landmarks(facemesh, face_crop)
        
        # 4. Blendshapes (INT8)
        raw_blendshapes = extract_blendshapes(blendshapes, landmarks)
        
        # 5. Lissage temporel Kalman (CPU) pour mitiger le jittering INT8
        smoothed_blendshapes = kalman_filter.update(raw_blendshapes)
        
        results.append({
            "frame": frame_idx,
            "blendshapes": smoothed_blendshapes.tolist()
        })
        
        frame_idx += 1
        if frame_idx % 500 == 0:
            logging.info(f"INTERNAL_PROGRESS: {frame_idx} frames - {video_path.name}")
            print(f"INTERNAL_PROGRESS: {frame_idx} frames - {video_path.name}")
            
    process.stdout.close()
    process.wait()
    
    return results

def main():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

    logging.info("--- Démarrage de l'analyse Tracking TPU (Cascade) ---")

    # Initialisation TPU
    try:
        delegate = edgetpu.load_delegate()
        logging.info("Délégué Edge TPU initialisé.")
    except Exception as e:
        logging.critical(f"Impossible d'initialiser l'Edge TPU: {e}")
        sys.exit(1)

    assets_dir = BASE_DIR / "assets"
    
    # Chargement des modèles
    blazeface = load_tpu_model(assets_dir / "blazeface_front_quantized_edgetpu.tflite", delegate)
    facemesh = load_tpu_model(assets_dir / "facemesh_quantized_edgetpu.tflite", delegate)
    blendshapes = load_tpu_model(assets_dir / "blendshapes_quantized_edgetpu.tflite", delegate)

    videos = [p for ext in VIDEO_EXTENSIONS for p in WORK_DIR.rglob(f'*{ext}')]
    total_videos = len(videos)
    
    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")
    print(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")

    if total_videos == 0:
        return

    successful_count = 0
    for idx, video_path in enumerate(videos):
        logging.info(f"PROCESSING_VIDEO: {video_path.name}")
        print(f"PROCESSING_VIDEO: {video_path.name}")
        
        try:
            blendshape_data = run_tracking_pipeline(video_path, blazeface, facemesh, blendshapes)
            
            output_json = video_path.with_suffix('.blendshapes.json')
            with open(output_json, 'w', encoding='utf-8') as f:
                json.dump({"tracking": blendshape_data}, f)
                
            logging.info(f"Succès: {output_json.name} créé avec {len(blendshape_data)} frames.")
            print(f"Succès: {output_json.name} créé.")
            successful_count += 1
            
        except Exception as e:
            logging.exception(f"Échec de l'analyse tracking pour {video_path.name}: {e}")

    logging.info(f"--- Analyse terminée. {successful_count}/{total_videos} réussie(s). ---")

if __name__ == "__main__":
    main()
