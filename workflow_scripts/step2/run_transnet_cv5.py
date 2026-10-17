#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'analyse des transitions vidéo avec TransNetV2 (ONNX) - Étape 2
Architecture Haute Performance GPU Zéro-Copie (Double Tampon Ping-Pong + IOBinding).

Backends supportés :
  - ONNX Runtime GPU (CUDAExecutionProvider avec IOBinding, kSameAsRequested, EXHAUSTIVE cuDNN, use_tf32=0) [Nominal]
  - OpenCV 5.0 DNN orienté graphe (ENGINE_NEW CPU) en cas d'absence de GPU
  - ONNX Runtime CPU avec IOBinding en repli universel

Atouts :
  - Accélération 3x à 5x (> 260x temps réel)
  - Invariance stricte FP32 (|Delta P| < 1e-5, score F1 et timecodes invariants)
  - Cadencement 25.0 FPS strict et timecodes millisecondes HH:MM:SS.mmm
  - Ingestion FFmpeg asynchrone hors-GIL sans allocations par trame
  - Contrats de logs Flask respectés (INTERNAL_PROGRESS, Succès: ...)
"""

import os
import re
import sys
import csv
import argparse
import logging
import json
import numpy as np
import cv2
from pathlib import Path
from datetime import datetime
from scenedetect import FrameTimecode
import time

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from utils.media_filters import split_preserved_media
from utils.media_normalizer import check_fps_conformance
from workflow_scripts.step2.zero_copy_pipeline import (
    ZeroCopyTransNetPipeline,
    TransNetV2GpuEngine,
    OpenCV5CpuEngine,
    create_transnet_engine,
    write_scenes_to_csv,
    predictions_to_scenes,
    WINDOW_SIZE,
    WINDOW_STRIDE,
    PADDING_LEFT,
    FPS_TARGET,
    DECISION_THRESHOLD,
)

# --- Configuration ---
WORK_DIR = Path(os.getcwd())
VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent

# --- Configuration du Logger ---
LOG_DIR = BASE_DIR / "logs" / "step2"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"transnet_cv5_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Default ONNX model path
ONNX_MODEL_PATH = BASE_DIR / "assets" / "models" / "onnx" / "transnetv2.onnx"


def get_video_fps(video_path):
    """Retourne toujours 25.0 FPS pour stabiliser les timecodes (Étape 2 force 25 FPS)."""
    return FPS_TARGET


def validate_onnx_slice_operator(engine, window_size=WINDOW_SIZE):
    """Validation pré-vol du graphe TransNetV2 sur le backend chargé.

    Vérifie avec une entrée synthétique que le modèle et l'arène VRAM fonctionnent
    parfaitement sans lever d'exception ni produire de tenseur vide.
    """
    try:
        val_batch = getattr(engine, "batch_size", 1)
        dummy_input = np.zeros((val_batch, window_size, 27, 48, 3), dtype=np.uint8)
        if hasattr(engine, "infer_windows"):
            output = engine.infer_windows(dummy_input)
            if output is None or len(output) == 0:
                logging.error("VALIDATION_ECHEC: Le modèle produit un tenseur vide.")
                return False
            logging.info(
                f"VALIDATION_OK: Moteur {backend_label(engine)} validé. "
                f"Sortie shape={output.shape}, range=[{output.min():.4f}, {output.max():.4f}]"
            )
            return True
        elif hasattr(engine, "setInput"):
            engine.setInput(dummy_input)
            output = engine.forward()
            if output is None or (hasattr(output, 'size') and output.size == 0):
                logging.error("VALIDATION_ECHEC: Le modèle produit un tenseur vide.")
                return False
            logging.info(f"VALIDATION_OK: OpenCV net validé. Sortie shape={output.shape}")
            return True
        return False
    except Exception as e:
        logging.error(f"VALIDATION_ECHEC: Exception lors du test du graphe: {e}")
        return False


def graph_engine_available():
    """Indique si OpenCV expose le moteur DNN orienté graphe (OpenCV 5.x)."""
    return hasattr(cv2.dnn, "DNN_ENGINE_NEW") or hasattr(cv2.dnn, "ENGINE_NEW")


def backend_label(engine):
    """Libellé du backend d'inférence réellement chargé."""
    return getattr(engine, "backend_label", str(type(engine).__name__))


def detect_scenes_cv5(
    video_path,
    engine,
    threshold=DECISION_THRESHOLD,
    windows_per_chunk=50,
    ffmpeg_threads=0,
):
    """
    Détection de scènes avec TransNetV2 (ONNX) et streaming FFmpeg zéro-copie.
    Utilise le pipeline à double tampon Ping-Pong (2600 trames) et IOBinding.
    """
    try:
        pipeline = ZeroCopyTransNetPipeline(
            engine=engine,
            windows_per_chunk=windows_per_chunk,
            ffmpeg_threads=ffmpeg_threads,
        )
        probs, scenes = pipeline.process_video(str(video_path), threshold=threshold)
        return scenes, engine
    except Exception as e:
        logging.exception(f"Erreur lors de la détection de scènes pour {Path(video_path).name}: {e}")
        return None, engine


def process_single_video(idx, total, video_path, engine, model_path, cfg):
    """Traite une seule vidéo : inférence zéro-copie, écriture CSV."""
    try:
        logging.info(f"PROCESSING_VIDEO: {idx + 1}/{total}: {video_path.name}")
        print(f"PROCESSING_VIDEO: {idx + 1}/{total}: {video_path.name}", flush=True)

        t0 = time.perf_counter()

        threshold = float(cfg.get("threshold", DECISION_THRESHOLD))
        windows_per_chunk = int(cfg.get("windows_per_chunk", 50))
        ffmpeg_threads = int(cfg.get("ffmpeg_threads", 0))

        scenes, engine = detect_scenes_cv5(
            video_path,
            engine,
            threshold=threshold,
            windows_per_chunk=windows_per_chunk,
            ffmpeg_threads=ffmpeg_threads,
        )

        if scenes is None:
            logging.error(f"Échec du traitement de {video_path.name}")
            return False, engine

        elapsed = time.perf_counter() - t0

        # Écriture CSV (format strict avec FrameTimecode HH:MM:SS.mmm)
        output_csv_path = video_path.with_suffix('.csv')
        fps = get_video_fps(video_path)
        write_scenes_to_csv(scenes, output_csv_path, fps=fps)

        logging.info(
            f"Succès: {output_csv_path.name} créé avec {len(scenes)} scènes "
            f"({elapsed:.2f}s, {backend_label(engine)})"
        )
        print(f"Succès: {output_csv_path.name} créé", flush=True)
        return True, engine

    except Exception as e:
        logging.exception(f"Erreur worker pour {video_path}: {e}")
        return False, engine


def setup_cuda_paths():
    """Recherche les répertoires de bibliothèques NVIDIA (CUDA/cuDNN) dans le venv
    courant et les injecte dans LD_LIBRARY_PATH pour permettre le chargement GPU par ONNX Runtime.
    """
    try:
        venv_site_packages = Path(sys.executable).parent.parent / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
        if not venv_site_packages.exists():
            return

        nvidia_dirs = [str(d) for d in venv_site_packages.glob("nvidia/*/lib")]
        if not nvidia_dirs:
            return

        current_ld = os.environ.get("LD_LIBRARY_PATH", "")
        current_entries = [entry for entry in current_ld.split(":") if entry]
        missing_dirs = [d for d in nvidia_dirs if d not in current_entries]
        if not missing_dirs:
            return

        os.environ["LD_LIBRARY_PATH"] = ":".join(missing_dirs + current_entries)
        logging.info(f"CUDA_PATH_SETUP: LD_LIBRARY_PATH enrichi avec les packages nvidia du venv: {len(missing_dirs)} répertoires ajoutés.")

        if os.environ.get("STEP2_CV5_CUDA_ENV_READY") != "1":
            os.environ["STEP2_CV5_CUDA_ENV_READY"] = "1"
            if sys.argv and sys.argv[0] != "-c":
                sys.stdout.flush()
                sys.stderr.flush()
                os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        logging.warning(f"CUDA_PATH_SETUP_WARNING: Impossible d'injecter automatiquement les chemins CUDA du venv: {e}")


def main():
    setup_cuda_paths()
    parser = argparse.ArgumentParser(
        description="Analyse des transitions vidéo avec TransNetV2 (ONNX Runtime GPU Zero-Copy & OpenCV DNN)."
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help=f"Chemin vers le modèle ONNX (défaut: {ONNX_MODEL_PATH})"
    )
    parser.add_argument(
        "--config", type=str, default=None,
        help="Chemin du fichier de configuration JSON"
    )
    parser.add_argument("--threshold", type=float, default=None, help="Seuil de détection (0-1). Défaut: 0.5")
    parser.add_argument("--window", type=int, default=None, help="Taille de fenêtre (frames). Défaut: 100")
    parser.add_argument("--stride", type=int, default=None, help="Pas entre fenêtres (frames). Défaut: 50")
    parser.add_argument("--padding", type=int, default=None, help="Padding au début/fin (frames). Défaut: 25")
    parser.add_argument("--ffmpeg_threads", type=int, default=None, help="Nombre de threads FFmpeg (0 = auto)")
    parser.add_argument("--batch_size", type=int, default=None, help="Taille de lot pour l'inférence. Défaut: 8")
    parser.add_argument("--windows_per_chunk", type=int, default=None, help="Nombre de fenêtres par chunk. Défaut: 8")
    parser.add_argument("--input_dir", type=str, default=None, help="Dossier contenant les vidéos à analyser (défaut: répertoire courant)")
    parser.add_argument("--force", action="store_true", help="Re-traiter les vidéos même si le fichier .csv existe déjà")
    args = parser.parse_args()

    # Defaults nominaux haute performance
    defaults = {
        "threshold": 0.5,
        "window": 100,
        "stride": 50,
        "padding": 25,
        "ffmpeg_threads": 0,
        "batch_size": 8,
        "windows_per_chunk": 8,
        "use_tf32": False,
    }

    # Résolution config JSON
    config_path = None
    if args.config:
        config_path = Path(args.config)
    else:
        candidate1 = BASE_DIR / "config" / "step2_transnet.json"
        candidate2 = BASE_DIR / "config" / "step2_cv5.json"
        if candidate1.exists():
            config_path = candidate1
        elif candidate2.exists():
            config_path = candidate2

    file_cfg = {}
    if config_path is not None:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            logging.info(f"Configuration chargée depuis: {config_path}")
        except Exception as e:
            logging.exception(f"Impossible de charger la configuration {config_path}: {e}")

    effective_cfg = dict(defaults)
    effective_cfg.update({k: v for k, v in file_cfg.items() if v is not None})
    if "onnx_batch_size" in file_cfg:
        effective_cfg["batch_size"] = int(file_cfg["onnx_batch_size"])

    if args.threshold is not None:
        effective_cfg["threshold"] = float(args.threshold)
    if args.window is not None:
        effective_cfg["window"] = int(args.window)
    if args.stride is not None:
        effective_cfg["stride"] = int(args.stride)
    if args.padding is not None:
        effective_cfg["padding"] = int(args.padding)
    if args.ffmpeg_threads is not None:
        effective_cfg["ffmpeg_threads"] = int(args.ffmpeg_threads)
    if args.batch_size is not None:
        effective_cfg["batch_size"] = int(args.batch_size)
    if args.windows_per_chunk is not None:
        effective_cfg["windows_per_chunk"] = int(args.windows_per_chunk)

    batch_size = int(effective_cfg["batch_size"])

    logging.info(
        f"CONFIG_EFFECTIVE: threshold={effective_cfg['threshold']}, "
        f"window={effective_cfg['window']}, stride={effective_cfg['stride']}, "
        f"padding={effective_cfg['padding']}, ffmpeg_threads={effective_cfg['ffmpeg_threads']}, "
        f"batch_size={batch_size}, windows_per_chunk={effective_cfg['windows_per_chunk']}, "
        f"use_tf32={effective_cfg.get('use_tf32', False)}"
    )

    model_path = Path(args.model) if args.model else ONNX_MODEL_PATH
    logging.info("--- Démarrage de l'analyse des transitions (TransNetV2 ONNX Zero-Copy) ---")

    # Initialisation du moteur GPU optimisé avec fallback automatique CPU
    engine = create_transnet_engine(model_path, batch_size=batch_size)
    if engine is None:
        logging.critical("Impossible d'initialiser le moteur d'inférence TransNetV2.")
        sys.exit(1)

    logging.info(f"Validation du moteur d'inférence ({backend_label(engine)})...")
    if not validate_onnx_slice_operator(engine, window_size=int(effective_cfg["window"])):
        logging.critical(
            f"Validation pré-vol échouée avec le backend {backend_label(engine)}. "
            "Vérifiez le modèle ONNX et le moteur d'inférence."
        )
        sys.exit(1)

    target_dir = Path(args.input_dir).resolve() if args.input_dir else WORK_DIR
    if args.force:
        videos = [p for ext in VIDEO_EXTENSIONS for p in target_dir.rglob(f'*{ext}')]
    else:
        videos = [p for ext in VIDEO_EXTENSIONS for p in target_dir.rglob(f'*{ext}') if not p.with_suffix('.csv').exists()]
    videos, preserved_logos = split_preserved_media(videos)
    if preserved_logos:
        logging.info(
            f"{len(preserved_logos)} média(s) .mov préservé(s) ignoré(s) par la détection de scènes."
        )
    total_videos = len(videos)
    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")
    print(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}", flush=True)

    for video_path in videos:
        check_fps_conformance(video_path)

    if total_videos == 0:
        return

    successful_count = 0
    t_start = time.perf_counter()

    for i, video_path in enumerate(videos):
        ok, engine = process_single_video(i, total_videos, video_path, engine, model_path, effective_cfg)
        successful_count += 1 if ok else 0

    total_elapsed = time.perf_counter() - t_start
    logging.info(
        f"--- Analyse terminée. {successful_count}/{total_videos} réussie(s). "
        f"Temps total: {total_elapsed:.1f}s ---"
    )

    if successful_count < total_videos:
        sys.exit(1)


if __name__ == "__main__":
    main()
