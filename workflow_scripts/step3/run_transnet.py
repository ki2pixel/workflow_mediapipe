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

# --- Configuration ---
WORK_DIR = Path(os.getcwd())
VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent

# --- Configuration du Logger ---
LOG_DIR = BASE_DIR / "logs" / "step3"
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
                     "Assurez-vous qu'il est dans le dossier 'workflow_scripts/step3/'.")
    sys.exit(1)


def get_video_fps(video_path):
    """Retourne toujours 25.0 FPS pour stabiliser les timecodes (Étape 2 force 25 FPS)."""
    return 25.0


def detect_scenes_with_pytorch(video_path, model, device, threshold=0.5):
    """Détection de scènes avec lecture streaming (chunked) et batching glissant.

    - Décodage FFmpeg en streaming (48x27, fps=25) avec run_async.
    - Fenêtre de taille WINDOW_SIZE, pas WINDOW_STRIDE, padding PADDING_FRAMES
      en répétant les frames de bord pour les fenêtres au début/à la fin.
    - Retourne des segments [start_frame, end_frame] basés sur un seuil.
    """
    try:
        process = (
            ffmpeg
            .input(str(video_path))
            .output(
                'pipe:',
                format='rawvideo',
                pix_fmt='rgb24',
                s='48x27',
                r=25  # forcer 25 FPS
            )
            .global_args('-threads', str(FFMPEG_THREADS) if FFMPEG_THREADS is not None else '0')
            .run_async(pipe_stdout=True, pipe_stderr=True, quiet=True)
        )

        FRAME_H, FRAME_W, FRAME_C = 27, 48, 3
        FRAME_SIZE = FRAME_H * FRAME_W * FRAME_C

        def read_n_frames(n):
            """Lit n frames depuis stdout et retourne une liste de np.ndarray shape (27,48,3)."""
            buf = bytearray()
            target = n * FRAME_SIZE
            while len(buf) < target:
                chunk = process.stdout.read(target - len(buf))
                if not chunk:
                    break
                buf.extend(chunk)
            if not buf:
                return []
            total_bytes = len(buf)
            frames_count = total_bytes // FRAME_SIZE
            if frames_count == 0:
                return []
            arr = np.frombuffer(bytes(buf[:frames_count * FRAME_SIZE]), np.uint8)
            return list(arr.reshape([frames_count, FRAME_H, FRAME_W, FRAME_C]))

        frames = []  # tampon de frames décodées
        predictions = []
        total_batches = 0
        batch_count = 0

        with torch.inference_mode():
            # Remplir suffisamment pour la première fenêtre (WINDOW_SIZE-PADDING_FRAMES) + PADDING_FRAMES à droite
            # On lit au moins WINDOW_SIZE frames réelles pour démarrer
            if len(frames) < WINDOW_SIZE:
                frames.extend(read_n_frames(WINDOW_SIZE - len(frames)))

            # Si aucune frame
            if len(frames) == 0:
                logging.warning(f"Aucune frame extraite pour {video_path.name}.")
                return []

            # Calculer une estimation du nombre de batches (approx, peut ajuster à la fin)
            # Impossible de connaître la longueur totale à l'avance en streaming.
            # On loguera la progression basée sur le compteur de batches.

            start_idx = 0

            def build_window(idx, available_right):
                """Construit une fenêtre de longueur WINDOW_SIZE autour de idx avec padding bords.

                idx est l'index de départ des frames réelles (sans le padding gauche).
                available_right indique combien de frames réelles existent à droite à partir de idx.
                """
                left_needed = PADDING_FRAMES
                right_needed = PADDING_FRAMES

                # gauche
                if idx >= left_needed:
                    left_part = frames[idx - left_needed: idx]
                else:
                    pad = [frames[0]] * (left_needed - idx)
                    left_part = pad + frames[0:idx]

                # milieu
                mid_len = WINDOW_SIZE - PADDING_FRAMES - PADDING_FRAMES
                mid_part = frames[idx: idx + mid_len]

                # droite
                right_have = max(0, available_right - mid_len)
                if right_have >= right_needed:
                    right_part = frames[idx + mid_len: idx + mid_len + right_needed]
                else:
                    # compléter avec la dernière frame disponible
                    base = frames[idx + mid_len - 1] if (idx + mid_len - 1) < len(frames) else frames[-1]
                    right_part = frames[idx + mid_len: idx + mid_len + right_have] + [base] * (right_needed - right_have)

                window = left_part + mid_part + right_part
                return np.asarray(window, dtype=np.uint8)

            while True:
                # S'assurer qu'on a assez de frames pour avancer d'un STRIDE
                to_read = max(0, (start_idx + WINDOW_SIZE) - len(frames))
                if to_read > 0:
                    new_frames = read_n_frames(to_read)
                    if new_frames:
                        frames.extend(new_frames)
                    else:
                        # fin du flux, on traitera ce qui reste avec padding à droite
                        pass

                if start_idx >= len(frames):
                    break

                # combien de frames réelles dispo à droite de idx
                available_right = max(0, len(frames) - start_idx)
                # Construire la fenêtre avec padding si nécessaire
                window_np = build_window(start_idx, available_right)
                if window_np.shape[0] != WINDOW_SIZE:
                    # cas limite si frames < 1
                    if len(frames) == 0:
                        break
                    # compléter strictement à WINDOW_SIZE
                    lastf = frames[-1]
                    add = WINDOW_SIZE - window_np.shape[0]
                    window_np = np.concatenate([window_np, np.repeat(np.expand_dims(lastf, 0), add, axis=0)], axis=0)

                batch_torch = torch.from_numpy(window_np).unsqueeze(0).to(device, dtype=torch.uint8)

                if USE_AMP and device.type == 'cuda':
                    try:
                        with torch.amp.autocast('cuda', dtype=AMP_DTYPE):
                            out = model(batch_torch)
                    except AttributeError:
                        with torch.cuda.amp.autocast(dtype=AMP_DTYPE):
                            out = model(batch_torch)
                else:
                    out = model(batch_torch)

                # Normaliser la sortie: prendre le tenseur principal si tuple/list
                single_frame_pred_logits = out[0] if isinstance(out, (tuple, list)) else out

                pred_slice = torch.sigmoid(single_frame_pred_logits).cpu().numpy()[0, PADDING_FRAMES:WINDOW_SIZE - PADDING_FRAMES, 0]
                predictions.append(pred_slice)
                batch_count += 1

                # progression (approx)
                if batch_count % 10 == 0:
                    logging.info(f"INTERNAL_PROGRESS: {batch_count} batches - {video_path.name}")
                    print(f"INTERNAL_PROGRESS: {batch_count} batches - {video_path.name}")

                # avancer
                start_idx += WINDOW_STRIDE

                # condition d'arrêt: si on est à la fin et qu'aucune nouvelle frame lue
                if start_idx >= len(frames):
                    # tenter de lire plus pour une dernière fenêtre sinon sortir
                    more = read_n_frames(WINDOW_STRIDE)
                    if more:
                        frames.extend(more)
                    else:
                        break

        # concat predictions and trim to actual frame count
        if not predictions:
            return [[0, len(frames) - 1]] if len(frames) > 0 else []

        final_predictions = np.concatenate(predictions)[:len(frames)]
        shot_boundaries = np.where(final_predictions > threshold)[0]

        if len(shot_boundaries) == 0:
            return [[0, len(frames) - 1]] if len(frames) > 0 else []

        # Création des scènes
        detected_scenes = []
        last_cut = -1
        for cut in shot_boundaries:
            if cut > last_cut:
                detected_scenes.append([last_cut + 1, cut])
            last_cut = cut
        if last_cut < len(frames) - 1:
            detected_scenes.append([last_cut + 1, len(frames) - 1])

        return detected_scenes

    except Exception as e:
        logging.error(f"Erreur lors de la détection de scènes pour {video_path.name}: {e}", exc_info=True)
        return None


def main():
    # L'argument `weights_dir` de app_new.py n'est pas utilisé, on utilise un chemin fixe
    # pour le fichier .pth pour simplifier.
    parser = argparse.ArgumentParser(description="Analyse des transitions vidéo avec TransNetV2 (PyTorch).")
    parser.add_argument("--weights_dir", help="Argument ignoré, présent pour compatibilité.")
    parser.add_argument("--config", type=str, help="Chemin du fichier de configuration JSON (par défaut: config/step3_transnet.json si présent)")
    # Mettre None comme défaut pour permettre au JSON de définir la valeur quand le flag n'est pas fourni
    parser.add_argument("--threshold", type=float, default=None, help="Seuil de détection (0-1). Défaut: 0.5")
    parser.add_argument("--window", type=int, default=None, help="Taille de fenêtre (frames). Défaut: 100")
    parser.add_argument("--stride", type=int, default=None, help="Pas entre fenêtres (frames). Défaut: 50")
    parser.add_argument("--padding", type=int, default=None, help="Padding au début/fin (frames). Défaut: 25")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default=None, help="Sélection du device. Défaut: auto")
    parser.add_argument("--ffmpeg_threads", type=int, default=None, help="Nombre de threads FFmpeg (0 = auto)")
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
        candidate = BASE_DIR / "config" / "step3_transnet.json"
        if candidate.exists():
            config_path = candidate

    file_cfg = {}
    if config_path is not None:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            logging.info(f"Configuration chargée depuis: {config_path}")
        except Exception as e:
            logging.error(f"Impossible de charger le fichier de configuration {config_path}: {e}")

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
    global WINDOW_SIZE, WINDOW_STRIDE, PADDING_FRAMES, FFMPEG_THREADS, USE_AMP, AMP_DTYPE
    WINDOW_SIZE = int(effective_cfg["window"])
    WINDOW_STRIDE = int(effective_cfg["stride"])
    PADDING_FRAMES = int(effective_cfg["padding"])
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
        f"num_workers={effective_cfg['num_workers']}, torchscript={effective_cfg['torchscript']}, warmup={effective_cfg['warmup']}, warmup_batches={effective_cfg['warmup_batches']}, "
        f"torchscript_auto_fallback={effective_cfg['torchscript_auto_fallback']}"
    )

    # Chemin vers le modèle PyTorch
    pytorch_weights_path = BASE_DIR / "assets" / "transnetv2-pytorch-weights.pth"

    logging.info("--- Démarrage de l'analyse des transitions (PyTorch) ---")

    # Préparer la liste des vidéos

    # Trouver les vidéos à traiter
    videos = [p for ext in VIDEO_EXTENSIONS for p in WORK_DIR.rglob(f'*{ext}') if not p.with_suffix('.csv').exists()]
    total_videos = len(videos)
    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")
    print(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")

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
            logging.error(f"Erreur CUDA lors du chargement du modèle: {e}")
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
            logging.error(f"Erreur lors du chargement du modèle: {e}", exc_info=True)
            return None
    except Exception as e:
        logging.error(f"Erreur inattendue lors du chargement du modèle: {e}", exc_info=True)
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
        global WINDOW_SIZE, WINDOW_STRIDE, PADDING_FRAMES, FFMPEG_THREADS, USE_AMP, AMP_DTYPE
        WINDOW_SIZE = int(cfg["window"])
        WINDOW_STRIDE = int(cfg["stride"])
        PADDING_FRAMES = int(cfg["padding"])
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
        logging.error(f"Erreur worker pour {video_path_str}: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    main()