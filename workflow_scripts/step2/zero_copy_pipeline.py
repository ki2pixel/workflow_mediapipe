#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline d'Ingestion Asynchrone Zéro-Copie & Strides Tricks pour TransNetV2 (STEP2).
Double tampon Ping-Pong (2600 trames), lecture stdout.readinto hors-GIL,
vues 5D O(1) via sliding_window_view, formatage strict des timecodes HH:MM:SS.mmm
et émission périodique des logs UI Flask INTERNAL_PROGRESS.
"""

import os
import sys
import csv
import logging
import subprocess
import threading
import time
from pathlib import Path
from typing import List, Tuple, Optional, Generator, Any

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scenedetect import FrameTimecode

# --- Constantes architecturales TransNetV2 ---
FRAME_H: int = 27
FRAME_W: int = 48
FRAME_C: int = 3
FRAME_BYTES: int = FRAME_H * FRAME_W * FRAME_C  # 3 888 octets par trame

WINDOW_SIZE: int = 100
WINDOW_STRIDE: int = 50
PADDING_LEFT: int = 25
CENTRAL_START: int = 25
CENTRAL_END: int = 75
VALID_PREDS_PER_WIN: int = CENTRAL_END - CENTRAL_START  # 50 prédictions utiles

FPS_TARGET: float = 25.0
DECISION_THRESHOLD: float = 0.5


def build_reference_windows_global_pad(raw_frames: np.ndarray) -> np.ndarray:
    """
    Fonction de référence historique appliquant np.pad(..., mode='edge') global
    et extrayant les fenêtres par pas de 50 trames.
    Utilisée pour les tests unitaires de parité bit-à-bit.
    """
    n_frames = len(raw_frames)
    if n_frames == 0:
        return np.empty((0, WINDOW_SIZE, FRAME_H, FRAME_W, FRAME_C), dtype=np.uint8)

    no_padded_frames_start = PADDING_LEFT
    remainder = n_frames % WINDOW_STRIDE
    no_padded_frames_end = PADDING_LEFT + WINDOW_STRIDE - (remainder if remainder != 0 else WINDOW_STRIDE)

    start_frame = np.expand_dims(raw_frames[0], 0)
    end_frame = np.expand_dims(raw_frames[-1], 0)

    padded = np.concatenate(
        [start_frame] * no_padded_frames_start + [raw_frames] + [end_frame] * no_padded_frames_end,
        axis=0
    )

    windows = []
    ptr = 0
    while ptr + WINDOW_SIZE <= len(padded):
        windows.append(padded[ptr : ptr + WINDOW_SIZE])
        ptr += WINDOW_STRIDE

    return np.stack(windows)


def extract_windows_chunked_zero_copy(
    raw_frames: np.ndarray,
    windows_per_chunk: int = 50,
) -> np.ndarray:
    """
    Simule l'extraction par double tampon et sliding_window_view sur un tableau en mémoire
    pour valider la stricte parité bit-à-bit avec build_reference_windows_global_pad.
    Gère rigoureusement la capacité de 2 600 trames pour absorber N in [2501, 2524].
    """
    n_frames = len(raw_frames)
    if n_frames == 0:
        return np.empty((0, WINDOW_SIZE, FRAME_H, FRAME_W, FRAME_C), dtype=np.uint8)

    chunk_advance = windows_per_chunk * WINDOW_STRIDE  # 2500
    overlap_frames = WINDOW_SIZE - WINDOW_STRIDE  # 50
    buffer_cap = chunk_advance + overlap_frames + WINDOW_STRIDE  # 2600

    buf = np.empty((buffer_cap, FRAME_H, FRAME_W, FRAME_C), dtype=np.uint8)
    carry_50 = np.empty((overlap_frames, FRAME_H, FRAME_W, FRAME_C), dtype=np.uint8)
    last_valid = np.empty((1, FRAME_H, FRAME_W, FRAME_C), dtype=np.uint8)

    total_windows_needed = (n_frames + WINDOW_STRIDE - 1) // WINDOW_STRIDE
    windows_list = []

    raw_offset = 0
    is_first = True
    emitted_windows = 0

    while raw_offset < n_frames or is_first:
        if is_first:
            write_start = PADDING_LEFT
            read_len = min(2525, n_frames)
            buf[write_start : write_start + read_len] = raw_frames[raw_offset : raw_offset + read_len]
            raw_offset += read_len
            frames_read = read_len
            buf[0:PADDING_LEFT] = buf[PADDING_LEFT : PADDING_LEFT + 1]
            valid_buf_len = PADDING_LEFT + frames_read
        else:
            write_start = overlap_frames
            read_len = min(chunk_advance, n_frames - raw_offset)
            if read_len > 0:
                buf[write_start : write_start + read_len] = raw_frames[raw_offset : raw_offset + read_len]
                raw_offset += read_len
            frames_read = read_len
            buf[0:overlap_frames] = carry_50
            valid_buf_len = overlap_frames + frames_read

        if frames_read > 0:
            last_valid[0] = buf[valid_buf_len - 1]

        is_eof = raw_offset >= n_frames
        if not is_eof:
            np.copyto(carry_50, buf[chunk_advance : chunk_advance + overlap_frames])
            num_win = windows_per_chunk
            req_len = chunk_advance + overlap_frames
        else:
            num_win = total_windows_needed - emitted_windows
            if num_win <= 0:
                break
            req_len = num_win * WINDOW_STRIDE + overlap_frames
            buf[valid_buf_len:req_len] = last_valid

        view = sliding_window_view(
            buf[:req_len], window_shape=WINDOW_SIZE, axis=0
        )[::WINDOW_STRIDE].transpose(0, 4, 1, 2, 3)

        windows_list.append(np.copy(view[:num_win]))
        emitted_windows += num_win
        is_first = False
        if is_eof:
            break

    return np.concatenate(windows_list, axis=0)


def predictions_to_scenes(predictions: np.ndarray, threshold: float = DECISION_THRESHOLD) -> List[List[int]]:
    """
    Convertit les probabilités de coupure par trame (N,) en liste de segments de scènes
    [start_frame, end_frame] (index base 0 inclusifs).
    Strictement identique au comportement de production.
    """
    n_frames = len(predictions)
    if n_frames == 0:
        return []

    shot_boundaries = np.where(predictions > threshold)[0]
    if len(shot_boundaries) == 0:
        return [[0, n_frames - 1]]

    detected_scenes = []
    last_cut = -1
    for cut in shot_boundaries:
        if cut > last_cut:
            detected_scenes.append([last_cut + 1, int(cut)])
        last_cut = int(cut)
    if last_cut < n_frames - 1:
        detected_scenes.append([last_cut + 1, n_frames - 1])

    return detected_scenes


def write_scenes_to_csv(scenes: List[List[int]], output_csv_path: Path, fps: float = FPS_TARGET) -> None:
    """
    Écrit les segments de plans dans un fichier CSV avec formatage strict
    du timecode milliseconde HH:MM:SS.mmm via scenedetect FrameTimecode.
    """
    output_csv_path = Path(output_csv_path)
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


class ZeroCopyTransNetPipeline:
    """
    Pipeline d'ingestion asynchrone haute performance en double tampon Ping-Pong.
    - Thread Producteur : lit stdout FFmpeg via readinto() directement dans les tampons pré-alloués (hors GIL).
    - Thread Consommateur : applique le padding vectorisé, assemble les vues 5D O(1)
      via sliding_window_view et pilote l'inférence.
    - Capacité physique pré-allouée : 2 600 trames (résout le cas limite N in [2501, 2524]).
    """

    def __init__(
        self,
        engine: Any = None,
        windows_per_chunk: int = 50,
        ffmpeg_threads: int = 0,
    ) -> None:
        self.engine = engine
        self.windows_per_chunk = windows_per_chunk  # K = 50 fenêtres
        self.chunk_advance_frames = windows_per_chunk * WINDOW_STRIDE  # 2 500 trames
        self.overlap_frames = WINDOW_SIZE - WINDOW_STRIDE  # 50 trames
        self.nominal_chunk_capacity = self.chunk_advance_frames + self.overlap_frames  # 2 550 trames

        # Capacité physique 2 600 trames pour absorber le cas limite N in [2501, 2524] (51 fenêtres = 2600 trames)
        self.buffer_capacity_frames = self.nominal_chunk_capacity + WINDOW_STRIDE  # 2 600 trames
        self.ffmpeg_threads = ffmpeg_threads

        # Double Buffer (Ping-Pong) pré-alloué en RAM : 2 x [2600, 27, 48, 3] (~10.1 Mo chacun)
        self.buffers = [
            np.empty((self.buffer_capacity_frames, FRAME_H, FRAME_W, FRAME_C), dtype=np.uint8),
            np.empty((self.buffer_capacity_frames, FRAME_H, FRAME_W, FRAME_C), dtype=np.uint8),
        ]

    @staticmethod
    def _read_exact_into(stream, mv: memoryview) -> int:
        """
        Remplit un memoryview directement depuis le descripteur de fichier OS (hors GIL).
        Gère les lectures partielles du pipe POSIX jusqu'à complétion ou EOF.
        """
        total_read = 0
        target_len = len(mv)
        while total_read < target_len:
            n_bytes = stream.readinto(mv[total_read:])
            if not n_bytes:
                break
            total_read += n_bytes
        return total_read

    def iter_video_windows(
        self,
        video_path: str,
    ) -> Generator[Tuple[np.ndarray, int, int, bool], None, None]:
        """
        Générateur asynchrone produisant des vues 5D (num_win, 100, 27, 48, 3) zéro-copie
        au fur et à mesure du décodage FFmpeg.
        Rend (windows_5d_view, frames_in_chunk, total_raw_frames_so_far, is_eof).
        """
        video_path = Path(video_path)
        if not video_path.is_file():
            raise FileNotFoundError(f"Fichier vidéo introuvable : {video_path}")

        ffmpeg_cmd = [
            "ffmpeg",
            "-nostdin",
            "-v", "error",
            "-threads", str(self.ffmpeg_threads),
            "-i", str(video_path),
            "-vf", f"fps={FPS_TARGET},scale={FRAME_W}:{FRAME_H}:flags=bilinear",
            "-pix_fmt", "rgb24",
            "-f", "rawvideo",
            "pipe:1",
        ]

        proc = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=16 * 1024 * 1024,
        )

        free_slots: List[int] = [0, 1]
        ready_chunks: List[Optional[Tuple[int, int, bool, bool]]] = []
        cond = threading.Condition()
        producer_error: List[Exception] = []

        def _producer_worker() -> None:
            is_first_chunk = True
            try:
                assert proc.stdout is not None
                while True:
                    with cond:
                        while not free_slots:
                            cond.wait()
                        slot = free_slots.pop(0)

                    buf = self.buffers[slot]

                    if is_first_chunk:
                        write_start_frame = PADDING_LEFT  # index 25
                        frames_to_read = self.nominal_chunk_capacity - PADDING_LEFT  # 2 525 trames
                    else:
                        write_start_frame = self.overlap_frames  # index 50
                        frames_to_read = self.chunk_advance_frames  # 2 500 trames

                    target_slice = buf[write_start_frame : write_start_frame + frames_to_read]
                    mv = memoryview(target_slice).cast("B")

                    bytes_read = self._read_exact_into(proc.stdout, mv)
                    if bytes_read % FRAME_BYTES != 0:
                        raise RuntimeError(
                            f"Trame tronquée détectée dans le flux FFmpeg ({bytes_read} octets lus)."
                        )

                    frames_read = bytes_read // FRAME_BYTES
                    is_eof = frames_read < frames_to_read

                    with cond:
                        ready_chunks.append((slot, frames_read, is_first_chunk, is_eof))
                        cond.notify_all()

                    is_first_chunk = False
                    if is_eof:
                        break
            except Exception as exc:
                with cond:
                    producer_error.append(exc)
                    ready_chunks.append(None)
                    cond.notify_all()

        producer_thread = threading.Thread(target=_producer_worker, daemon=True)
        producer_thread.start()

        carry_50_frames = np.empty((self.overlap_frames, FRAME_H, FRAME_W, FRAME_C), dtype=np.uint8)
        last_valid_frame = np.empty((1, FRAME_H, FRAME_W, FRAME_C), dtype=np.uint8)
        total_raw_frames = 0
        emitted_windows = 0

        try:
            while True:
                with cond:
                    while not ready_chunks:
                        cond.wait()
                    item = ready_chunks.pop(0)

                if item is None:
                    if producer_error:
                        raise producer_error[0]
                    break

                slot, frames_read, is_first, is_eof = item
                buf = self.buffers[slot]
                total_raw_frames += frames_read

                if is_first and frames_read == 0:
                    raise RuntimeError("Le flux vidéo décodé ne contient aucune trame.")

                # 1. Padding bord gauche (initial) ou recouvrement 50 trames
                if is_first:
                    buf[0:PADDING_LEFT] = buf[PADDING_LEFT : PADDING_LEFT + 1]
                    valid_buf_len = PADDING_LEFT + frames_read
                else:
                    if frames_read > 0 or not is_eof:
                        buf[0 : self.overlap_frames] = carry_50_frames
                    valid_buf_len = self.overlap_frames + frames_read

                if frames_read > 0:
                    last_valid_frame[0] = buf[valid_buf_len - 1]

                # 2. Sauvegarde des 50 dernières trames pour le chunk suivant si le bloc est complet
                if not is_eof:
                    np.copyto(carry_50_frames, buf[self.chunk_advance_frames : self.nominal_chunk_capacity])
                    num_win = self.windows_per_chunk
                    required_buf_len = self.nominal_chunk_capacity
                else:
                    total_windows_needed = (total_raw_frames + WINDOW_STRIDE - 1) // WINDOW_STRIDE
                    num_win = total_windows_needed - emitted_windows
                    if num_win <= 0:
                        with cond:
                            free_slots.append(slot)
                            cond.notify_all()
                        break

                    required_buf_len = num_win * WINDOW_STRIDE + self.overlap_frames
                    if not is_first and frames_read == 0:
                        buf[0 : self.overlap_frames] = carry_50_frames

                    # Padding bord droit in-place avec la dernière trame valide (résout N in [2501, 2524])
                    buf[valid_buf_len : required_buf_len] = last_valid_frame

                # 3. Création de la vue 5D zéro-copie [num_win, 100, 27, 48, 3] en O(1)
                # Strides : (194400, 3888, 144, 3, 1)
                windows_5d_view = sliding_window_view(
                    buf[:required_buf_len], window_shape=WINDOW_SIZE, axis=0
                )[::WINDOW_STRIDE].transpose(0, 4, 1, 2, 3)

                emitted_windows += num_win

                yield windows_5d_view[:num_win], frames_read, total_raw_frames, is_eof

                with cond:
                    free_slots.append(slot)
                    cond.notify_all()

                if is_eof:
                    break

            producer_thread.join(timeout=5.0)
            proc.wait(timeout=5.0)
        finally:
            if proc.poll() is None:
                proc.kill()

    def process_video(
        self,
        video_path: str,
        threshold: float = DECISION_THRESHOLD,
    ) -> Tuple[np.ndarray, List[List[int]]]:
        """
        Traite une vidéo complète avec l'engine d'inférence configuré.
        Émet périodiquement les logs INTERNAL_PROGRESS avec flush=True.
        Retourne (frame_probabilities (N,), scenes [[start, end], ...]).
        """
        video_name = Path(video_path).name
        all_predictions: List[np.ndarray] = []
        total_frames = 0
        batch_idx = 0

        for windows_5d, frames_read, total_so_far, is_eof in self.iter_video_windows(video_path):
            total_frames = total_so_far
            if self.engine is not None:
                chunk_probs = self.engine.infer_windows(windows_5d)
                all_predictions.append(chunk_probs)

            batch_idx += 1
            # Émission conforme du log de progression Flask
            processed_frames = min(len(all_predictions) * self.windows_per_chunk * WINDOW_STRIDE, total_frames) if all_predictions else total_frames
            pct = int((processed_frames / total_frames * 100.0)) if total_frames > 0 else 0
            progress_msg = f"INTERNAL_PROGRESS: {processed_frames}/{total_frames} frames ({pct}%) - {video_name}"
            logging.info(progress_msg)
            print(progress_msg, flush=True)

        if not all_predictions:
            return np.empty((0,), dtype=np.float32), []

        frame_probabilities = np.concatenate(all_predictions)[:total_frames]
        scenes = predictions_to_scenes(frame_probabilities, threshold=threshold)
        return frame_probabilities, scenes


def _ensure_nvidia_libs() -> None:
    """Précharge les bibliothèques CUDA/cuDNN installées par pip dans site-packages/nvidia."""
    try:
        import ctypes
        import site
        packages = site.getsitepackages()
        for sp in packages:
            nvidia_dir = os.path.join(sp, "nvidia")
            if os.path.isdir(nvidia_dir):
                for root, _, files in os.walk(nvidia_dir):
                    if os.path.basename(root) == "lib":
                        for f in files:
                            if ".so" in f:
                                try:
                                    ctypes.CDLL(os.path.join(root, f), mode=ctypes.RTLD_GLOBAL)
                                except Exception:
                                    pass
    except Exception:
        pass


class TransNetV2GpuEngine:
    """
    Moteur d'inférence ONNX Runtime optimisé avec IOBinding persistant,
    arène VRAM kSameAsRequested, recherche d'algorithme cuDNN EXHAUSTIVE (repli HEURISTIC via STEP2_CUDNN_ALGO_SEARCH)
    et désactivation stricte de TF32 (use_tf32=0) pour garantir l'invariance FP32 (|Delta P| < 1e-5).
    """

    def __init__(
        self,
        onnx_path: str,
        batch_size: int = 8,
        device_id: int = 0,
        force_cpu: bool = False,
        use_tf32: bool = False,
    ) -> None:
        if not os.path.isfile(onnx_path):
            raise FileNotFoundError(f"Modèle ONNX introuvable : {onnx_path}")

        self.onnx_path = onnx_path
        self.device_id = device_id
        self.batch_size = batch_size
        self.use_tf32 = use_tf32
        self.force_cpu = force_cpu

        env_force_cpu = os.environ.get("STEP2_CV5_FORCE_CPU", "false").lower() == "true"
        effective_force_cpu = force_cpu or env_force_cpu

        cudnn_algo = os.environ.get("STEP2_CUDNN_ALGO_SEARCH", "EXHAUSTIVE").upper()
        if cudnn_algo not in ("EXHAUSTIVE", "HEURISTIC", "DEFAULT"):
            cudnn_algo = "EXHAUSTIVE"

        if not effective_force_cpu:
            _ensure_nvidia_libs()

        try:
            self._init_session(self.batch_size, effective_force_cpu, cudnn_algo)
        except Exception as e:
            self._cleanup_session()
            if not effective_force_cpu and self.batch_size > 8:
                fallback_batch = 8
                logging.warning(
                    f"Échec initialisation CUDA avec batch_size={self.batch_size} ({e}). "
                    f"Adaptation dynamique de la taille de lot à {fallback_batch} pour cartes 4 Go..."
                )
                try:
                    self._init_session(fallback_batch, effective_force_cpu, cudnn_algo)
                except Exception as e2:
                    self._cleanup_session()
                    logging.warning(
                        f"Échec initialisation CUDA avec batch={fallback_batch} ({e2}). Bascule automatique sur CPU..."
                    )
                    self._init_session(self.batch_size, force_cpu=True, cudnn_algo="DEFAULT")
            elif not effective_force_cpu:
                self._cleanup_session()
                logging.warning(f"Échec initialisation CUDA ({e}). Bascule automatique sur CPU...")
                self._init_session(self.batch_size, force_cpu=True, cudnn_algo="DEFAULT")
            else:
                raise

    def _cleanup_session(self) -> None:
        """Libère explicitement les tampons IOBinding et la session ONNX pour récupérer la VRAM."""
        for attr in ("io_binding", "input_ortvalue", "output_ortvalues", "session"):
            if hasattr(self, attr):
                try:
                    delattr(self, attr)
                except Exception:
                    pass
        import gc
        gc.collect()

    def _init_session(self, batch_size: int, force_cpu: bool, cudnn_algo: str) -> None:
        import onnxruntime as ort
        ort.set_default_logger_severity(3)

        self.batch_size = batch_size
        self.input_shape = (self.batch_size, WINDOW_SIZE, FRAME_H, FRAME_W, FRAME_C)

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        sess_options.enable_mem_pattern = True
        sess_options.enable_cpu_mem_arena = True
        sess_options.log_severity_level = 3

        providers = []
        available = ort.get_available_providers()
        if not force_cpu and "CUDAExecutionProvider" in available:
            providers.append(
                (
                    "CUDAExecutionProvider",
                    {
                        "device_id": self.device_id,
                        "arena_extend_strategy": "kSameAsRequested",
                        "cudnn_conv_algo_search": cudnn_algo,
                        "do_copy_in_default_stream": "1",
                        "use_tf32": 1 if self.use_tf32 else 0,
                    },
                )
            )
        if "CPUExecutionProvider" in available:
            providers.append("CPUExecutionProvider")
        if not providers:
            providers = ["CPUExecutionProvider"]

        self.session = ort.InferenceSession(
            str(self.onnx_path), sess_options=sess_options, providers=providers
        )
        self.active_provider = self.session.get_providers()[0]
        self.is_gpu = self.active_provider == "CUDAExecutionProvider"
        self.backend_label = (
            f"ONNX Runtime (CUDA - cuDNN {cudnn_algo})" if self.is_gpu else "ONNX Runtime (CPU)"
        )
        logging.info(
            f"TransNetV2GpuEngine initialisé : {self.backend_label} [batch={self.batch_size}, tf32={int(self.use_tf32)}]"
        )

        self.input_name = self.session.get_inputs()[0].name
        self.output_meta = self.session.get_outputs()

        # Tampon Hôte contigu d'assemblage DMA
        self.host_staging_buffer = np.zeros(self.input_shape, dtype=np.uint8)

        # Pré-allocation persistante sur VRAM GPU (ou CPU) et configuration IOBinding
        self.io_binding = self.session.io_binding()
        target_device = "cuda" if self.is_gpu else "cpu"

        self.input_ortvalue = ort.OrtValue.ortvalue_from_numpy(
            self.host_staging_buffer, target_device, self.device_id
        )
        self.io_binding.bind_ortvalue_input(self.input_name, self.input_ortvalue)

        self.output_ortvalues = []
        for out_node in self.output_meta:
            raw_shape = out_node.shape
            out_shape = [self.batch_size, WINDOW_SIZE]
            if len(raw_shape) == 3:
                out_shape.append(raw_shape[2] if isinstance(raw_shape[2], int) else 1)

            ort_out = ort.OrtValue.ortvalue_from_shape_and_type(
                out_shape, np.float32, target_device, self.device_id
            )
            self.output_ortvalues.append(ort_out)
            self.io_binding.bind_ortvalue_output(out_node.name, ort_out)

        # Passe de Warm-up obligatoire pour verrouiller les kernels cuDNN optimaux
        self._warmup()

    def _warmup(self) -> None:
        """Exécute une passe à blanc à lot fixe pour verrouiller les kernels cuDNN optimaux."""
        self.session.run_with_iobinding(self.io_binding)
        self.io_binding.synchronize_outputs()

    def infer_windows(self, windows_5d_view: np.ndarray) -> np.ndarray:
        """
        Infère un ensemble de M fenêtres issues d'une vue 5D zéro-copie (M, 100, 27, 48, 3)
        et retourne les probabilités de la tranche centrale [25:75] aplatie de taille (M * 50,).
        """
        num_windows = windows_5d_view.shape[0]
        if num_windows == 0:
            return np.empty((0,), dtype=np.float32)

        probs_out = np.empty((num_windows, VALID_PREDS_PER_WIN), dtype=np.float32)

        offset = 0
        while offset < num_windows:
            valid_b = min(self.batch_size, num_windows - offset)
            batch_slice_view = windows_5d_view[offset : offset + valid_b]

            # Copie vectorisée C-level depuis la vue chevauchante vers le tampon Hôte contigu
            np.copyto(self.host_staging_buffer[:valid_b], batch_slice_view)
            if valid_b < self.batch_size:
                # Maintien de la forme statique exacte pour éviter un re-tuning cuDNN
                self.host_staging_buffer[valid_b:].fill(0)

            # Transfert H2D in-place vers l'adresse VRAM pré-allouée sans réallocation
            self.input_ortvalue.update_inplace(self.host_staging_buffer)

            # Exécution des kernels sur GPU via IOBinding
            self.session.run_with_iobinding(self.io_binding)

            # Transfert D2H unique du tenseur de logits (~10 Ko) vers RAM
            logits = self.output_ortvalues[0].numpy()
            if logits.ndim == 3:
                logits = logits.squeeze(-1)

            # Extraction immédiate de la tranche centrale [25:75] avant calcul de la sigmoïde
            central_logits = logits[:valid_b, CENTRAL_START:CENTRAL_END]

            # Sigmoïde vectorisée numériquement stable : 1 / (1 + exp(-x))
            target_out = probs_out[offset : offset + valid_b]
            np.negative(central_logits, out=target_out)
            np.exp(target_out, out=target_out)
            target_out += 1.0
            np.divide(1.0, target_out, out=target_out)

            offset += valid_b

        return probs_out.reshape(-1)


class OpenCV5CpuEngine:
    """Moteur d'inférence basé sur OpenCV DNN (ENGINE_NEW CPU)."""

    def __init__(self, net: Any, batch_size: int = 25) -> None:
        self.net = net
        self.batch_size = batch_size
        import cv2
        self.backend_label = f"OpenCV DNN {cv2.__version__} (ENGINE_NEW CPU)"

    def infer_windows(self, windows_5d_view: np.ndarray) -> np.ndarray:
        num_windows = windows_5d_view.shape[0]
        if num_windows == 0:
            return np.empty((0,), dtype=np.float32)

        probs_out = np.empty((num_windows, VALID_PREDS_PER_WIN), dtype=np.float32)

        offset = 0
        while offset < num_windows:
            valid_b = min(self.batch_size, num_windows - offset)
            batch_slice = np.ascontiguousarray(windows_5d_view[offset : offset + valid_b])

            self.net.setInput(batch_slice)
            output = self.net.forward()
            if output.ndim == 3:
                output = output.squeeze(-1)

            central_logits = output[:valid_b, CENTRAL_START:CENTRAL_END]

            target_out = probs_out[offset : offset + valid_b]
            np.negative(central_logits, out=target_out)
            np.exp(target_out, out=target_out)
            target_out += 1.0
            np.divide(1.0, target_out, out=target_out)

            offset += valid_b

        return probs_out.reshape(-1)


def create_transnet_engine(
    model_path: Path,
    batch_size: int = 25,
    force_cpu: bool = False,
    device: Optional[str] = None,
    use_tf32: bool = False,
) -> Any:
    """
    Instancie le moteur d'inférence optimal selon les ressources disponibles :
    1. ONNX Runtime CUDA avec IOBinding (nominal haute performance).
    2. OpenCV 5.0 DNN orienté graphe (ENGINE_NEW CPU) si disponible et demandé.
    3. ONNX Runtime CPU avec IOBinding en repli universel.
    """
    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"Modèle ONNX introuvable: {model_path}")

    env_force_cpu = os.environ.get("STEP2_CV5_FORCE_CPU", "false").lower() == "true"
    if device is not None:
        effective_force_cpu = (device.lower() == "cpu") or env_force_cpu
    else:
        effective_force_cpu = force_cpu or env_force_cpu

    # 1. Tentative ONNX Runtime GPU CUDA
    if not effective_force_cpu:
        try:
            import onnxruntime as ort
            if "CUDAExecutionProvider" in ort.get_available_providers():
                logging.info("Initialisation du moteur TransNetV2GpuEngine (CUDA)...")
                engine = TransNetV2GpuEngine(
                    str(model_path),
                    batch_size=batch_size,
                    force_cpu=False,
                    use_tf32=use_tf32,
                )
                if engine.is_gpu:
                    return engine
        except Exception as e:
            logging.warning(f"Échec initialisation CUDAExecutionProvider: {e}. Bascule sur le fallback CPU...")

    # 2. Tentative OpenCV 5.0 DNN Graph Engine (si ENGINE_NEW est supporté)
    try:
        import cv2
        if hasattr(cv2.dnn, "DNN_ENGINE_NEW") or hasattr(cv2.dnn, "ENGINE_NEW"):
            logging.info("Tentative de chargement du modèle via OpenCV 5.0 DNN ENGINE_NEW...")
            net = cv2.dnn.readNetFromONNX(str(model_path))
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            if hasattr(cv2.dnn, "DNN_ENGINE_NEW"):
                net.set(cv2.dnn.DNN_ENGINE_NEW, True)
            elif hasattr(cv2.dnn, "ENGINE_NEW"):
                net.setEngineType(cv2.dnn.ENGINE_NEW)
            logging.info("Moteur OpenCV 5.0 DNN chargé avec succès.")
            return OpenCV5CpuEngine(net, batch_size=batch_size)
    except Exception as dnn_e:
        logging.info(f"OpenCV DNN non retenu ({dnn_e}). Utilisation de ONNX Runtime CPU...")

    # 3. Repli nominal CPU : ONNX Runtime CPU avec IOBinding
    logging.info("Initialisation du moteur TransNetV2GpuEngine en mode CPU (IOBinding)...")
    return TransNetV2GpuEngine(
        str(model_path),
        batch_size=batch_size,
        force_cpu=True,
        use_tf32=use_tf32,
    )
