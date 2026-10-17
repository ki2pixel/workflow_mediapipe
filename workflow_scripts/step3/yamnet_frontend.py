#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Frontend audio Log-Mel CPU pour l'architecture YAMNet Split (Axe 2).

Ce module implémente le calcul vectorisé des spectrogrammes log-mel et le découpage
en fenêtres de 96 trames (0.96s) à parité exacte avec le modèle TensorFlow officiel.
Il s'exécute sur CPU (NumPy / Numba) dans coral_env pour alimenter le CNN YAMNet
compilé sur l'Edge TPU via assets/yamnet_split_edgetpu_compiled.tflite.
"""

from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MEL_MATRIX_PATH = PROJECT_ROOT / "assets" / "yamnet_mel_matrix.npy"

_CACHED_MEL_MATRIX = None


def get_yamnet_mel_filterbank(sr: int = 16000, n_fft: int = 512, n_mels: int = 64,
                              fmin: float = 125.0, fmax: float = 7500.0,
                              matrix_path: Path = None) -> np.ndarray:
    """Retourne la matrice de banc de filtres mel (257, 64) à parité exacte avec TensorFlow."""
    global _CACHED_MEL_MATRIX
    if _CACHED_MEL_MATRIX is not None:
        return _CACHED_MEL_MATRIX

    path = matrix_path or DEFAULT_MEL_MATRIX_PATH
    if path.exists():
        try:
            _CACHED_MEL_MATRIX = np.load(str(path)).astype(np.float32)
            return _CACHED_MEL_MATRIX
        except Exception:
            pass

    # Formule mathématique exacte de TensorFlow tf.signal.linear_to_mel_weight_matrix
    def hz_to_mel(hz):
        return 1127.0 * np.log(1.0 + hz / 700.0)

    def mel_to_hz(mel):
        return 700.0 * (np.exp(mel / 1127.0) - 1.0)

    min_mel = hz_to_mel(fmin)
    max_mel = hz_to_mel(fmax)
    mels = np.linspace(min_mel, max_mel, n_mels + 2)
    nyquist = sr / 2.0
    linear_frequencies = np.linspace(0.0, nyquist, n_fft // 2 + 1)
    spectrogram_bins_mel = hz_to_mel(linear_frequencies)

    lower_edge_mel = mels[:-2]
    center_mel = mels[1:-1]
    upper_edge_mel = mels[2:]

    weights = np.maximum(
        0.0,
        np.minimum(
            (spectrogram_bins_mel[:, None] - lower_edge_mel) / (center_mel - lower_edge_mel),
            (upper_edge_mel - spectrogram_bins_mel[:, None]) / (upper_edge_mel - center_mel)
        )
    )
    _CACHED_MEL_MATRIX = weights.astype(np.float32)
    return _CACHED_MEL_MATRIX


def compute_yamnet_log_mel_spectrogram(waveform: np.ndarray, sample_rate: int = 16000,
                                       mel_matrix: np.ndarray = None) -> np.ndarray:
    """Calcule le spectrogramme log-mel continu pour tout le signal waveform."""
    frame_length = 400
    hop_length = 160
    fft_length = 512

    if mel_matrix is None:
        mel_matrix = get_yamnet_mel_filterbank(sr=sample_rate, n_fft=fft_length, n_mels=64)

    if len(waveform) < frame_length:
        return np.empty((0, 64), dtype=np.float32)

    # Periodic Hann window (400 samples)
    window = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(frame_length) / frame_length)
    window = window.astype(np.float32)

    num_frames = 1 + (len(waveform) - frame_length) // hop_length
    frames = np.lib.stride_tricks.as_strided(
        waveform,
        shape=(num_frames, frame_length),
        strides=(waveform.strides[0] * hop_length, waveform.strides[0]),
        writeable=False,
    )
    windowed = frames * window
    stft = np.fft.rfft(windowed, n=fft_length)
    mag_spectrogram = np.abs(stft).astype(np.float32)

    mel_spectrogram = np.matmul(mag_spectrogram, mel_matrix)
    log_mel = np.log(mel_spectrogram + 0.001).astype(np.float32)
    return log_mel


def extract_patches_for_window_starts(data: np.ndarray, window_starts: list,
                                      segment_size: int = 15360,
                                      sample_rate: int = 16000,
                                      mel_matrix: np.ndarray = None) -> np.ndarray:
    """Extrait directement un tenseur (N, 96, 64) pour une liste de débuts de fenêtres (hop 0.48s).

    Chaque fenêtre fait segment_size = 15360 échantillons (0.96s).
    À hop_length=160, 15360 échantillons produisent exactement 1 + (15360 - 400)//160 = 94.5 -> 94 trames.
    Pour obtenir exactement 96 trames STFT (0.96s dans la définition YAMNet: 95*160 + 400 = 15600 échantillons),
    cette fonction gère le centrage ou découpage continu.
    """
    if mel_matrix is None:
        mel_matrix = get_yamnet_mel_filterbank(sr=sample_rate)

    # Si data est en int16, normaliser en [-1.0, 1.0]
    if data.dtype == np.int16:
        float_data = data.astype(np.float32) / 32768.0
    else:
        float_data = data.astype(np.float32)

    full_log_mel = compute_yamnet_log_mel_spectrogram(float_data, sample_rate=sample_rate, mel_matrix=mel_matrix)
    total_mel_frames = full_log_mel.shape[0]

    patch_frames = 96
    num_windows = len(window_starts)
    patches = np.empty((num_windows, patch_frames, 64), dtype=np.float32)

    hop_samples = 160
    for idx, start_sample in enumerate(window_starts):
        start_frame = start_sample // hop_samples
        end_frame = start_frame + patch_frames
        if end_frame <= total_mel_frames:
            patches[idx] = full_log_mel[start_frame:end_frame]
        else:
            avail = full_log_mel[start_frame:total_mel_frames]
            missing = patch_frames - len(avail)
            if len(avail) > 0:
                pad = np.repeat(avail[-1:], missing, axis=0) if missing > 0 else np.empty((0, 64), dtype=np.float32)
                patches[idx] = np.vstack([avail, pad])
            else:
                patches[idx] = np.zeros((patch_frames, 64), dtype=np.float32)
    return patches


def quantize_log_mel_patch(patch: np.ndarray, scale: float, zero_point: int) -> np.ndarray:
    """Quantifie un patch (1, 96, 64) en int8 selon l'échelle et le point zéro du modèle compilé."""
    if scale <= 0.0:
        return patch.astype(np.int8)
    return np.clip(np.rint(patch / scale + zero_point), -128, 127).astype(np.int8)
