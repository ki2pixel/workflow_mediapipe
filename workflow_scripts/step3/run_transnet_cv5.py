#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'analyse des transitions vidéo avec TransNetV2 via OpenCV 5.0 DNN (ONNX)
Version Expérimentale - Étape 3 (Alternative au pipeline PyTorch)

Ce script remplace le runtime PyTorch par le moteur DNN orienté graphe d'OpenCV 5.0
pour l'inférence TransNetV2. Avantages attendus :
  - Empreinte mémoire réduite (~200 Mo vs ~2 Go pour PyTorch)
  - Démarrage instantané (pas de JIT/compilation CUDA)
  - Dispatching HAL SIMD automatique (AVX2/AVX-512/NEON via KleidiCV)

Prérequis :
  - Le modèle ONNX (transnetv2.onnx) doit être placé dans assets/models/onnx/
  - Le venv transnet_cv5_env doit être activé (opencv-python-headless>=5.0.0)

Activation : USE_OPENCV5_STEP3=true dans .env
"""

import os
import sys
import csv
import argparse
import logging
import json
import numpy as np
import cv2
import ffmpeg
from pathlib import Path
from datetime import datetime
from scenedetect import FrameTimecode
import time

# --- Configuration ---
WORK_DIR = Path(os.getcwd())
VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent

# --- Configuration du Logger ---
LOG_DIR = BASE_DIR / "logs" / "step3"
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

# --- Hyperparamètres globaux (redéfinis dans main) ---
WINDOW_SIZE = 100
WINDOW_STRIDE = 50
PADDING_FRAMES = 25
BATCH_SIZE = 16
FFMPEG_THREADS = 0

# Default ONNX model path
ONNX_MODEL_PATH = BASE_DIR / "assets" / "models" / "onnx" / "transnetv2.onnx"


def get_video_fps(video_path):
    """Retourne toujours 25.0 FPS pour stabiliser les timecodes (Étape 2 force 25 FPS)."""
    return 25.0


def validate_onnx_slice_operator(net, window_size=100):
    """Validation de l'opérateur Slice d'OpenCV 5.0 DNN pour TransNetV2.

    Le rapport de faisabilité identifie le Slice comme point de défaillance
    potentiel. Ce test envoie une entrée synthétique et vérifie que la sortie
    n'est pas un tenseur vide ou dégénéré.

    Returns:
        True si la validation passe, False sinon.
    """
    try:
        # Le modèle ONNX attend un tenseur [B, T, 27, 48, 3] de type uint8
        dummy_input = np.zeros((1, window_size, 27, 48, 3), dtype=np.uint8)
        net.setInput(dummy_input)
        output = net.forward()

        # Si le net est un wrapper ONNX Runtime, l'output est directement disponible
        # sous forme de tableau numpy
        if output is None or (hasattr(output, 'size') and output.size == 0):
            logging.error(
                "VALIDATION_ECHEC: Le modèle produit un tenseur vide."
            )
            return False

        # Vérifier que la forme de sortie est cohérente
        # TransNetV2 attend [B, T, 1] ou [B, T] en sortie
        if len(output.shape) < 2:
            logging.error(
                f"VALIDATION_ECHEC: Forme de sortie inattendue: {output.shape}. "
                f"Attendu [B, T, ...] avec B=1, T~={window_size}."
            )
            return False

        logging.info(
            f"VALIDATION_OK: Slice / Graph model validé. "
            f"Sortie shape={output.shape}, "
            f"range=[{output.min():.4f}, {output.max():.4f}]"
        )
        return True

    except Exception as e:
        logging.error(f"VALIDATION_ECHEC: Exception lors du test du graphe: {e}")
        return False


def load_opencv_dnn_model(model_path):
    """Charge le modèle TransNetV2 ONNX via OpenCV 5.0 DNN avec Fallback ONNX Runtime."""
    model_path = Path(model_path)
    if not model_path.exists():
        logging.critical(f"Modèle ONNX non trouvé: {model_path}")
        return None

    # 1. Tentative avec OpenCV DNN
    try:
        logging.info("Tentative de chargement du modèle ONNX avec OpenCV DNN...")
        net = cv2.dnn.readNetFromONNX(str(model_path))

        # Configurer le backend OpenCV CPU avec le nouveau moteur orienté graphe
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

        # Tenter d'activer le moteur DNN orienté graphe (ENGINE_NEW)
        # si disponible dans cette version d'OpenCV 5.0
        if hasattr(cv2.dnn, 'ENGINE_NEW'):
            try:
                net.setEngineType(cv2.dnn.ENGINE_NEW)
                logging.info("ENGINE_NEW (moteur DNN orienté graphe) activé.")
            except Exception as e:
                logging.warning(f"ENGINE_NEW non applicable, fallback moteur classique: {e}")
        else:
            logging.info("ENGINE_NEW non disponible dans cette version d'OpenCV. Utilisation du moteur DNN classique.")

        logging.info(f"Modèle ONNX chargé avec OpenCV DNN: {model_path.name} (OpenCV {cv2.__version__})")
        return net
    except Exception as dnn_err:
        logging.warning(f"Échec de chargement avec OpenCV DNN ({dnn_err}). Passage au fallback ONNX Runtime...")

    # 2. Fallback ONNX Runtime
    try:
        class ORTDNNNet:
            """Wrapper imitant l'API cv2.dnn.Net pour un remplacement transparent par ONNX Runtime."""
            def __init__(self, path):
                import onnxruntime as ort
                opts = ort.SessionOptions()
                
                # Détection et priorisation des execution providers (GPU vs CPU)
                available = ort.get_available_providers()
                providers = []
                if 'CUDAExecutionProvider' in available:
                    providers.append('CUDAExecutionProvider')
                    logging.info("ONNX Runtime : Accélération GPU CUDA disponible et activée.")
                if 'CPUExecutionProvider' in available:
                    providers.append('CPUExecutionProvider')
                
                if not providers:
                    providers = ['CPUExecutionProvider']
                
                # Optimisation du multi-threading :
                # - Sur GPU, on limite les threads CPU d'appoint pour éviter la contention CPU.
                # - Sur CPU uniquement, on évite de brider à 1 thread car le traitement des vidéos est séquentiel.
                #   On laisse ORT utiliser son multi-threading interne auto-détecté.
                if 'CUDAExecutionProvider' in providers:
                    opts.intra_op_num_threads = 2
                    opts.inter_op_num_threads = 2
                    
                self.session = ort.InferenceSession(str(path), sess_options=opts, providers=providers)
                
                # Journalisation du provider actif pour confirmation
                active_providers = self.session.get_providers()
                logging.info(f"Session ONNX Runtime initialisée avec les providers actifs : {active_providers}")
                
                self.input_name = self.session.get_inputs()[0].name
                self.output_names = [o.name for o in self.session.get_outputs()]
                self.inputs = {}

            def setInput(self, blob, name=""):
                self.inputs[name or self.input_name] = blob

            def forward(self, outputName=""):
                if outputName:
                    outputs = self.session.run([outputName], self.inputs)
                    return outputs[0]
                else:
                    outputs = self.session.run(self.output_names, self.inputs)
                    return outputs[0] if len(outputs) == 1 else outputs

        net = ORTDNNNet(model_path)
        logging.info(f"Modèle ONNX chargé via ONNX Runtime (fallback) : {model_path.name}")
        return net
    except Exception as ort_err:
        logging.critical(f"Erreur fatale : Impossible de charger le modèle via OpenCV DNN ou ONNX Runtime. Erreur ORT: {ort_err}")
        return None


def detect_scenes_cv5(video_path, net, threshold=0.5):
    """Détection de scènes avec OpenCV 5.0 DNN et streaming FFmpeg.

    Pipeline :
      1. FFmpeg -> frames brutes 48x27 RGB à 25 FPS (streaming asynchrone)
      2. Fenêtres glissantes (WINDOW_SIZE) avec padding aux bords
      3. Inférence via cv2.dnn (batch) pour obtenir les probabilités de transition
      4. Seuillage et extraction des frontières de scènes

    Gestion mémoire :
      - Pruning glissant du tampon de frames (empreinte O(WINDOW_SIZE))
      - Pas de copie inutile grâce au slicing numpy
    """
    import queue
    import threading

    try:
        process = (
            ffmpeg
            .input(str(video_path))
            .output(
                'pipe:',
                format='rawvideo',
                pix_fmt='rgb24',
                s='48x27',
                r=25
            )
            .global_args('-threads', str(FFMPEG_THREADS) if FFMPEG_THREADS else '0')
            .run_async(pipe_stdout=True, pipe_stderr=True, quiet=True)
        )

        FRAME_H, FRAME_W, FRAME_C = 27, 48, 3
        FRAME_SIZE = FRAME_H * FRAME_W * FRAME_C

        frame_queue = queue.Queue(maxsize=1000)
        read_error = []

        def ffmpeg_reader():
            try:
                while True:
                    buf = bytearray()
                    target = 50 * FRAME_SIZE
                    while len(buf) < target:
                        chunk = process.stdout.read(target - len(buf))
                        if not chunk:
                            break
                        buf.extend(chunk)

                    if not buf:
                        frame_queue.put(None)
                        break

                    total_bytes = len(buf)
                    frames_count = total_bytes // FRAME_SIZE
                    if frames_count > 0:
                        arr = np.frombuffer(bytes(buf[:frames_count * FRAME_SIZE]), np.uint8)
                        arr_split = list(arr.reshape([frames_count, FRAME_H, FRAME_W, FRAME_C]))
                        for f in arr_split:
                            frame_queue.put(f)

                    if len(buf) < target:
                        frame_queue.put(None)
                        break
            except Exception as e:
                read_error.append(e)
                frame_queue.put(None)

        reader_thread = threading.Thread(target=ffmpeg_reader, daemon=True)
        reader_thread.start()

        frames = []
        predictions = []
        batch_count = 0
        global_start_idx = 0
        total_frames_read = 0
        frames_eof = False

        def get_more_frames(needed):
            nonlocal frames_eof, total_frames_read
            count = 0
            while count < needed and not frames_eof:
                try:
                    f = frame_queue.get(timeout=5.0)
                    if f is None:
                        frames_eof = True
                    else:
                        frames.append(f)
                        total_frames_read += 1
                        count += 1
                except queue.Empty:
                    if read_error:
                        raise read_error[0]
                    frames_eof = True
            return count

        def build_window(start_idx, available_right):
            """Construit une fenêtre WINDOW_SIZE avec padding aux bords."""
            left_needed = PADDING_FRAMES
            right_needed = PADDING_FRAMES

            if start_idx >= left_needed:
                left_part = frames[start_idx - left_needed: start_idx]
            else:
                pad = [frames[0]] * (left_needed - start_idx)
                left_part = pad + frames[0:start_idx]

            mid_len = WINDOW_SIZE - PADDING_FRAMES - PADDING_FRAMES
            mid_part = frames[start_idx: start_idx + mid_len]

            right_have = max(0, available_right - mid_len)
            if right_have >= right_needed:
                right_part = frames[start_idx + mid_len: start_idx + mid_len + right_needed]
            else:
                base = frames[start_idx + mid_len - 1] if (start_idx + mid_len - 1) < len(frames) else frames[-1]
                right_part = frames[start_idx + mid_len: start_idx + mid_len + right_have] + [base] * (right_needed - right_have)

            window = left_part + mid_part + right_part
            return np.asarray(window, dtype=np.uint8)

        # Remplir la première fenêtre
        get_more_frames(WINDOW_SIZE)

        if total_frames_read == 0:
            logging.warning(f"Aucune frame extraite pour {video_path.name}.")
            return []

        windows_batch = []

        while True:
            frames_offset = total_frames_read - len(frames)
            local_start_idx = global_start_idx - frames_offset

            to_read = max(0, (local_start_idx + WINDOW_SIZE) - len(frames))
            if to_read > 0:
                get_more_frames(to_read)

            frames_offset = total_frames_read - len(frames)
            local_start_idx = global_start_idx - frames_offset

            if local_start_idx >= len(frames):
                break

            available_right = max(0, len(frames) - local_start_idx)
            window_np = build_window(local_start_idx, available_right)

            if window_np.shape[0] != WINDOW_SIZE:
                if len(frames) == 0:
                    break
                lastf = frames[-1]
                add = WINDOW_SIZE - window_np.shape[0]
                window_np = np.concatenate([window_np, np.repeat(np.expand_dims(lastf, 0), add, axis=0)], axis=0)

            windows_batch.append(window_np)
            global_start_idx += WINDOW_STRIDE

            is_eof = (global_start_idx - (total_frames_read - len(frames))) >= len(frames) and frames_eof

            if len(windows_batch) == BATCH_SIZE or is_eof:
                # Le modèle ONNX attend l'entrée [B, T, H, W, C] en uint8 car la permutation
                # [B, C, T, H, W] et la division par 255.0 sont intégrées au graphe de calcul.
                batch_blob = np.stack(windows_batch)

                net.setInput(batch_blob)
                output = net.forward()

                # Appliquer sigmoid pour obtenir les probabilités
                batch_preds = 1.0 / (1.0 + np.exp(-output))

                for b_idx in range(batch_preds.shape[0]):
                    # Extraire la tranche valide (sans padding)
                    if len(batch_preds.shape) == 3:
                        pred_slice = batch_preds[b_idx, PADDING_FRAMES:WINDOW_SIZE - PADDING_FRAMES, 0]
                    elif len(batch_preds.shape) == 2:
                        pred_slice = batch_preds[b_idx, PADDING_FRAMES:WINDOW_SIZE - PADDING_FRAMES]
                    else:
                        # Fallback: aplatir
                        pred_flat = batch_preds[b_idx].flatten()
                        pred_slice = pred_flat[PADDING_FRAMES:WINDOW_SIZE - PADDING_FRAMES]

                    predictions.append(pred_slice)

                batch_count += 1
                windows_batch = []

                # Affichage du progrès à chaque lot (batch) pour un feedback en temps réel dans l'UI
                if batch_count % 1 == 0:
                    logging.info(f"INTERNAL_PROGRESS: {batch_count} batches - {video_path.name}")
                    print(f"INTERNAL_PROGRESS: {batch_count} batches - {video_path.name}", flush=True)

            # Pruning du tampon RAM
            frames_offset = total_frames_read - len(frames)
            next_local_start_idx = global_start_idx - frames_offset
            drop_count = max(0, next_local_start_idx - PADDING_FRAMES)
            if drop_count > 0 and len(frames) > drop_count:
                frames = frames[drop_count:]

        # Fermeture propre du processus FFmpeg
        try:
            process.stdout.close()
            process.stderr.close()
            process.wait(timeout=2)
        except Exception:
            pass

        if not predictions:
            return [[0, total_frames_read - 1]] if total_frames_read > 0 else []

        final_predictions = np.concatenate(predictions)[:total_frames_read]
        shot_boundaries = np.where(final_predictions > threshold)[0]

        if len(shot_boundaries) == 0:
            return [[0, total_frames_read - 1]] if total_frames_read > 0 else []

        detected_scenes = []
        last_cut = -1
        for cut in shot_boundaries:
            if cut > last_cut:
                detected_scenes.append([last_cut + 1, cut])
            last_cut = cut
        if last_cut < total_frames_read - 1:
            detected_scenes.append([last_cut + 1, total_frames_read - 1])

        return detected_scenes

    except Exception as e:
        logging.exception(f"Erreur lors de la détection de scènes pour {video_path.name}: {e}")
        return None


def process_single_video(idx, total, video_path, net, cfg):
    """Traite une seule vidéo : inférence, écriture CSV.

    Args:
        idx: index courant
        total: total de vidéos
        video_path: Path vers la vidéo
        net: réseau OpenCV DNN chargé
        cfg: configuration effective

    Returns:
        bool: True si succès
    """
    try:
        logging.info(f"PROCESSING_VIDEO: {idx + 1}/{total}: {video_path.name}")
        print(f"PROCESSING_VIDEO: {idx + 1}/{total}: {video_path.name}")

        t0 = time.perf_counter()

        scenes = detect_scenes_cv5(video_path, net, threshold=float(cfg["threshold"]))

        if scenes is None:
            logging.error(f"Échec du traitement de {video_path.name}")
            return False

        elapsed = time.perf_counter() - t0

        # Écriture CSV (format identique au pipeline legacy)
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

        logging.info(
            f"Succès: {output_csv_path.name} créé avec {len(scenes)} scènes "
            f"({elapsed:.2f}s, OpenCV 5.0 DNN)"
        )
        return True

    except Exception as e:
        logging.exception(f"Erreur worker pour {video_path}: {e}")
        return False


def setup_cuda_paths():
    """Recherche les répertoires de bibliothèques NVIDIA (CUDA/cuDNN) dans le venv
    courant et les injecte dans LD_LIBRARY_PATH pour permettre le chargement GPU par ONNX Runtime.
    """
    try:
        # Trouver le répertoire site-packages du venv courant
        venv_site_packages = Path(sys.executable).parent.parent / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
        if venv_site_packages.exists():
            # Trouver les dossiers nvidia/*/lib
            nvidia_dirs = list(venv_site_packages.glob("nvidia/*/lib"))
            if nvidia_dirs:
                paths = [str(d) for d in nvidia_dirs]
                current_ld = os.environ.get("LD_LIBRARY_PATH", "")
                if current_ld:
                    paths.append(current_ld)
                # Injecter dans le processus courant
                new_ld = ":".join(paths)
                os.environ["LD_LIBRARY_PATH"] = new_ld
                logging.info(f"CUDA_PATH_SETUP: LD_LIBRARY_PATH configuré avec les packages nvidia du venv: {len(nvidia_dirs)} répertoires ajoutés.")
    except Exception as e:
        logging.warning(f"CUDA_PATH_SETUP_WARNING: Impossible d'injecter automatiquement les chemins CUDA du venv: {e}")


def main():
    setup_cuda_paths()
    parser = argparse.ArgumentParser(
        description="Analyse des transitions vidéo avec TransNetV2 (OpenCV 5.0 DNN ONNX)."
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
    parser.add_argument("--batch_size", type=int, default=None, help="Taille de lot pour l'inférence. Défaut: 16")
    args = parser.parse_args()

    # Defaults
    defaults = {
        "threshold": 0.5,
        "window": 100,
        "stride": 50,
        "padding": 25,
        "ffmpeg_threads": 0,
        "batch_size": 16,
    }

    # Config JSON optionnel
    config_path = None
    if args.config:
        config_path = Path(args.config)
    else:
        candidate = BASE_DIR / "config" / "step3_cv5.json"
        if candidate.exists():
            config_path = candidate

    file_cfg = {}
    if config_path is not None:
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_cfg = json.load(f)
            logging.info(f"Configuration chargée depuis: {config_path}")
        except Exception as e:
            logging.exception(f"Impossible de charger la configuration {config_path}: {e}")

    # Fusion: defaults < JSON < CLI
    effective_cfg = dict(defaults)
    effective_cfg.update({k: v for k, v in file_cfg.items() if v is not None})

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

    # Propager les hyperparamètres globaux
    global WINDOW_SIZE, WINDOW_STRIDE, PADDING_FRAMES, FFMPEG_THREADS, BATCH_SIZE
    WINDOW_SIZE = int(effective_cfg["window"])
    WINDOW_STRIDE = int(effective_cfg["stride"])
    PADDING_FRAMES = int(effective_cfg["padding"])
    BATCH_SIZE = int(effective_cfg["batch_size"])
    FFMPEG_THREADS = int(effective_cfg["ffmpeg_threads"])

    logging.info(
        f"CONFIG_EFFECTIVE: threshold={effective_cfg['threshold']}, "
        f"window={WINDOW_SIZE}, stride={WINDOW_STRIDE}, padding={PADDING_FRAMES}, "
        f"ffmpeg_threads={FFMPEG_THREADS}, batch_size={BATCH_SIZE}"
    )
    logging.info(f"OpenCV version: {cv2.__version__}")
    logging.info(f"Backend: OpenCV DNN (ONNX), Engine: {'ENGINE_NEW' if hasattr(cv2.dnn, 'ENGINE_NEW') else 'LEGACY'}")

    # Résolution du chemin modèle
    model_path = Path(args.model) if args.model else ONNX_MODEL_PATH

    logging.info("--- Démarrage de l'analyse des transitions (OpenCV 5.0 DNN) ---")

    # Charger le modèle
    net = load_opencv_dnn_model(model_path)
    if net is None:
        sys.exit(1)

    # Validation de l'opérateur Slice
    logging.info("Validation de l'opérateur Slice ONNX...")
    if not validate_onnx_slice_operator(net, window_size=WINDOW_SIZE):
        logging.critical(
            "L'opérateur Slice n'est pas supporté correctement. "
            "Vérifiez la version d'OpenCV et le modèle ONNX."
        )
        sys.exit(1)

    # Trouver les vidéos à traiter
    videos = [p for ext in VIDEO_EXTENSIONS for p in WORK_DIR.rglob(f'*{ext}') if not p.with_suffix('.csv').exists()]
    total_videos = len(videos)
    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")
    print(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")

    if total_videos == 0:
        return

    # Traitement séquentiel (pas de multiprocessing pour OpenCV DNN)
    # OpenCV DNN n'est pas thread-safe dans le contexte fork, et spawn
    # serait trop coûteux pour recharger le modèle par worker.
    successful_count = 0
    t_start = time.perf_counter()

    for i, video_path in enumerate(videos):
        ok = process_single_video(i, total_videos, video_path, net, effective_cfg)
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
