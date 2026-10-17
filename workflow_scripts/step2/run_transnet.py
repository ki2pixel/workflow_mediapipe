#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'analyse des transitions vidéo avec TransNetV2 (PyTorch)
Version Ubuntu - Étape 3
"""

import os
import sys
import csv
import argparse
import logging
import json
import numpy as np
import torch
import torch.nn as nn
import ffmpeg
from pathlib import Path
from datetime import datetime
from scenedetect import FrameTimecode
import multiprocessing as mp
import time
import queue
import threading

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

STEP2_DIR = Path(__file__).resolve().parent
if str(STEP2_DIR) not in sys.path:
    sys.path.insert(0, str(STEP2_DIR))

from utils.media_filters import split_preserved_media
from utils.media_normalizer import check_fps_conformance

# --- Configuration ---
WORK_DIR = Path(os.getcwd())
VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent

# --- Configuration du Logger ---
LOG_DIR = BASE_DIR / "logs" / "step2"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"transnet_pytorch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- Logique de TransNetV2 PyTorch ---
# On s'attend à ce que transnetv2_pytorch.py soit dans le même dossier
try:
    from transnetv2_pytorch import TransNetV2 as TransNetV2_PyTorch_Model
except ImportError:
    logging.critical("ERREUR: Le module 'transnetv2_pytorch.py' n'a pas pu être importé. "
                     "Assurez-vous qu'il est dans le dossier 'workflow_scripts/step2/'.")
    sys.exit(1)


import warnings
from zero_copy_pipeline import ZeroCopyTransNetPipeline, predictions_to_scenes, write_scenes_to_csv

WINDOW_SIZE = 100
WINDOW_STRIDE = 50
PADDING_FRAMES = 25
BATCH_SIZE = 25
FFMPEG_THREADS = 0
USE_AMP = False
AMP_DTYPE = torch.float16

def get_video_fps(video_path):
    """Retourne toujours 25.0 FPS pour stabiliser les timecodes (Étape 2 force 25 FPS)."""
    return 25.0


def detect_scenes_with_pytorch(video_path, model, device, threshold=0.5, batch_size=None):
    """Détection de scènes avec ingestion asynchrone zéro-copie en double tampon Ping-Pong (2600 trames)
    et fenêtrage vectorisé O(1) via sliding_window_view, avec inférence PyTorch batchée.
    """
    if batch_size is None:
        batch_size = BATCH_SIZE

    pipeline = ZeroCopyTransNetPipeline(
        ffmpeg_threads=FFMPEG_THREADS,
        windows_per_chunk=50,
    )

    video_path = Path(video_path)
    video_name = video_path.name
    all_predictions = []
    total_frames = 0
    batch_count = 0
    processed_windows = 0

    warnings.filterwarnings("ignore", message="The given NumPy array is not writable")

    try:
        with torch.inference_mode():
            for windows_5d, frames_read, total_so_far, is_eof in pipeline.iter_video_windows(video_path):
                total_frames = total_so_far
                num_win = windows_5d.shape[0]

                for start_idx in range(0, num_win, batch_size):
                    sub_batch_np = windows_5d[start_idx : start_idx + batch_size]
                    batch_torch = torch.from_numpy(sub_batch_np).to(device, dtype=torch.uint8)

                    if USE_AMP and device.type == 'cuda':
                        try:
                            with torch.amp.autocast('cuda', dtype=AMP_DTYPE):
                                out = model(batch_torch)
                        except AttributeError:
                            with torch.cuda.amp.autocast(dtype=AMP_DTYPE):
                                out = model(batch_torch)
                    else:
                        out = model(batch_torch)

                    single_frame_pred_logits = out[0] if isinstance(out, (tuple, list)) else out
                    
                    # Sigmoïde sur GPU directement sur les trames centrales utiles [25:75]
                    logits_central = single_frame_pred_logits[:, PADDING_FRAMES : WINDOW_SIZE - PADDING_FRAMES, 0]
                    chunk_preds = torch.sigmoid(logits_central).cpu().numpy().reshape(-1)
                    all_predictions.append(chunk_preds)
                    batch_count += 1

                processed_windows += num_win
                # Progression UI Flask
                processed_frames = min(processed_windows * WINDOW_STRIDE, total_frames) if total_frames > 0 else 0
                pct = int((processed_frames / total_frames * 100.0)) if total_frames > 0 else 0
                progress_msg = f"INTERNAL_PROGRESS: {processed_frames}/{total_frames} frames ({pct}%) - {video_name}"
                logging.info(progress_msg)
                print(progress_msg, flush=True)

        if total_frames == 0 or not all_predictions:
            logging.warning(f"Aucune frame extraite pour {video_path.name}.")
            return []

        final_predictions = np.concatenate(all_predictions)[:total_frames]
        return predictions_to_scenes(final_predictions, threshold=threshold)

    except Exception as e:
        logging.exception(f"Erreur lors de la détection de scènes pour {video_path.name}: {e}")
        return None


def main():
    # L'argument `weights_dir` de app_new.py n'est pas utilisé, on utilise un chemin fixe
    # pour le fichier .pth pour simplifier.
    parser = argparse.ArgumentParser(description="Analyse des transitions vidéo avec TransNetV2 (PyTorch).")
    parser.add_argument("--weights_dir", help="Argument ignoré, présent pour compatibilité.")
    parser.add_argument("--config", type=str, help="Chemin du fichier de configuration JSON (par défaut: config/step2_transnet.json si présent)")
    # Mettre None comme défaut pour permettre au JSON de définir la valeur quand le flag n'est pas fourni
    parser.add_argument("--threshold", type=float, default=None, help="Seuil de détection (0-1). Défaut: 0.5")
    parser.add_argument("--window", type=int, default=None, help="Taille de fenêtre (frames). Défaut: 100")
    parser.add_argument("--stride", type=int, default=None, help="Pas entre fenêtres (frames). Défaut: 50")
    parser.add_argument("--padding", type=int, default=None, help="Padding au début/fin (frames). Défaut: 25")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default=None, help="Sélection du device. Défaut: auto")
    parser.add_argument("--ffmpeg_threads", type=int, default=None, help="Nombre de threads FFmpeg (0 = auto)")
    parser.add_argument("--batch_size", type=int, default=None, help="Taille de lot pour l'inférence. Défaut: 16")
    parser.add_argument("--mixed_precision", action="store_true", help="Active l'AMP (CUDA seulement)")
    parser.add_argument("--num_workers", type=int, default=None, help="Nombre de workers parallèles (1 par défaut, 1 forcé en CUDA)")
    parser.add_argument("--torchscript", action="store_true", help="Active TorchScript (expérimental)")
    parser.add_argument("--warmup", action="store_true", help="Effectue un warm-up du modèle avant traitement")
    parser.add_argument("--warmup_batches", type=int, default=None, help="Nombre de passes de warm-up (défaut: 1)")
    parser.add_argument("--torchscript_auto_fallback", action="store_true", help="En cas d'échec par vidéo avec TorchScript, retenter en Eager")
    args = parser.parse_args()

    # Chargement du fichier de configuration JSON (optionnel)
    # Ordre de priorité: défauts internes < fichier JSON < CLI
    defaults = {
        "threshold": 0.5,
        "window": 100,
        "stride": 50,
        "padding": 25,
        "device": "auto",
        "ffmpeg_threads": 0,
        "mixed_precision": False,
        "amp_dtype": "float16",
        "num_workers": 1,
        "batch_size": 16,
        "torchscript": False,
        "warmup": True,
        "warmup_batches": 1,
        "torchscript_auto_fallback": True,
    }

    # Déterminer le chemin de config effectif
    config_path = None
    if args.config:
        config_path = Path(args.config)
    else:
        candidate = BASE_DIR / "config" / "step2_transnet.json"
        if candidate.exists():
            config_path = candidate

    file_cfg = {}
    if config_path is not None:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            logging.info(f"Configuration chargée depuis: {config_path}")
        except Exception as e:
            logging.exception(f"Impossible de charger le fichier de configuration {config_path}: {e}")

    # Fusion des configurations
    effective_cfg = dict(defaults)
    effective_cfg.update({k: v for k, v in file_cfg.items() if v is not None})

    # Appliquer les overrides CLI seulement si fournis (None signifie non fourni)
    if args.threshold is not None:
        effective_cfg["threshold"] = float(args.threshold)
    if args.window is not None:
        effective_cfg["window"] = int(args.window)
    if args.stride is not None:
        effective_cfg["stride"] = int(args.stride)
    if args.padding is not None:
        effective_cfg["padding"] = int(args.padding)
    if args.device is not None:
        effective_cfg["device"] = args.device
    if args.ffmpeg_threads is not None:
        effective_cfg["ffmpeg_threads"] = int(args.ffmpeg_threads)
    if args.batch_size is not None:
        effective_cfg["batch_size"] = int(args.batch_size)
    # mixed_precision: le flag CLI l'active si présent, sinon on garde config/défaut
    if args.mixed_precision:
        effective_cfg["mixed_precision"] = True
    if args.num_workers is not None:
        effective_cfg["num_workers"] = int(args.num_workers)
    if args.torchscript:
        effective_cfg["torchscript"] = True
    if args.warmup:
        effective_cfg["warmup"] = True
    if args.warmup_batches is not None:
        effective_cfg["warmup_batches"] = int(args.warmup_batches)
    if args.torchscript_auto_fallback:
        effective_cfg["torchscript_auto_fallback"] = True

    # Propager les hyperparamètres globaux (utilisés dans detect_scenes_with_pytorch)
    global WINDOW_SIZE, WINDOW_STRIDE, PADDING_FRAMES, FFMPEG_THREADS, USE_AMP, AMP_DTYPE, BATCH_SIZE
    WINDOW_SIZE = int(effective_cfg["window"])
    WINDOW_STRIDE = int(effective_cfg["stride"])
    PADDING_FRAMES = int(effective_cfg["padding"])
    BATCH_SIZE = int(effective_cfg["batch_size"])
    FFMPEG_THREADS = int(effective_cfg["ffmpeg_threads"]) if effective_cfg["ffmpeg_threads"] is not None else 0
    USE_AMP = bool(effective_cfg["mixed_precision"])
    # Convertir amp_dtype string en torch.dtype
    if effective_cfg["amp_dtype"] == "bfloat16":
        AMP_DTYPE = torch.bfloat16
    else:
        AMP_DTYPE = torch.float16

    # Log de la configuration effective
    logging.info(
        "CONFIG_EFFECTIVE: "
        f"threshold={effective_cfg['threshold']}, window={WINDOW_SIZE}, stride={WINDOW_STRIDE}, padding={PADDING_FRAMES}, "
        f"device={effective_cfg['device']}, ffmpeg_threads={FFMPEG_THREADS}, mixed_precision={USE_AMP}, amp_dtype={effective_cfg['amp_dtype']}, "
        f"num_workers={effective_cfg['num_workers']}, batch_size={BATCH_SIZE}, torchscript={effective_cfg['torchscript']}, warmup={effective_cfg['warmup']}, warmup_batches={effective_cfg['warmup_batches']}, "
        f"torchscript_auto_fallback={effective_cfg['torchscript_auto_fallback']}"
    )

    # Chemin vers le modèle PyTorch
    pytorch_weights_path = BASE_DIR / "assets" / "transnetv2-pytorch-weights.pth"

    logging.info("--- Démarrage de l'analyse des transitions (PyTorch) ---")

    # Préparer la liste des vidéos

    # Trouver les vidéos à traiter
    videos = [p for ext in VIDEO_EXTENSIONS for p in WORK_DIR.rglob(f'*{ext}') if not p.with_suffix('.csv').exists()]
    videos, preserved_logos = split_preserved_media(videos)
    if preserved_logos:
        logging.info(
            f"{len(preserved_logos)} média(s) .mov préservé(s) ignoré(s) par la détection de scènes (alpha/liste noire conservé jusqu'à la finalisation)."
        )
    total_videos = len(videos)
    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")
    print(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")

    # Garde-fou : le pipeline suppose des vidéos normalisées (MP4 / H.264 / 25 fps).
    # Un fichier non normalisé désynchronise les index de frames et les timecodes en aval.
    for video_path in videos:
        check_fps_conformance(video_path)

    if total_videos == 0:
        return

    # En CUDA, FORCER 1 worker pour éviter contention GPU (critique)
    device_mode = effective_cfg["device"]
    if device_mode == "cuda" or (device_mode == "auto" and torch.cuda.is_available()):
        if effective_cfg["num_workers"] and effective_cfg["num_workers"] > 1:
            logging.warning(f"CUDA mode détecté: limitation forcée des workers de {effective_cfg['num_workers']} à 1 pour éviter la contention GPU.")
            effective_cfg["num_workers"] = 1

    # Préparer les tâches
    tasks = [(str(p), effective_cfg, str(pytorch_weights_path)) for p in videos]

    successful_count = 0
    if effective_cfg["num_workers"] <= 1:
        for i, (vpath, cfg, wpath) in enumerate(tasks):
            ok = _process_single_video(i, total_videos, vpath, cfg, wpath)
            successful_count += 1 if ok else 0
    else:
        with mp.Pool(processes=effective_cfg["num_workers"]) as pool:
            for i, ok in enumerate(pool.imap_unordered(_pool_worker_wrapper, tasks), start=1):
                successful_count += 1 if ok else 0

    if torch.cuda.is_available():
        max_vram = torch.cuda.max_memory_allocated() / (1024 ** 2)
        logging.info(f"MAX_VRAM_MB: {max_vram:.2f}")
        print(f"MAX_VRAM_MB: {max_vram:.2f}")

    logging.info(f"--- Analyse terminée. {successful_count}/{total_videos} réussie(s). ---")
    if successful_count < total_videos:
        sys.exit(1)


def _pool_worker_wrapper(task):
    """Wrapper compatible Pool pour traiter une vidéo."""
    return _process_single_video(None, None, *task)


def _load_model_for_cfg(device, weights_path, use_torchscript=False):
    """Charge le modèle, optionnellement TorchScript, sur le device donné.
    
    Args:
        device: torch.device où charger le modèle
        weights_path: chemin vers les poids .pth
        use_torchscript: si True, compile avec TorchScript
    
    Returns:
        Le modèle chargé ou None en cas d'échec
    """
    if not Path(weights_path).exists():
        logging.critical(f"Fichier de poids PyTorch non trouvé: {weights_path}")
        logging.critical("Téléchargez les poids depuis https://github.com/soCzech/TransNetV2 et placez-les dans assets/")
        return None
    
    try:
        model = TransNetV2_PyTorch_Model()
        # Charger d'abord en CPU pour éviter les erreurs CUDA au chargement
        state = torch.load(str(weights_path), map_location='cpu')
        model.load_state_dict(state)
        model.eval()
        # Puis déplacer sur le device cible
        model.to(device)
    except RuntimeError as e:
        if "CUDA" in str(e):
            logging.exception(f"Erreur CUDA lors du chargement du modèle: {e}")
            logging.warning("Tentative de fallback sur CPU...")
            try:
                # Fallback CPU
                cpu_device = torch.device('cpu')
                model = TransNetV2_PyTorch_Model()
                state = torch.load(str(weights_path), map_location='cpu')
                model.load_state_dict(state)
                model.eval().to(cpu_device)
                logging.info("Modèle chargé avec succès sur CPU (fallback)")
                return model
            except Exception as cpu_err:
                logging.error(f"Échec du fallback CPU: {cpu_err}")
                return None
        else:
            logging.exception(f"Erreur lors du chargement du modèle: {e}")
            return None
    except Exception as e:
        logging.exception(f"Erreur inattendue lors du chargement du modèle: {e}")
        return None

    if device.type == 'cuda':
        torch.backends.cudnn.benchmark = True

    if use_torchscript:
        try:
            class InferenceWrapper(nn.Module):
                def __init__(self, base: nn.Module):
                    super().__init__()
                    self.base = base

                def forward(self, x: torch.Tensor) -> torch.Tensor:
                    out = self.base(x)
                    # Le modèle peut retourner (tensor, {"many_hot": tensor})
                    if isinstance(out, (tuple, list)):
                        return out[0]
                    return out

            wrapper = InferenceWrapper(model).to(device).eval()
            example = torch.zeros((1, WINDOW_SIZE, 27, 48, 3), dtype=torch.uint8, device=device)
            scripted = torch.jit.trace(wrapper, example)
            scripted = torch.jit.freeze(scripted)
            logging.info("TorchScript activé via wrapper pour TransNetV2 (sortie tensor-only).")
            return scripted
        except Exception as e:
            logging.warning(f"TorchScript a échoué, fallback modèle Eager: {e}")
            return model
    return model


def _process_single_video(idx, total, video_path_str, cfg, weights_path_str):
    """Traite une seule vidéo: charge le modèle, warm-up, détecte, écrit CSV.

    Args:
      idx: index (peut être None en pool)
      total: total de vidéos (peut être None en pool)
      video_path_str: chemin de la vidéo
      cfg: dict de configuration effectif
      weights_path_str: chemin vers les poids du modèle
    Returns: bool succès
    """
    try:
        video_path = Path(video_path_str)
        # Propager globals dans le worker
        global WINDOW_SIZE, WINDOW_STRIDE, PADDING_FRAMES, FFMPEG_THREADS, USE_AMP, AMP_DTYPE, BATCH_SIZE
        WINDOW_SIZE = int(cfg["window"])
        WINDOW_STRIDE = int(cfg["stride"])
        PADDING_FRAMES = int(cfg["padding"])
        BATCH_SIZE = int(cfg["batch_size"])
        FFMPEG_THREADS = int(cfg["ffmpeg_threads"]) if cfg["ffmpeg_threads"] is not None else 0
        USE_AMP = bool(cfg["mixed_precision"])
        AMP_DTYPE = torch.bfloat16 if cfg.get("amp_dtype") == "bfloat16" else torch.float16

        # Device selection avec fallback intelligent
        if cfg["device"] == "cpu":
            device = torch.device("cpu")
            logging.info(f"Device sélectionné: CPU (forcé par config)")
        elif cfg["device"] == "cuda":
            if torch.cuda.is_available():
                device = torch.device("cuda")
                logging.info(f"Device sélectionné: CUDA (GPU disponible)")
            else:
                device = torch.device("cpu")
                logging.warning("CUDA demandé mais non disponible, fallback sur CPU")
        else:  # auto
            if torch.cuda.is_available():
                device = torch.device("cuda")
                logging.info(f"Device sélectionné: CUDA (auto-détection)")
            else:
                device = torch.device("cpu")
                logging.info(f"Device sélectionné: CPU (auto-détection)")

        if idx is not None and total is not None:
            logging.info(f"PROCESSING_VIDEO: {idx + 1}/{total}: {video_path.name}")
            print(f"PROCESSING_VIDEO: {idx + 1}/{total}: {video_path.name}")
        else:
            logging.info(f"PROCESSING_VIDEO: {video_path.name}")

        # Charger modèle par worker
        use_ts = bool(cfg.get("torchscript"))
        model = _load_model_for_cfg(device, weights_path_str, use_torchscript=use_ts)
        if model is None:
            return False

        # Warm-up optionnel
        if bool(cfg.get("warmup", True)):
            warm_batches = int(cfg.get("warmup_batches", 1))
            for _ in range(max(1, warm_batches)):
                dummy = torch.zeros((1, WINDOW_SIZE, 27, 48, 3), dtype=torch.uint8, device=device)
                if USE_AMP and device.type == 'cuda':
                    try:
                        with torch.amp.autocast('cuda', dtype=AMP_DTYPE):
                            _ = model(dummy)
                    except AttributeError:
                        with torch.cuda.amp.autocast(dtype=AMP_DTYPE):
                            _ = model(dummy)
                else:
                    _ = model(dummy)

        # Détection avec fallback multi-niveaux
        scenes = detect_scenes_with_pytorch(video_path, model, device, threshold=float(cfg["threshold"]))
        
        # Niveau 1: Si TorchScript activé et échec, retenter en Eager
        if scenes is None and use_ts and bool(cfg.get("torchscript_auto_fallback", True)):
            logging.warning(f"TorchScript a échoué pour {video_path.name}, tentative de fallback Eager...")
            model = _load_model_for_cfg(device, weights_path_str, use_torchscript=False)
            if model is None:
                return False
            scenes = detect_scenes_with_pytorch(video_path, model, device, threshold=float(cfg["threshold"]))
        
        # Niveau 2: Si CUDA et échec, retenter en CPU
        if scenes is None and device.type == 'cuda':
            logging.warning(f"Erreur avec CUDA pour {video_path.name}, tentative de fallback CPU...")
            cpu_device = torch.device('cpu')
            model = _load_model_for_cfg(cpu_device, weights_path_str, use_torchscript=False)
            if model is None:
                logging.error(f"Échec du fallback CPU pour {video_path.name}")
                return False
            scenes = detect_scenes_with_pytorch(video_path, model, cpu_device, threshold=float(cfg["threshold"]))
            if scenes is None:
                logging.error(f"Échec définitif du traitement de {video_path.name} (CUDA et CPU)")
                return False
            logging.info(f"Succès avec fallback CPU pour {video_path.name}")
        
        if scenes is None:
            logging.error(f"Échec du traitement de {video_path.name}")
            return False

        # Écriture CSV
        output_csv_path = video_path.with_suffix('.csv')
        fps = get_video_fps(video_path)
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['No', 'Timecode In', 'Timecode Out', 'Frame In', 'Frame Out'])
            for j, (start, end) in enumerate(scenes):
                start_frame = int(start)
                end_frame = int(end)
                timecode_in = FrameTimecode(start_frame, fps)
                timecode_out = FrameTimecode(end_frame, fps)
                writer.writerow([
                    j + 1,
                    timecode_in.get_timecode(),
                    timecode_out.get_timecode(),
                    start_frame + 1,
                    end_frame + 1
                ])
        logging.info(f"Succès: {output_csv_path.name} créé avec {len(scenes)} scènes.")
        return True
    except Exception as e:
        logging.exception(f"Erreur worker pour {video_path_str}: {e}")
        return False


if __name__ == "__main__":
    main()