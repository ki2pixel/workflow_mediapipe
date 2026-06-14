#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'analyse audio (VAD + Diarisation) avec Google Coral Edge TPU
Version Ubuntu - Étape 4 (Alternative à Pyannote/Lemonfox)

Algorithmes implémentés (Audit TPU vs GPU "Camille") :
- Fenêtrage glissant avec overlap 50% (hop 0.48s)
- Seuil VAD calibré pour compensation quantification INT8
- Filtre Médian 1D sur les probabilités de parole
- Machine à États Finis (FSM) avec Hangover pour fusion micro-silences
- Clustering Spectral Adaptatif (Eigen-gap / Silhouette Score)
- Section speaker_stats dans le JSON de sortie
"""

import os
import sys
import json
import argparse
import logging
import subprocess
import urllib.request
import numpy as np
import math
import tempfile
from pathlib import Path
from datetime import datetime
from enum import Enum
import threading
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import os

# --- Process-level globals ---
_tpu_lock = threading.Lock()
_yamnet_interp = None
_thread_local = threading.local()

def get_extractor_model_cached(model_path):
    if not hasattr(_thread_local, "extractor_model"):
        model_str = str(model_path)
        if model_str.endswith('.onnx'):
            if not HAS_ONNX:
                raise ImportError(f"Cannot load {model_str}: onnxruntime is not installed.")
            
            import multiprocessing
            step4_workers_str = os.environ.get("STEP4_MAX_WORKERS", "")
            max_workers = int(step4_workers_str) if step4_workers_str.isdigit() else max(1, multiprocessing.cpu_count() // 2)
            # Allocate the total CPU threads evenly among the max_workers
            onnx_threads = max(1, multiprocessing.cpu_count() // max_workers)
            
            sess_options = ort.SessionOptions()
            sess_options.intra_op_num_threads = onnx_threads
            sess_options.inter_op_num_threads = 1
            # Optimize execution mode for NUMA architecture
            sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            _thread_local.extractor_model = ort.InferenceSession(model_str, sess_options, providers=['CPUExecutionProvider'])
        else:
            import tflite_runtime.interpreter as tflite
            import multiprocessing
            step4_workers_str = os.environ.get("STEP4_MAX_WORKERS", "")
            max_workers = int(step4_workers_str) if step4_workers_str.isdigit() else max(1, multiprocessing.cpu_count() // 2)
            xnnpack_threads = max(1, multiprocessing.cpu_count() // max_workers)
            
            interp = tflite.Interpreter(model_path=model_str, num_threads=xnnpack_threads)
            interp.allocate_tensors()
            _thread_local.extractor_model = interp
    return _thread_local.extractor_model

# TFLite / PyCoral imports
# TFLite imports
import tflite_runtime.interpreter as tflite
try:
    import onnxruntime as ort
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False

try:
    import scipy.io.wavfile as wavfile
    from sklearn.cluster import SpectralClustering, AgglomerativeClustering
    from sklearn.metrics import silhouette_score
except ImportError as e:
    logging.critical(f"ERREUR: scipy ou scikit-learn manquant. Installez-les dans coral_env (pip install scipy scikit-learn). Erreur: {e}")
    sys.exit(1)

# --- Configuration Globale ---
WORK_DIR = Path(os.getcwd())
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')

# Modèles TPU par défaut
YAMNET_URL = "https://s3.ap-northeast-2.wasabisys.com/pinto-model-zoo/097_YAMNet/resources.tar.gz"

# --- Defaults algorithmiques (Audit Camille) ---
DEFAULT_VAD_THRESHOLD = 0.20
DEFAULT_HOP_OVERLAP = 0.5  # 50% overlap
DEFAULT_MEDIAN_FILTER_SIZE = 5
DEFAULT_HANGOVER_SEC = 1.0
DEFAULT_MAX_SPEAKERS = 5
DEFAULT_MIN_CLUSTER_EMBEDDINGS = 4
DEFAULT_CLUSTERING_THRESHOLD = 0.32
DEFAULT_MIN_SPEAKER_SPEECH_DURATION = 7.0

# --- ECAPA-TDNN Log-Mel Configuration ---
# Must match the training/calibration parameters used in prepare_ecapa_model.py
ECAPA_SAMPLE_RATE = 16000
ECAPA_N_MELS = 80
ECAPA_N_FFT = 400        # 25ms window at 16kHz
ECAPA_HOP_LENGTH = 160   # 10ms hop at 16kHz
ECAPA_FIXED_DURATION_SEC = 3.0  # Fixed input duration for the model
ECAPA_FIXED_N_FRAMES = int(np.ceil(ECAPA_FIXED_DURATION_SEC * ECAPA_SAMPLE_RATE / ECAPA_HOP_LENGTH))


# --- Log-Mel Spectrogram Extraction (CPU-side) ---
# These functions are the EXACT same as used during model calibration,
# ensuring consistency between quantization calibration and runtime inference.

def _create_mel_filterbank(sr, n_fft, n_mels):
    """Create a Mel filter bank matrix (n_mels, n_fft//2+1)."""
    def _hz_to_mel(hz):
        return 2595.0 * np.log10(1.0 + hz / 700.0)

    def _mel_to_hz(mel):
        return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)

    n_freqs = n_fft // 2 + 1
    low_mel = _hz_to_mel(0)
    high_mel = _hz_to_mel(sr / 2)
    mel_points = np.linspace(low_mel, high_mel, n_mels + 2)
    hz_points = _mel_to_hz(mel_points)
    bin_points = np.floor((n_fft + 1) * hz_points / sr).astype(int)

    filterbank = np.zeros((n_mels, n_freqs), dtype=np.float32)
    for i in range(n_mels):
        left = bin_points[i]
        center = bin_points[i + 1]
        right = bin_points[i + 2]
        for j in range(left, center):
            if center > left:
                filterbank[i, j] = (j - left) / (center - left)
        for j in range(center, right):
            if right > center:
                filterbank[i, j] = (right - j) / (right - center)

    return filterbank


# Module-level cache for the Mel filter bank (computed once)
_MEL_FILTERBANK_CACHE = None


def compute_log_mel_spectrogram(waveform_np, sr=ECAPA_SAMPLE_RATE,
                                 n_mels=ECAPA_N_MELS, n_fft=ECAPA_N_FFT,
                                 hop_length=ECAPA_HOP_LENGTH):
    """Compute Log-Mel spectrogram using numpy/scipy (CPU-side).

    Identical to the calibration function in prepare_ecapa_model.py.

    Args:
        waveform_np: 1D float32 numpy array, mono, 16kHz.
        sr: Sample rate (16000).
        n_mels: Number of Mel filter banks (80).
        n_fft: FFT window size (400 = 25ms).
        hop_length: Hop size (160 = 10ms).

    Returns:
        Log-Mel spectrogram of shape (n_mels, T) as float32.
    """
    from scipy.signal import stft
    from scipy.signal.windows import hann

    global _MEL_FILTERBANK_CACHE

    # STFT
    window = hann(n_fft, sym=False)
    _, _, Zxx = stft(waveform_np, fs=sr, window=window, nperseg=n_fft,
                     noverlap=n_fft - hop_length, nfft=n_fft, boundary=None,
                     padded=False)
    power_spec = np.abs(Zxx) ** 2  # (n_fft//2 + 1, T)

    # Mel filter bank (cached)
    if _MEL_FILTERBANK_CACHE is None:
        _MEL_FILTERBANK_CACHE = _create_mel_filterbank(sr, n_fft, n_mels)
    mel_spec = _MEL_FILTERBANK_CACHE @ power_spec  # (n_mels, T)

    # Log compression
    return np.log(np.maximum(mel_spec, 1e-10)).astype(np.float32)


def _pad_or_trim_mel(log_mel, target_frames=ECAPA_FIXED_N_FRAMES):
    """Pad or trim spectrogram to fixed number of frames."""
    n_mels, n_frames = log_mel.shape
    if n_frames >= target_frames:
        return log_mel[:, :target_frames]
    else:
        pad_width = target_frames - n_frames
        return np.pad(log_mel, ((0, 0), (0, pad_width)), mode='constant',
                      constant_values=np.log(1e-10))


def _extract_3s_segment(data, sample_rate, center_sample):
    """Extract a 3.0-second waveform segment centered at center_sample.
    Pads with silence if out of bounds.
    """
    half_size = int(3.0 * sample_rate / 2)  # 24000 samples for 16kHz
    start = center_sample - half_size
    end = center_sample + half_size
    
    # Pad if out of bounds
    if start < 0:
        pad_left = -start
        start = 0
    else:
        pad_left = 0
        
    if end > len(data):
        pad_right = end - len(data)
        end = len(data)
    else:
        pad_right = 0
        
    segment = data[start:end]
    if pad_left > 0 or pad_right > 0:
        segment = np.pad(segment, (pad_left, pad_right), mode='constant')
        
    return segment.astype(np.float32) / 32768.0




def extract_ecapa_embedding_batch(waveform_segments, extractor_model):
    """Extract a batch of 192D speaker embeddings from waveform segments.

    Pipeline:
    1. Compute Log-Mel spectrogram for each segment
    2. CMN normalization
    3. Run batched Inference

    Args:
        waveform_segments: List of 1D float32 numpy arrays (mono, 16kHz).
        extractor_model: ONNX InferenceSession or TFLite Interpreter.

    Returns:
        2D float32 numpy array of shape (batch, 192).
    """
    log_mels = []
    for wf in waveform_segments:
        log_mel = compute_log_mel_spectrogram(wf)
        log_mel = _pad_or_trim_mel(log_mel)  # (80, 300)
        log_mel = log_mel - np.mean(log_mel, axis=1, keepdims=True)
        log_mels.append(log_mel)

    # shape: (batch, 80, 300)
    input_data = np.stack(log_mels, axis=0).astype(np.float32)

    if hasattr(extractor_model, 'run'):
        # ONNX mode
        input_name = extractor_model.get_inputs()[0].name
        output = extractor_model.run(None, {input_name: input_data})[0]
        return output
    else:
        # TFLite fallback (iterative over batch since it doesn't support dynamic batching)
        input_details = extractor_model.get_input_details()[0]
        output_details = extractor_model.get_output_details()[0]
        
        embeddings = []
        for i in range(input_data.shape[0]):
            single_input = input_data[i:i+1, :, :]
            extractor_model.set_tensor(input_details['index'], single_input)
            extractor_model.invoke()
            emb = extractor_model.get_tensor(output_details['index'])
            embeddings.append(emb.flatten())
            
        return np.array(embeddings)


class VADState(Enum):
    """États de la Machine à États Finis (FSM) pour la VAD."""
    SILENCE = "SILENCE"
    SPEECH_DETECTED = "SPEECH_DETECTED"
    HANGOVER = "HANGOVER"


def download_model(url: str, path: Path):
    if not path.exists():
        import tarfile
        import io
        logging.info(f"Téléchargement du modèle: {path.name} depuis {url}...")
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with urllib.request.urlopen(url) as response:
                with tarfile.open(fileobj=io.BytesIO(response.read()), mode="r:gz") as tar:
                    member = tar.getmember("saved_model/model_full_integer_quant.tflite")
                    with tar.extractfile(member) as f_in, open(path, 'wb') as f_out:
                        f_out.write(f_in.read())
            logging.info("Téléchargement et extraction terminés.")
        except Exception as e:
            logging.critical(f"Échec du téléchargement du modèle YAMNet: {e}")
            raise e


def extract_audio(video_path: Path, temp_wav: Path):
    """Extrait l'audio de la vidéo en WAV 16kHz mono (Requis pour YAMNet)"""
    cmd = [
        'ffmpeg', '-y', '-i', str(video_path),
        '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
        '-loglevel', 'error', str(temp_wav)
    ]
    subprocess.run(cmd, check=True)


def _run_ffprobe_duration(video_path: Path) -> float:
    """Retourne la durée (en secondes) via ffprobe, ou -1 en cas d'échec."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "default=nw=1:nk=1", str(video_path)
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True
        )
        return float(result.stdout.strip())
    except Exception as e:
        logging.warning(f"ffprobe a échoué pour {video_path.name}: {e}")
        return -1.0


def apply_median_filter_vad(probabilities, kernel_size=DEFAULT_MEDIAN_FILTER_SIZE):
    """Applique un filtre médian 1D sur les probabilités de parole.

    Élimine les pics isolés transitoires (toux, chocs physiques) sans
    altérer les zones de parole continue.

    Args:
        probabilities: Array 1D des probabilités de parole brutes.
        kernel_size: Taille du noyau médian (impaire, typiquement 3 ou 5).

    Returns:
        Array 1D des probabilités filtrées.
    """
    if len(probabilities) < kernel_size:
        return probabilities

    # Forcer taille impaire
    if kernel_size % 2 == 0:
        kernel_size += 1

    try:
        from scipy.signal import medfilt
        return medfilt(probabilities, kernel_size=kernel_size)
    except ImportError:
        # Fallback numpy si scipy absent
        half_w = kernel_size // 2
        filtered = probabilities.copy()
        for i in range(half_w, len(probabilities) - half_w):
            filtered[i] = np.median(probabilities[i - half_w:i + half_w + 1])
        return filtered


def apply_fsm_hangover(vad_flags, hop_sec, hangover_sec=DEFAULT_HANGOVER_SEC):
    """Applique la Machine à États Finis (FSM) avec Hangover sur les décisions VAD.

    Transitions :
    - SILENCE → (flag=True) → SPEECH_DETECTED (ouverture segment)
    - SPEECH_DETECTED → (flag=False) → HANGOVER (VAD=True, init compteur)
    - HANGOVER → (flag=True) → SPEECH_DETECTED (reset compteur)
    - HANGOVER → (compteur ≥ limite) → SILENCE (clôture segment)

    Le hangover comble les micro-silences physiologiques intra-mots.

    Args:
        vad_flags: Liste de booleans (True=speech détecté par le seuil).
        hop_sec: Durée du pas entre fenêtres (en secondes).
        hangover_sec: Durée du maintien hangover (en secondes).

    Returns:
        Liste de booleans après application du hangover.
    """
    if not vad_flags:
        return []

    hangover_limit = max(1, int(math.ceil(hangover_sec / hop_sec)))
    state = VADState.SILENCE
    hangover_counter = 0
    result = []

    for flag in vad_flags:
        if state == VADState.SILENCE:
            if flag:
                state = VADState.SPEECH_DETECTED
                result.append(True)
            else:
                result.append(False)

        elif state == VADState.SPEECH_DETECTED:
            if flag:
                result.append(True)
            else:
                state = VADState.HANGOVER
                hangover_counter = 0
                result.append(True)  # Maintien pendant hangover

        elif state == VADState.HANGOVER:
            if flag:
                state = VADState.SPEECH_DETECTED
                hangover_counter = 0
                result.append(True)
            else:
                hangover_counter += 1
                if hangover_counter >= hangover_limit:
                    state = VADState.SILENCE
                    result.append(False)
                else:
                    result.append(True)  # Maintien pendant hangover

    return result


def estimate_num_speakers(embeddings, max_speakers=DEFAULT_MAX_SPEAKERS):
    """Estime le nombre optimal de locuteurs via Eigen-gap et Silhouette Score.

    Méthode :
    1. Si peu d'embeddings (< 4), retourne 1
    2. Calcule la matrice d'affinité RBF
    3. Extrait les eigenvalues du Laplacien normalisé
    4. Eigen-gap : argmax(λ_i - λ_{i+1}) + 1
    5. Validation par Silhouette Score si suffisamment d'échantillons

    Args:
        embeddings: Array numpy d'embeddings (N × D).
        max_speakers: Nombre maximum de locuteurs autorisé.

    Returns:
        Nombre optimal de clusters (entre 1 et max_speakers).
    """
    n = len(embeddings)
    if n < DEFAULT_MIN_CLUSTER_EMBEDDINGS:
        return 1

    max_k = min(max_speakers, n // 2)
    if max_k < 2:
        return 1

    try:
        # Calcul de la matrice d'affinité via noyau RBF
        from sklearn.metrics.pairwise import rbf_kernel
        gamma = 1.0 / embeddings.shape[1]  # 1/D
        affinity = rbf_kernel(embeddings, gamma=gamma)

        # Laplacien normalisé
        degree = np.diag(affinity.sum(axis=1))
        d_inv_sqrt = np.diag(1.0 / np.sqrt(np.maximum(affinity.sum(axis=1), 1e-10)))
        laplacian = np.eye(n) - d_inv_sqrt @ affinity @ d_inv_sqrt

        # Eigenvalues
        eigenvalues = np.sort(np.real(np.linalg.eigvalsh(laplacian)))

        # Eigen-gap : chercher le plus grand saut entre eigenvalues consécutives
        # On ne considère que les max_k premières valeurs propres
        gaps = np.diff(eigenvalues[:max_k + 1])
        if len(gaps) > 0:
            n_clusters_eigengap = int(np.argmax(gaps)) + 1
        else:
            n_clusters_eigengap = 1

        # Clamp
        n_clusters_eigengap = max(1, min(n_clusters_eigengap, max_k))

        # Validation par Silhouette Score si assez d'échantillons
        if n >= 10 and n_clusters_eigengap >= 2:
            best_score = -1.0
            best_k = n_clusters_eigengap

            for k in range(max(2, n_clusters_eigengap - 1), min(max_k + 1, n_clusters_eigengap + 2)):
                try:
                    clustering = SpectralClustering(
                        n_clusters=k,
                        affinity='nearest_neighbors',
                        assign_labels='kmeans',
                        random_state=42,
                        n_neighbors=min(10, n - 1)
                    )
                    labels = clustering.fit_predict(embeddings)
                    if len(set(labels)) >= 2:
                        score = silhouette_score(embeddings, labels)
                        if score > best_score:
                            best_score = score
                            best_k = k
                except Exception:
                    continue

            return best_k

        return n_clusters_eigengap

    except Exception as e:
        logging.warning(f"Estimation du nombre de locuteurs échouée: {e}. Fallback n=1.")
        return 1


def run_vad_and_embedding(wav_path, extractor_model_path=None,
                          vad_threshold=DEFAULT_VAD_THRESHOLD,
                          hop_overlap=DEFAULT_HOP_OVERLAP,
                          median_filter_size=DEFAULT_MEDIAN_FILTER_SIZE,
                          hangover_sec=DEFAULT_HANGOVER_SEC, video_name=""):
    """
    Exécute le VAD via YAMNet (Edge TPU) avec fenêtrage glissant et FSM hangover.

    Pipeline algorithmique (Audit Camille) :
    1. Fenêtrage glissant avec overlap configurable (défaut 50%, hop=0.48s)
    2. Inférence YAMNet INT8 par fenêtre
    3. Filtre Médian sur les probabilités de parole brutes
    4. Seuil VAD calibré (0.20 pour compenser la quantification INT8)
    5. Machine à États FSM avec Hangover (1.0s) pour combler les micro-silences

    Args:
        wav_path: Chemin du fichier WAV (16kHz mono).
        yamnet_interpreter: Interpréteur TFLite Edge TPU pour YAMNet.
        extractor_interpreter: Interpréteur optionnel pour l'extraction de d-vectors.
        vad_threshold: Seuil d'activation de la parole (défaut 0.20).
        hop_overlap: Taux de recouvrement (0.5 = 50%, 0.75 = 75%).
        median_filter_size: Taille du filtre médian sur les probabilités.
        hangover_sec: Durée du hangover FSM (en secondes).

    Returns:
        Tuple (speech_segments, embeddings_array) :
        - speech_segments : Liste de paires [start_sec, end_sec]
        - embeddings_array : Array numpy des d-vectors correspondants
    """
    global _tpu_lock, _yamnet_interp
    yamnet_interpreter = _yamnet_interp

    sample_rate, data = wavfile.read(wav_path)

    # YAMNet attend des segments de 0.96s (15360 samples à 16kHz)
    segment_size = 15360
    total_samples = len(data)

    # Hop size basé sur l'overlap
    hop_size = int(segment_size * (1.0 - hop_overlap))
    hop_sec = hop_size / sample_rate

    input_details = yamnet_interpreter.get_input_details()[0]
    output_details = yamnet_interpreter.get_output_details()

    # --- Étape 1 & 2 : Fenêtrage glissant + Inférence ---
    raw_probabilities = []
    raw_embeddings = []
    window_starts = []  # Positions de départ en samples

    for start in range(0, total_samples - segment_size + 1, hop_size):
        end = start + segment_size
        segment = data[start:end]

        # Préparation de l'entrée selon le type attendu par le modèle
        if input_details['dtype'] == np.int16:
            input_data = segment.reshape(input_details['shape'])
        elif input_details['dtype'] in (np.int8, np.uint8):
            segment_float = segment.astype(np.float32) / 32768.0
            scale, zero_point = input_details['quantization']
            input_data = np.round(segment_float / scale + zero_point).astype(input_details['dtype'])
        else:
            # Float fallback
            segment_float = segment.astype(np.float32) / 32768.0
            input_data = segment_float.reshape(input_details['shape'])

        yamnet_interpreter.set_tensor(input_details['index'], input_data)
        if _tpu_lock is not None:
            with _tpu_lock:
                yamnet_interpreter.invoke()
        else:
            yamnet_interpreter.invoke()

        # Scores de classification (Speech = index 0)
        scores_tensor = yamnet_interpreter.get_tensor(output_details[0]['index'])
        if output_details[0]['dtype'] in (np.int8, np.uint8):
            scale_out, zero_point_out = output_details[0]['quantization']
            scores = (scores_tensor.astype(np.float32) - zero_point_out) * scale_out
        else:
            scores = scores_tensor

        speech_prob = float(scores[0][0])
        raw_probabilities.append(speech_prob)
        window_starts.append(start)

        # Extraction du d-vector pour chaque fenêtre (seulement pour fallback YAMNet)
        if not extractor_model_path:
            # Fallback : embeddings YAMNet (1024D, généralistes)
            try:
                embeddings_tensor = yamnet_interpreter.get_tensor(output_details[2]['index'])
                if output_details[2]['dtype'] in (np.int8, np.uint8):
                    scale_emb, zero_point_emb = output_details[2]['quantization']
                    d_vector = (embeddings_tensor.astype(np.float32) - zero_point_emb) * scale_emb
                else:
                    d_vector = embeddings_tensor
                raw_embeddings.append(d_vector[0])
            except Exception as e:
                logging.warning(f"Impossible de lire l'embedding YAMNet: {e}")
                raw_embeddings.append(np.random.randn(128))

    # Traiter le dernier segment si des échantillons restent
    remaining = total_samples - (window_starts[-1] + segment_size) if window_starts else total_samples
    if remaining > segment_size // 4 and total_samples >= segment_size:
        start = total_samples - segment_size
        segment = data[start:start + segment_size]

        if input_details['dtype'] == np.int16:
            input_data = segment.reshape(input_details['shape'])
        elif input_details['dtype'] in (np.int8, np.uint8):
            segment_float = segment.astype(np.float32) / 32768.0
            scale, zero_point = input_details['quantization']
            input_data = np.round(segment_float / scale + zero_point).astype(input_details['dtype'])
        else:
            segment_float = segment.astype(np.float32) / 32768.0
            input_data = segment_float.reshape(input_details['shape'])

        yamnet_interpreter.set_tensor(input_details['index'], input_data)
        if _tpu_lock is not None:
            with _tpu_lock:
                yamnet_interpreter.invoke()
        else:
            yamnet_interpreter.invoke()

        scores_tensor = yamnet_interpreter.get_tensor(output_details[0]['index'])
        if output_details[0]['dtype'] in (np.int8, np.uint8):
            scale_out, zero_point_out = output_details[0]['quantization']
            scores = (scores_tensor.astype(np.float32) - zero_point_out) * scale_out
        else:
            scores = scores_tensor

        raw_probabilities.append(float(scores[0][0]))
        window_starts.append(start)

        if not extractor_model_path:
            try:
                embeddings_tensor = yamnet_interpreter.get_tensor(output_details[2]['index'])
                if output_details[2]['dtype'] in (np.int8, np.uint8):
                    scale_emb, zero_point_emb = output_details[2]['quantization']
                    d_vector = (embeddings_tensor.astype(np.float32) - zero_point_emb) * scale_emb
                else:
                    d_vector = embeddings_tensor
                raw_embeddings.append(d_vector[0])
            except Exception:
                raw_embeddings.append(np.random.randn(128))

    if not raw_probabilities:
        return [], np.array([])

    # --- Étape 3 : Filtre Médian sur les probabilités ---
    probs_array = np.array(raw_probabilities, dtype=np.float32)
    filtered_probs = apply_median_filter_vad(probs_array, kernel_size=median_filter_size)

    # --- Étape 4 : Seuil VAD calibré ---
    vad_flags = [bool(p > vad_threshold) for p in filtered_probs]

    # --- Étape 5 : FSM Hangover ---
    vad_flags_fsm = apply_fsm_hangover(vad_flags, hop_sec=hop_sec, hangover_sec=hangover_sec)

    # --- Construction des segments de parole et des embeddings correspondants ---
    speech_segments = []
    speech_embeddings = []

    speech_indices = [i for i, is_speech in enumerate(vad_flags_fsm) if is_speech]
    for idx in speech_indices:
        start_sec = window_starts[idx] / sample_rate
        end_sec = (window_starts[idx] + segment_size) / sample_rate
        speech_segments.append([start_sec, end_sec])

    # Collecter les embeddings des fenêtres de parole
    if extractor_model_path and Path(extractor_model_path).exists() and speech_indices:
        model_str = str(extractor_model_path)
        # Try to use ONNX if it exists alongside TFLite
        onnx_path = model_str.replace(".tflite", ".onnx")
        if HAS_ONNX and os.path.exists(onnx_path):
            model_to_load = onnx_path
            logging.info(f"ECAPA-TDNN: Utilisation du moteur ONNX Runtime (Dynamic Batching) via {onnx_path}")
        else:
            model_to_load = model_str
            logging.info(f"ECAPA-TDNN: Utilisation du moteur TFLite Float32 (Batch 1) via {model_to_load}")
            
        logging.info(f"ECAPA-TDNN: extraction de {len(speech_indices)} d-vectors 192D...")
        
        extractor_model = get_extractor_model_cached(model_to_load)
        total_speech = len(speech_indices)
        
        BATCH_SIZE = 32
        
        for batch_start in range(0, total_speech, BATCH_SIZE):
            batch_indices = speech_indices[batch_start:batch_start+BATCH_SIZE]
            
            waveforms = []
            for idx in batch_indices:
                center_sample = window_starts[idx] + (segment_size // 2)
                waveform_3s = _extract_3s_segment(data, sample_rate, center_sample)
                waveforms.append(waveform_3s)
            
            # Inférence groupée
            d_vecs = extract_ecapa_embedding_batch(waveforms, extractor_model)
            for d_vec in d_vecs:
                speech_embeddings.append(d_vec)
            
            current_count = min(batch_start + BATCH_SIZE, total_speech)
            if current_count % 32 == 0 or current_count == total_speech:
                progress_percent = int(current_count / total_speech * 100)
                vid_log = f" - {video_name}" if video_name else ""
                logging.info(f"ECAPA_PROGRESS: {current_count}/{total_speech} embeddings ({progress_percent}%){vid_log}")
            
        logging.info(f"ECAPA-TDNN: extraction terminée ({len(speech_embeddings)} embeddings)")
    elif speech_indices:
        # Fallback YAMNet : collecter directement les embeddings pré-calculés
        for idx in speech_indices:
            speech_embeddings.append(raw_embeddings[idx])

    return speech_segments, np.array(speech_embeddings) if speech_embeddings else np.array([])


def _compute_actual_durations(labels, segments):
    """Computes actual contiguous duration for each speaker cluster by merging overlapping segments."""
    cluster_segments = {}
    for label, seg in zip(labels, segments):
        if label not in cluster_segments:
            cluster_segments[label] = []
        cluster_segments[label].append(seg)
        
    durations = {}
    for label, segs in cluster_segments.items():
        segs = sorted(segs, key=lambda x: x[0])
        merged = []
        current_start = segs[0][0]
        current_end = segs[0][1]
        for i in range(1, len(segs)):
            if segs[i][0] - current_end < 1.0:
                current_end = max(current_end, segs[i][1])
            else:
                merged.append((current_start, current_end))
                current_start = segs[i][0]
                current_end = segs[i][1]
        merged.append((current_start, current_end))
        durations[label] = sum(end - start for start, end in merged)
    return durations


def perform_clustering(embeddings, segments, max_speakers=DEFAULT_MAX_SPEAKERS):
    """
    Clustering par Agglomération Hiérarchique (AHC) avec normalisation L2
    et post-traitement de réassignation des locuteurs mineurs (silence/bruit).

    Args:
        embeddings: Array numpy d'embeddings (N × D).
        segments: Liste de paires [start_sec, end_sec].
        max_speakers: Non utilisé pour AHC avec seuil, conservé pour signature.

    Returns:
        Liste de dicts {"speaker": str, "start": float, "end": float}.
    """
    if len(embeddings) == 0:
        return []

    if len(embeddings) == 1:
        return [{"speaker": "SPEAKER_00", "start": segments[0][0], "end": segments[0][1]}]

    # 1. Normalisation L2
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norm_embeddings = np.where(norms > 1e-10, embeddings / norms, embeddings)

    # 2. Clustering AHC avec distance cosine et seuil adaptatif
    clustering = AgglomerativeClustering(
        n_clusters=None,
        metric='cosine',
        linkage='average',
        distance_threshold=DEFAULT_CLUSTERING_THRESHOLD
    )
    labels = clustering.fit_predict(norm_embeddings)

    # 3. Calcul des durées réelles contiguës de parole par locuteur
    cluster_durations = _compute_actual_durations(labels, segments)

    # 4. Identification des locuteurs majeurs (durée >= 7.0 secondes)
    major_clusters = [c for c, dur in cluster_durations.items() if dur >= DEFAULT_MIN_SPEAKER_SPEECH_DURATION]
    
    if not major_clusters:
        # Fallback : garder le locuteur ayant le plus grand temps de parole
        major_clusters = [max(cluster_durations.keys(), key=lambda k: cluster_durations[k])]

    # 5. Réassigner les locuteurs mineurs au locuteur majeur le plus proche
    if len(major_clusters) < len(cluster_durations):
        logging.info(f"Clustering AHC: Réassignation de {len(cluster_durations) - len(major_clusters)} locuteurs mineurs...")
        
        # Calcule les vecteurs moyens (centroïdes) pour chaque locuteur majeur
        major_means = {}
        for c in major_clusters:
            major_means[c] = np.mean(norm_embeddings[labels == c], axis=0)
            norm_val = np.linalg.norm(major_means[c])
            if norm_val > 1e-10:
                major_means[c] /= norm_val

        new_labels = labels.copy()
        for i, label in enumerate(labels):
            if label not in major_clusters:
                emb = norm_embeddings[i]
                best_c = None
                best_sim = -1.0
                for c in major_clusters:
                    sim = np.dot(emb, major_means[c])
                    if sim > best_sim:
                        best_sim = sim
                        best_c = c
                new_labels[i] = best_c
        labels = new_labels

    # Recalculer les durées finales après réassignation
    final_durations = _compute_actual_durations(labels, segments)

    # 6. Tri et mapping des étiquettes (SPEAKER_00, SPEAKER_01...) par ordre décroissant d'activité
    unique_labels = sorted(list(set(labels)))
    sorted_labels = sorted(unique_labels, key=lambda l: final_durations.get(l, 0.0), reverse=True)
    label_map = {l: f"SPEAKER_{i:02d}" for i, l in enumerate(sorted_labels)}

    # 7. Fusion des segments adjacents
    results = []
    current_speaker = label_map[labels[0]]
    current_start = segments[0][0]
    current_end = segments[0][1]

    for i in range(1, len(segments)):
        speaker = label_map[labels[i]]
        if speaker == current_speaker and segments[i][0] - current_end < 1.0:
            current_end = segments[i][1]
        else:
            results.append({
                "speaker": current_speaker,
                "start": current_start,
                "end": current_end
            })
            current_speaker = speaker
            current_start = segments[i][0]
            current_end = segments[i][1]

    results.append({
        "speaker": current_speaker,
        "start": current_start,
        "end": current_end
    })

    return results


def _compute_speaker_stats(diarization_result, duration_sec):
    """Calcule les statistiques par locuteur pour la section speaker_stats.

    Args:
        diarization_result: Liste de dicts avec 'speaker', 'start', 'end'.
        duration_sec: Durée totale de la vidéo en secondes.

    Returns:
        Dict {speaker_label: {"total_time_sec": float, "percentage": float}}.
    """
    if not diarization_result or duration_sec <= 0:
        return {}

    speaker_times = {}
    for item in diarization_result:
        speaker = item["speaker"]
        segment_duration = item["end"] - item["start"]
        speaker_times[speaker] = speaker_times.get(speaker, 0.0) + segment_duration

    total_speech = sum(speaker_times.values())
    stats = {}
    for speaker in sorted(speaker_times.keys()):
        time_sec = round(speaker_times[speaker], 3)
        percentage = round((speaker_times[speaker] / total_speech) * 100, 1) if total_speech > 0 else 0.0
        stats[speaker] = {
            "total_time_sec": time_sec,
            "percentage": percentage
        }

    return stats


def _write_audio_json_file(output_json, video_path, diarization_result, duration_sec, temp_wav, fps=25.0):
    """Écrit le fichier JSON de sortie au format compatible STEP5/STEP6.

    Inclut la section speaker_stats pour conformité structurelle totale.
    """
    if duration_sec <= 0 and temp_wav is not None:
        # Fallback sur la durée de l'audio si ffprobe échoue
        try:
            sample_rate, wav_data = wavfile.read(temp_wav)
            duration_sec = len(wav_data) / sample_rate
        except Exception:
            duration_sec = -1.0

    total_frames = int(round(duration_sec * fps)) if duration_sec > 0 else -1

    # Alignement des segments de diarisation sur la timeline des frames (25 fps)
    audio_timeline = {}
    max_frame_seen = 0
    for item in diarization_result:
        start_sec = item["start"]
        end_sec = item["end"]
        speaker_label = item["speaker"]

        start_frame = max(1, int(start_sec * fps))
        end_frame = int(end_sec * fps)
        if end_frame < start_frame:
            continue
        max_frame_seen = max(max_frame_seen, end_frame)
        for frame_num in range(start_frame, end_frame + 1):
            frame_entry = audio_timeline.get(frame_num)
            if frame_entry is None:
                frame_entry = set()
                audio_timeline[frame_num] = frame_entry
            frame_entry.add(speaker_label)

    if total_frames < 0:
        total_frames = max_frame_seen
    total_frames = max(1, total_frames)

    # Calcul des speaker_stats
    speaker_stats = _compute_speaker_stats(diarization_result, duration_sec)

    # Écriture JSON streaming (schéma identique à run_audio_analysis.py + speaker_stats)
    with open(output_json, 'w', encoding='utf-8') as f:
        f.write("{\n")
        f.write(f"  \"video_filename\": \"{video_path.name}\",\n")
        f.write(f"  \"total_frames\": {total_frames},\n")
        f.write(f"  \"fps\": {round(fps, 2)},\n")

        # Section speaker_stats (Audit Camille : conformité structurelle)
        if speaker_stats:
            f.write(f"  \"speaker_stats\": {json.dumps(speaker_stats, ensure_ascii=False)},\n")

        f.write("  \"frames_analysis\": [\n")

        frames_processed = 0
        for frame_num in range(1, total_frames + 1):
            speakers = sorted(audio_timeline.get(frame_num, []))
            is_speech = len(speakers) > 0
            timecode = round((frame_num - 1) / fps, 3)
            obj = {
                "frame": frame_num,
                "audio_info": {
                    "is_speech_present": is_speech,
                    "num_distinct_speakers_audio": len(speakers),
                    "active_speaker_labels": speakers,
                    "timecode_sec": timecode,
                },
            }
            if frame_num > 1:
                f.write(",\n")
            f.write("    " + json.dumps(obj))

            frames_processed += 1
            if frames_processed % 500 == 0 or frames_processed == total_frames:
                progress_percent = int((frames_processed / total_frames) * 100) if total_frames else 100
                logging.info(f"INTERNAL_PROGRESS: {frames_processed}/{total_frames} frames ({progress_percent}%) - {video_path.name}")

        f.write("\n  ]\n")
        f.write("}\n")


def worker_process_video(video_path, cfg, extractor_model_path):
    try:
        logging.info(f"PROCESSING_VIDEO: {video_path.name}")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_wav = Path(temp_dir) / "audio.wav"
            extract_audio(video_path, temp_wav)

            # 1. VAD et Extraction (TPU) avec fenêtrage glissant + FSM
            segments, embeddings = run_vad_and_embedding(
                temp_wav, 
                extractor_model_path=extractor_model_path,
                vad_threshold=cfg['vad_threshold'],
                hop_overlap=cfg['hop_overlap'],
                median_filter_size=cfg['median_filter_size'],
                hangover_sec=cfg['hangover_sec'],
                video_name=video_path.name
            )

            logging.info(f"VAD: {len(segments)} segments de parole détectés")

            # 2. Spectral Clustering adaptatif (CPU)
            diarization_result = perform_clustering(
                embeddings, segments,
                max_speakers=cfg['max_speakers']
            )

            # Sauvegarde JSON au format original compatible STEP5/6 + speaker_stats
            output_json = video_path.with_name(f"{video_path.stem}_audio.json")
            duration_sec = _run_ffprobe_duration(video_path)
            _write_audio_json_file(output_json, video_path, diarization_result, duration_sec, temp_wav)

            logging.info(f"Succès: {output_json.name} créé.")
            return True
    except Exception as e:
        logging.exception(f"Échec de l'analyse audio pour {video_path.name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log_dir", type=str, default="logs/step4", help="Dossier de logs")
    parser.add_argument("--config", type=str, help="Fichier de configuration JSON")
    args = parser.parse_args()

    # Paramètres par défaut (Audit Camille)
    vad_threshold = DEFAULT_VAD_THRESHOLD
    hop_overlap = DEFAULT_HOP_OVERLAP
    median_filter_size = DEFAULT_MEDIAN_FILTER_SIZE
    hangover_sec = DEFAULT_HANGOVER_SEC
    max_speakers = DEFAULT_MAX_SPEAKERS

    if args.config and Path(args.config).exists():
        with open(args.config, 'r') as f:
            cfg = json.load(f)
            vad_threshold = cfg.get("vad_threshold", vad_threshold)
            hop_overlap = cfg.get("hop_overlap", hop_overlap)
            median_filter_size = cfg.get("median_filter_size", median_filter_size)
            hangover_sec = cfg.get("hangover_sec", hangover_sec)
            max_speakers = cfg.get("max_speakers", max_speakers)

    # Configuration du Logger avec fichier log
    log_dir = Path(args.log_dir)
    if not log_dir.is_absolute():
        log_dir = (BASE_DIR / log_dir).resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"tpu_audio_diarization_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # Réinitialisation de la config root log
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.info("--- Démarrage de l'analyse Audio TPU (YAMNet INT8 - Audit Camille) ---")
    logging.info(
        f"CONFIG: vad_threshold={vad_threshold}, hop_overlap={hop_overlap}, "
        f"median_filter={median_filter_size}, hangover_sec={hangover_sec}, "
        f"max_speakers={max_speakers}"
    )

    assets_dir = BASE_DIR / "assets"
    yamnet_model = assets_dir / "yamnet_audio_classificator_quantized_edgetpu.tflite"
    # ECAPA-TDNN : modèle Float32 exécuté sur CPU (XNNPACK) — évite la perte de précision INT8
    extractor_model = assets_dir / "ecapa_tdnn_speaker_float.tflite"

    download_model(YAMNET_URL, yamnet_model)

    global _yamnet_interp
    try:
        import tflite_runtime.interpreter as tflite
        delegate = tflite.load_delegate('libedgetpu.so.1')
        _yamnet_interp = tflite.Interpreter(model_path=str(yamnet_model), experimental_delegates=[delegate])
        _yamnet_interp.resize_tensor_input(0, [15360])
        _yamnet_interp.allocate_tensors()
        logging.info("Modèle YAMNet Edge TPU chargé dans le processus principal.")
    except Exception as e:
        logging.critical(f"Erreur Edge TPU: {e}")
        sys.exit(1)

    videos = [p for ext in VIDEO_EXTENSIONS for p in WORK_DIR.rglob(f'*{ext}') if not p.with_name(f"{p.stem}_audio.json").exists()]
    total_videos = len(videos)
    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")

    if total_videos == 0:
        return

    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == "STEP4_MAX_WORKERS":
                        os.environ["STEP4_MAX_WORKERS"] = v.strip()
                        break

    step4_workers_str = os.environ.get("STEP4_MAX_WORKERS", "")
    if step4_workers_str.isdigit():
        max_workers = int(step4_workers_str)
    else:
        max_workers = max(1, multiprocessing.cpu_count() // 2)
    logging.info(f"Utilisation de {max_workers} threads (ThreadPoolExecutor) pour l'analyse inter-vidéos.")

    cfg = {
        'vad_threshold': vad_threshold,
        'hop_overlap': hop_overlap,
        'median_filter_size': median_filter_size,
        'hangover_sec': hangover_sec,
        'max_speakers': max_speakers
    }

    successful_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(worker_process_video, vp, cfg, extractor_model): vp for vp in videos}
        for future in as_completed(futures):
            if future.result():
                successful_count += 1

    logging.info(f"--- Analyse terminée. {successful_count}/{total_videos} réussie(s). ---")


if __name__ == "__main__":
    main()
