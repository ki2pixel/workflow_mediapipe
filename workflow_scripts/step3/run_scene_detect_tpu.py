#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'analyse des transitions vidéo avec MobileNetV2 INT8 (Google Coral Edge TPU)
Version Ubuntu - Étape 3 (Alternative à TransNetV2)

Algorithmes implémentés (Audit TPU vs GPU "Camille") :
- Embeddings GAP 1280D (avec fallback logits 1000D)
- Moyenne Mobile Exponentielle (EMA) sur les embeddings
- Filtre Médian 1D sur les distances cosinus
- Seuillage Adaptatif de Dugad (μ + k·σ sur fenêtre glissante)
- Double Seuil (Twin-Comparison) pour transitions graduelles
- Timecode aligné sur la baseline GPU (HH:MM:SS.mmm)
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
import threading
import queue
import numba as nb
from pathlib import Path
from datetime import datetime
import multiprocessing as mp

# Gestion des dépendances TPU
try:
    import tflite_runtime.interpreter as tflite
except ImportError as e:
    logging.critical(f"ERREUR: Les bibliothèques TFLite ne sont pas installées dans coral_env: {e}")
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

# --- Defaults algorithmiques (Audit Camille) ---
DEFAULT_EMA_ALPHA = 0.8
DEFAULT_DUGAD_WINDOW = 25
DEFAULT_DUGAD_K = 3.0
DEFAULT_MEDIAN_FILTER_SIZE = 5
DEFAULT_TWIN_ENABLED = True
DEFAULT_TWIN_K_HIGH = 3.5
DEFAULT_TWIN_K_LOW = 2.0
DEFAULT_MIN_SCENE_LEN = 12  # 0.5s à 25fps


def format_timecode(frame_num: int, fps: float) -> str:
    """Format frame number to HH:MM:SS.mmm (aligné sur baseline GPU FrameTimecode)"""
    total_seconds = frame_num / fps
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int(round((total_seconds - int(total_seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"


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


def apply_ema_smoothing(embeddings, alpha=DEFAULT_EMA_ALPHA):
    """Applique une Moyenne Mobile Exponentielle (EMA) sur les embeddings.

    E_i = α · F_i + (1 - α) · E_{i-1}

    Lisse le jitter de caméra tout en préservant les transitions nettes.

    Args:
        embeddings: Liste de vecteurs numpy (float32).
        alpha: Coefficient de lissage (0 < α ≤ 1). Plus α est grand, plus le lissage
               privilégie la frame courante (réactif).

    Returns:
        Liste de vecteurs numpy lissés par EMA.
    """
    if not embeddings or alpha >= 1.0:
        return embeddings

    smoothed = [embeddings[0].copy()]
    for i in range(1, len(embeddings)):
        ema = alpha * embeddings[i] + (1.0 - alpha) * smoothed[i - 1]
        smoothed.append(ema)
    return smoothed


@nb.njit(nopython=True, fastmath=True)
def _temporal_smoothing_numba(distances, window_size):
    n = len(distances)
    if n < window_size:
        return distances.copy()

    if window_size % 2 == 0:
        window_size += 1

    half_w = window_size // 2
    filtered = np.zeros(n, dtype=np.float32)

    for i in range(n):
        if i < half_w or i >= n - half_w:
            filtered[i] = distances[i]
        else:
            filtered[i] = np.median(distances[i - half_w:i + half_w + 1])
    return filtered

def temporal_smoothing(distances, window_size=DEFAULT_MEDIAN_FILTER_SIZE):
    """Filtre Médian 1D sur les distances cosinus accéléré par Numba JIT."""
    return _temporal_smoothing_numba(np.asarray(distances, dtype=np.float32), window_size)


@nb.njit(nopython=True, fastmath=True)
def _compute_adaptive_threshold_numba(distances, window_size, k):
    n = len(distances)
    thresholds = np.zeros(n, dtype=np.float32)
    half_w = window_size // 2

    for i in range(n):
        start = max(0, i - half_w)
        end = min(n, i + half_w + 1)
        window = distances[start:end]
        mu = np.mean(window)
        sigma = np.std(window)
        thresholds[i] = mu + k * sigma
    return thresholds

def compute_adaptive_threshold(distances, window_size=DEFAULT_DUGAD_WINDOW, k=DEFAULT_DUGAD_K):
    """Calcule le seuil adaptatif de Dugad accéléré par Numba JIT."""
    return _compute_adaptive_threshold_numba(np.asarray(distances, dtype=np.float32), window_size, float(k))


@nb.njit(nopython=True, fastmath=True)
def _detect_cuts_dugad_numba(distances, thresholds, refractory_period, min_scene_len):
    n = len(distances)
    cut_indices = np.zeros(n, dtype=np.int32)
    cut_count = 0
    last_cut = -refractory_period

    for i in range(1, n - 1):
        is_local_max = (distances[i] > distances[i - 1] and distances[i] > distances[i + 1])
        above_threshold = distances[i] > thresholds[i]
        after_refractory = (i - last_cut) >= refractory_period
        meets_min_len = (i - last_cut) >= min_scene_len if cut_count > 0 else True

        if is_local_max and above_threshold and after_refractory and meets_min_len:
            cut_indices[cut_count] = i
            cut_count += 1
            last_cut = i

    return cut_indices[:cut_count]

def detect_cuts_dugad(distances, thresholds, refractory_period, min_scene_len=DEFAULT_MIN_SCENE_LEN):
    """Détecte les coupures nettes via le modèle de Dugad accéléré par Numba JIT."""
    return list(_detect_cuts_dugad_numba(np.asarray(distances, dtype=np.float32), 
                                         np.asarray(thresholds, dtype=np.float32), 
                                         refractory_period, min_scene_len))


@nb.njit(nopython=True, fastmath=True)
def _detect_gradual_transitions_numba(distances, thresholds_high, thresholds_low, refractory_period, existing_cuts):
    n_frames = len(distances)
    detected_scenes = np.zeros(n_frames, dtype=np.int32)
    scene_idx = 0
    
    in_gradual = False
    acc_distance = 0.0
    start_gradual_idx = 0
    frames_above = 0
    gradual_peak_idx = 0
    gradual_peak_val = 0.0
    
    for i in range(1, n_frames - 1):
        if not in_gradual:
            if distances[i] > thresholds_low[i] and distances[i] <= thresholds_high[i]:
                in_gradual = True
                acc_distance = distances[i]
                start_gradual_idx = i
                gradual_peak_idx = i
                gradual_peak_val = distances[i]
                frames_above = 1
        else:
            if distances[i] > thresholds_low[i]:
                acc_distance += distances[i]
                frames_above += 1
                if distances[i] > gradual_peak_val:
                    gradual_peak_val = distances[i]
                    gradual_peak_idx = i
            else:
                if frames_above >= 3:
                    sum_t_h = 0.0
                    for j in range(start_gradual_idx, i):
                        sum_t_h += thresholds_high[j]
                    avg_threshold_h = sum_t_h / max(1, (i - start_gradual_idx))
                    
                    if acc_distance > avg_threshold_h * 1.5:
                        mid_point = (start_gradual_idx + i) // 2
                        
                        too_close = False
                        for c in existing_cuts:
                            if abs(mid_point - c) < refractory_period:
                                too_close = True
                                break
                        if not too_close:
                            for j in range(scene_idx):
                                if abs(mid_point - detected_scenes[j]) < refractory_period:
                                    too_close = True
                                    break
                                
                        if not too_close:
                            detected_scenes[scene_idx] = mid_point
                            scene_idx += 1
                
                in_gradual = False
                acc_distance = 0.0
                frames_above = 0

    return detected_scenes[:scene_idx]

def detect_gradual_transitions(distances, thresholds_high, thresholds_low, refractory_period,
                               existing_cuts=None):
    """Détecte les transitions graduelles accéléré par Numba JIT."""
    existing_cuts_arr = np.array(existing_cuts if existing_cuts is not None else [], dtype=np.int32)
    gradual_arr = _detect_gradual_transitions_numba(
        np.asarray(distances, dtype=np.float32), 
        np.asarray(thresholds_high, dtype=np.float32), 
        np.asarray(thresholds_low, dtype=np.float32), 
        refractory_period, 
        existing_cuts_arr
    )
    return list(gradual_arr)


def get_video_frame_count(video_path):
    """Estime le nombre total de frames via ffprobe pour la barre de progression."""
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=nb_frames',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)
        ]
        output = subprocess.check_output(cmd, text=True).strip()
        if output.isdigit():
            return int(output)
    except Exception:
        pass
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)
        ]
        output = subprocess.check_output(cmd, text=True).strip()
        if output:
            return int(float(output) * 25.0)
    except Exception:
        pass
    return 1000


def detect_scenes_tpu(video_path, interpreter, threshold=0.25, min_scene_len=DEFAULT_MIN_SCENE_LEN,
                      fps=25.0, ema_alpha=DEFAULT_EMA_ALPHA,
                      dugad_window=DEFAULT_DUGAD_WINDOW, dugad_k=DEFAULT_DUGAD_K,
                      median_filter_size=DEFAULT_MEDIAN_FILTER_SIZE,
                      twin_enabled=DEFAULT_TWIN_ENABLED,
                      twin_k_high=DEFAULT_TWIN_K_HIGH, twin_k_low=DEFAULT_TWIN_K_LOW):
    """
    Détecte les scènes en utilisant MobileNetV2 sur l'Edge TPU.

    Pipeline algorithmique (Audit Camille) :
    1. Extraction frame-par-frame des embeddings via Edge TPU
    2. Lissage EMA des embeddings (α configurable)
    3. Calcul des distances cosinus consécutives
    4. Filtre Médian 1D sur les distances
    5. Seuillage adaptatif de Dugad (μ + k·σ)
    6. Détection Twin-Comparison pour transitions graduelles
    7. Génération des paires [start_frame, end_frame]

    Args:
        video_path: Chemin de la vidéo.
        interpreter: Interpréteur TFLite Edge TPU.
        threshold: Seuil statique de fallback (non utilisé avec Dugad, conservé pour compat).
        min_scene_len: Durée minimale d'une scène (frames).
        fps: Framerate de la vidéo.
        ema_alpha: Coefficient EMA pour le lissage des embeddings.
        dugad_window: Taille de la fenêtre glissante Dugad (M).
        dugad_k: Coefficient de sensibilité du seuil Dugad.
        median_filter_size: Taille du filtre médian 1D.
        twin_enabled: Active la détection des transitions graduelles.
        twin_k_high: Coefficient k pour le seuil haut du twin-comparison.
        twin_k_low: Coefficient k pour le seuil bas du twin-comparison.

    Returns:
        Liste de paires [start_frame, end_frame], ou None en cas d'erreur.
    """
    try:
        # Configuration des entrées TFLite
        input_details = interpreter.get_input_details()[0]
        output_details = interpreter.get_output_details()[0]

        total_expected_frames = max(1, get_video_frame_count(video_path))

        # Le MobileNetV2 EdgeTPU prend du 224x224 RGB
        _, height, width, _ = input_details['shape']

        # Lancement de ffmpeg pour extraire les frames 224x224 RGB à 25 FPS
        command = [
            'ffmpeg',
            '-threads', '6',
            '-i', str(video_path),
            '-f', 'image2pipe',
            '-pix_fmt', 'rgb24',
            '-s', f'{width}x{height}',
            '-r', str(fps),
            '-vcodec', 'rawvideo',
            '-sws_flags', 'fast_bilinear',
            '-sws_dither', 'none',
            '-loglevel', 'error',
            '-'
        ]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10**8)

        frame_size = width * height * 3
        raw_embeddings = []
        frame_queue = queue.Queue(maxsize=128)

        def producer():
            while True:
                raw_image = process.stdout.read(frame_size)
                if len(raw_image) != frame_size:
                    frame_queue.put(None)
                    break
                # Allocation mémoire en parallèle du TPU
                image = np.frombuffer(raw_image, dtype=np.uint8).reshape((height, width, 3))
                frame_queue.put(image)

        producer_thread = threading.Thread(target=producer, daemon=True)
        producer_thread.start()

        frame_idx = 0
        logging.info(f"Démarrage de l'inférence TPU pour {video_path.name} (Producer-Consumer activé)")

        while True:
            image = frame_queue.get()
            if image is None:
                break

            # Inférence Edge TPU (Libère le GIL)
            interpreter.set_tensor(input_details['index'], np.expand_dims(image, axis=0))
            interpreter.invoke()

            # Récupérer l'embedding (1280D GAP ou 1000D logits selon le modèle)
            output = interpreter.get_tensor(output_details['index']).copy()

            # Cast en float32 et aplatissement pour le calcul de distance CPU
            raw_embeddings.append(output.flatten().astype(np.float32))

            frame_idx += 1
            if frame_idx % 250 == 0:
                progress_pct = int(min(100, (frame_idx / total_expected_frames) * 100))
                logging.info(
                    f"INTERNAL_PROGRESS: {frame_idx}/{total_expected_frames} frames "
                    f"({progress_pct}%) - {video_path.name}"
                )

        producer_thread.join()
        process.stdout.close()
        process.wait()

        if not raw_embeddings:
            logging.warning(f"Aucune frame lue pour {video_path.name}")
            return []

        total_frames = len(raw_embeddings)
        embedding_dim = raw_embeddings[0].shape[0]
        logging.info(
            f"Extraction terminée pour {video_path.name}. "
            f"Total frames: {total_frames}, Embedding dim: {embedding_dim}D. "
            f"Application EMA (α={ema_alpha})..."
        )

        # --- Étape 2 : EMA sur les embeddings ---
        embeddings = apply_ema_smoothing(raw_embeddings, alpha=ema_alpha)

        # --- Étape 3 : Calcul des distances cosinus consécutives ---
        distances = np.zeros(total_frames)
        for i in range(1, total_frames):
            distances[i] = compute_cosine_distance(embeddings[i - 1], embeddings[i])

        # --- Étape 4 : Filtre Médian 1D ---
        smoothed_distances = temporal_smoothing(distances, window_size=median_filter_size)

        # Stats pour debug
        logging.info(
            f"Distances Stats - Max: {smoothed_distances.max():.4f}, "
            f"Mean: {smoothed_distances.mean():.4f}, "
            f"99th: {np.percentile(smoothed_distances, 99):.4f}, "
            f"95th: {np.percentile(smoothed_distances, 95):.4f}"
        )

        # --- Étape 5 : Seuillage adaptatif de Dugad ---
        refractory_period = dugad_window // 2
        thresholds = compute_adaptive_threshold(smoothed_distances, window_size=dugad_window, k=dugad_k)
        cut_indices = detect_cuts_dugad(
            smoothed_distances, thresholds,
            refractory_period=refractory_period,
            min_scene_len=min_scene_len
        )

        logging.info(f"Coupures nettes détectées (Dugad k={dugad_k}): {len(cut_indices)}")

        # --- Étape 6 : Twin-Comparison pour transitions graduelles ---
        gradual_indices = []
        if twin_enabled:
            thresholds_high = compute_adaptive_threshold(
                smoothed_distances, window_size=dugad_window, k=twin_k_high
            )
            thresholds_low = compute_adaptive_threshold(
                smoothed_distances, window_size=dugad_window, k=twin_k_low
            )
            gradual_indices = detect_gradual_transitions(
                smoothed_distances, thresholds_high, thresholds_low,
                refractory_period=refractory_period,
                existing_cuts=cut_indices
            )
            logging.info(f"Transitions graduelles détectées (Twin k_h={twin_k_high}, k_l={twin_k_low}): "
                         f"{len(gradual_indices)}")

        # --- Étape 7 : Fusion et génération des scènes ---
        all_cuts = sorted(set(cut_indices + gradual_indices))

        scenes = []
        current_start = 0
        for cut in all_cuts:
            if cut > current_start:
                scenes.append([current_start, cut])
                current_start = cut + 1

        if current_start < total_frames:
            scenes.append([current_start, total_frames - 1])

        logging.info(f"Total scènes détectées: {len(scenes)}")
        return scenes

    except Exception as e:
        logging.exception(f"Erreur TPU sur {video_path.name}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Analyse des transitions vidéo Edge TPU (MobileNetV2 Siamois).")
    parser.add_argument("--config", type=str, help="Fichier de configuration JSON")
    args = parser.parse_args()

    # Paramètres par défaut (Audit Camille)
    threshold = 0.25  # Fallback statique (non utilisé avec Dugad)
    min_scene_len = DEFAULT_MIN_SCENE_LEN
    ema_alpha = DEFAULT_EMA_ALPHA
    dugad_window = DEFAULT_DUGAD_WINDOW
    dugad_k = DEFAULT_DUGAD_K
    median_filter_size = DEFAULT_MEDIAN_FILTER_SIZE
    twin_enabled = DEFAULT_TWIN_ENABLED
    twin_k_high = DEFAULT_TWIN_K_HIGH
    twin_k_low = DEFAULT_TWIN_K_LOW

    if args.config and Path(args.config).exists():
        with open(args.config, 'r') as f:
            cfg = json.load(f)
            threshold = cfg.get("threshold", threshold)
            min_scene_len = cfg.get("min_scene_len", min_scene_len)
            ema_alpha = cfg.get("ema_alpha", ema_alpha)
            dugad_window = cfg.get("dugad_window_size", dugad_window)
            dugad_k = cfg.get("dugad_k", dugad_k)
            median_filter_size = cfg.get("median_filter_size", median_filter_size)
            twin_enabled = cfg.get("twin_threshold_enabled", twin_enabled)
            twin_k_high = cfg.get("twin_k_high", twin_k_high)
            twin_k_low = cfg.get("twin_k_low", twin_k_low)

    logging.info("--- Démarrage de l'analyse TPU (MobileNetV2 INT8 Siamois - Audit Camille) ---")
    logging.info(
        f"CONFIG: ema_alpha={ema_alpha}, dugad_window={dugad_window}, dugad_k={dugad_k}, "
        f"median_filter={median_filter_size}, twin_enabled={twin_enabled}, "
        f"twin_k_high={twin_k_high}, twin_k_low={twin_k_low}"
    )

    # Initialisation TPU — Chercher d'abord le modèle GAP 1280D, fallback sur logits 1000D
    gap_model_path = BASE_DIR / "assets" / "mobilenet_v2_gap_1280_quant_edgetpu.tflite"
    standard_model_path = BASE_DIR / "assets" / "mobilenet_v2_1.0_224_quant_edgetpu.tflite"

    if gap_model_path.exists():
        model_path = gap_model_path
        logging.info(f"Modèle GAP 1280D trouvé: {gap_model_path.name}")
    else:
        model_path = standard_model_path
        download_model_if_needed(model_path)
        logging.info(
            f"Modèle GAP 1280D non trouvé ({gap_model_path.name}), "
            f"utilisation du modèle standard logits 1000D: {model_path.name}"
        )

    try:
        # Load the Edge TPU delegate
        delegate = tflite.load_delegate('libedgetpu.so.1')
        interpreter = tflite.Interpreter(model_path=str(model_path), experimental_delegates=[delegate])
        interpreter.allocate_tensors()
        logging.info("Modèle Edge TPU chargé avec succès.")
    except Exception as e:
        logging.critical(f"Impossible d'initialiser l'Edge TPU. Vérifiez la connexion USB/PCIe et les permissions: {e}")
        sys.exit(1)

    videos = [p for ext in VIDEO_EXTENSIONS for p in WORK_DIR.rglob(f'*{ext}') if not p.with_suffix('.csv').exists()]
    total_videos = len(videos)
    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")

    if total_videos == 0:
        return

    successful_count = 0
    for idx, video_path in enumerate(videos):
        logging.info(f"PROCESSING_VIDEO: {video_path.name}")

        scenes = detect_scenes_tpu(
            video_path, interpreter,
            threshold=threshold,
            min_scene_len=min_scene_len,
            fps=25.0,
            ema_alpha=ema_alpha,
            dugad_window=dugad_window,
            dugad_k=dugad_k,
            median_filter_size=median_filter_size,
            twin_enabled=twin_enabled,
            twin_k_high=twin_k_high,
            twin_k_low=twin_k_low
        )

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
            successful_count += 1
        else:
            logging.error(f"Échec de l'analyse pour {video_path.name}")

    logging.info(f"--- Analyse terminée. {successful_count}/{total_videos} réussie(s). ---")
    if successful_count < total_videos:
        sys.exit(1)


if __name__ == "__main__":
    main()
