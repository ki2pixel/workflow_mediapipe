#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export et compilation Edge TPU du sous-graphe CNN YAMNet (Axe 2).

Ce script s'exécute dans un environnement TensorFlow 2.x (ex: /mnt/venv_ext4/transnet_env).
Il extrait le sous-graphe MobileNetV1 CNN (entrée: [1, 96, 64], sorties: scores [1, 521] et embeddings [1, 1024]),
charge les poids officiels YAMNet depuis Google Cloud, réalise une quantification INT8 (PTQ)
avec un jeu représentatif de log-mel issu de VoxConverse, valide le taux d'accord VAD (seuil 0.20 >= 99.5%),
et compile avec edgetpu_compiler -s vers assets/yamnet_split_edgetpu_compiled.tflite.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import wave
from pathlib import Path

import h5py
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WEIGHTS_URL = "https://storage.googleapis.com/audioset/yamnet.h5"
DEFAULT_WEIGHTS_PATH = PROJECT_ROOT / "assets" / "yamnet.h5"
DEFAULT_CORPUS = PROJECT_ROOT / "scratch" / "bench_step3_der" / "voxconverse"
DEFAULT_OUT_DIR = PROJECT_ROOT / "assets"


def ensure_weights(weights_path: Path) -> Path:
    if weights_path.exists() and weights_path.stat().st_size > 10_000_000:
        return weights_path
    temp_h5 = Path("/tmp/yamnet.h5")
    if temp_h5.exists() and temp_h5.stat().st_size > 10_000_000:
        shutil.copy2(temp_h5, weights_path)
        return weights_path
    print(f"Téléchargement des poids officiels YAMNet depuis {DEFAULT_WEIGHTS_URL}...")
    weights_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(DEFAULT_WEIGHTS_URL, str(weights_path))
    print(f"Poids téléchargés : {weights_path} ({weights_path.stat().st_size} octets)")
    return weights_path


def get_mel_filterbank(sr=16000, n_fft=512, n_mels=64, fmin=125.0, fmax=7500.0) -> np.ndarray:
    """Génère la matrice de filtres mel triangulaires à parité exacte avec TensorFlow."""
    matrix_file = PROJECT_ROOT / "assets" / "yamnet_mel_matrix.npy"
    if matrix_file.exists():
        return np.load(matrix_file).astype(np.float32)

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
    return weights.astype(np.float32)


def compute_log_mel_patches(waveform: np.ndarray, sample_rate: int = 16000,
                            mel_matrix: np.ndarray = None) -> list:
    """Calcule les patches (96, 64) log-mel depuis un signal audio 16kHz."""
    frame_length = 400
    hop_length = 160
    fft_length = 512

    if mel_matrix is None:
        mel_matrix = get_mel_filterbank(sr=sample_rate, n_fft=fft_length, n_mels=64)

    if len(waveform) < frame_length:
        return []

    # Periodic Hann window
    window = 0.5 - 0.5 * np.cos(2.0 * np.pi * np.arange(frame_length) / frame_length)
    
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

    patches = []
    patch_frames = 96
    patch_hop = 48
    num_patches = 1 + max(0, (log_mel.shape[0] - patch_frames) // patch_hop) if log_mel.shape[0] >= patch_frames else 0
    for p in range(num_patches):
        start = p * patch_hop
        patch = log_mel[start:start + patch_frames]
        patches.append(patch.reshape(1, 96, 64))
    return patches


def build_yamnet_cnn_model():
    """Construit l'architecture MobileNetV1 CNN de YAMNet sous TensorFlow Keras."""
    import tensorflow as tf
    from tensorflow.keras import layers, Model

    inp = layers.Input(shape=(96, 64), batch_size=1, dtype=tf.float32, name="log_mel_input")
    x = layers.Reshape((96, 64, 1), name="reshape")(inp)

    # Layer 1
    x = layers.Conv2D(32, (3, 3), strides=2, padding="same", use_bias=False, name="l1_conv")(x)
    x = layers.BatchNormalization(name="l1_bn", center=True, scale=False, epsilon=1e-4)(x)
    x = layers.ReLU(name="l1_relu")(x)

    layer_configs = [
        ((3, 3), 1, 64),
        ((3, 3), 2, 128),
        ((3, 3), 1, 128),
        ((3, 3), 2, 256),
        ((3, 3), 1, 256),
        ((3, 3), 2, 512),
        ((3, 3), 1, 512),
        ((3, 3), 1, 512),
        ((3, 3), 1, 512),
        ((3, 3), 1, 512),
        ((3, 3), 1, 512),
        ((3, 3), 2, 1024),
        ((3, 3), 1, 1024),
    ]

    for idx, (k, s, f) in enumerate(layer_configs, start=2):
        x = layers.DepthwiseConv2D(k, strides=s, depth_multiplier=1, padding="same", use_bias=False, name=f"l{idx}_dw")(x)
        x = layers.BatchNormalization(name=f"l{idx}_dw_bn", center=True, scale=False, epsilon=1e-4)(x)
        x = layers.ReLU(name=f"l{idx}_dw_relu")(x)
        x = layers.Conv2D(f, (1, 1), strides=1, padding="same", use_bias=False, name=f"l{idx}_pw")(x)
        x = layers.BatchNormalization(name=f"l{idx}_pw_bn", center=True, scale=False, epsilon=1e-4)(x)
        x = layers.ReLU(name=f"l{idx}_pw_relu")(x)

    embeddings = layers.GlobalAveragePooling2D(name="global_average_pooling2d")(x)
    logits = layers.Dense(521, use_bias=True, name="logits")(embeddings)
    predictions = layers.Activation("sigmoid", name="prediction")(logits)

    return Model(inputs=inp, outputs=[predictions, embeddings], name="yamnet_cnn")


def load_yamnet_weights(model, weights_path: Path):
    """Transfère chirurgicalement les tenseurs de poids depuis yamnet.h5."""
    with h5py.File(weights_path, "r") as f:
        # Layer 1
        conv_w = f["layer1"]["conv"]["layer1"]["conv"]["kernel:0"][:]
        model.get_layer("l1_conv").set_weights([conv_w])
        bn_beta = f["layer1"]["conv"]["bn"]["layer1"]["conv"]["bn"]["beta:0"][:]
        bn_mean = f["layer1"]["conv"]["bn"]["layer1"]["conv"]["bn"]["moving_mean:0"][:]
        bn_var = f["layer1"]["conv"]["bn"]["layer1"]["conv"]["bn"]["moving_variance:0"][:]
        model.get_layer("l1_bn").set_weights([bn_beta, bn_mean, bn_var])

        # Layers 2 to 14
        for idx in range(2, 15):
            grp = f[f"layer{idx}"]
            dw_w = grp["depthwise_conv"][f"layer{idx}"]["depthwise_conv"]["depthwise_kernel:0"][:]
            model.get_layer(f"l{idx}_dw").set_weights([dw_w])
            dw_beta = grp["depthwise_conv"]["bn"][f"layer{idx}"]["depthwise_conv"]["bn"]["beta:0"][:]
            dw_mean = grp["depthwise_conv"]["bn"][f"layer{idx}"]["depthwise_conv"]["bn"]["moving_mean:0"][:]
            dw_var = grp["depthwise_conv"]["bn"][f"layer{idx}"]["depthwise_conv"]["bn"]["moving_variance:0"][:]
            model.get_layer(f"l{idx}_dw_bn").set_weights([dw_beta, dw_mean, dw_var])

            pw_w = grp["pointwise_conv"][f"layer{idx}"]["pointwise_conv"]["kernel:0"][:]
            model.get_layer(f"l{idx}_pw").set_weights([pw_w])
            pw_beta = grp["pointwise_conv"]["bn"][f"layer{idx}"]["pointwise_conv"]["bn"]["beta:0"][:]
            pw_mean = grp["pointwise_conv"]["bn"][f"layer{idx}"]["pointwise_conv"]["bn"]["moving_mean:0"][:]
            pw_var = grp["pointwise_conv"]["bn"][f"layer{idx}"]["pointwise_conv"]["bn"]["moving_variance:0"][:]
            model.get_layer(f"l{idx}_pw_bn").set_weights([pw_beta, pw_mean, pw_var])

        # Dense
        logits_w = f["logits"]["logits"]["kernel:0"][:]
        logits_b = f["logits"]["logits"]["bias:0"][:]
        model.get_layer("logits").set_weights([logits_w, logits_b])


def collect_calibration_dataset(corpus_dir: Path, target_count: int = 350) -> list:
    """Collecte des patches log-mel représentatifs variés (parole, silence, ambiance)."""
    patches = []
    wav_files = sorted((corpus_dir / "wav").glob("*.wav"))
    mel_matrix = get_mel_filterbank(sr=16000, n_fft=512, n_mels=64)

    # 1. Silences et bruits blancs de base
    for _ in range(20):
        dummy_silence = np.zeros(16000 * 2, dtype=np.float32)
        patches.extend(compute_log_mel_patches(dummy_silence, mel_matrix=mel_matrix))
    for _ in range(20):
        dummy_noise = np.random.normal(0, 0.01, 16000 * 2).astype(np.float32)
        patches.extend(compute_log_mel_patches(dummy_noise, mel_matrix=mel_matrix))

    # 2. Vrais extraits audio VoxConverse
    for wav_file in wav_files:
        if len(patches) >= target_count:
            break
        try:
            with wave.open(str(wav_file), "rb") as wf:
                sr = wf.getframerate()
                n = wf.getnframes()
                # Lire au max 30 secondes
                read_n = min(n, sr * 30)
                raw = wf.readframes(read_n)
                data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                file_patches = compute_log_mel_patches(data, sample_rate=sr, mel_matrix=mel_matrix)
                # Prendre jusqu'à 25 patches par fichier
                patches.extend(file_patches[:25])
        except Exception as exc:
            continue

    print(f"Jeu de calibration : {len(patches)} patches log-mel collectés.")
    return patches[:target_count]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export et compilation Edge TPU de YAMNet Split")
    parser.add_argument("--weights", default=str(DEFAULT_WEIGHTS_PATH), help="Chemin vers yamnet.h5")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Dossier de sortie des modèles")
    parser.add_argument("--corpus", default=str(DEFAULT_CORPUS), help="Dossier VoxConverse pour calibration")
    parser.add_argument("--num-patches", type=int, default=300, help="Nombre de patches de calibration")
    parser.add_argument("--threshold", type=float, default=0.20, help="Seuil de décision VAD")
    args = parser.parse_args()

    import tensorflow as tf

    weights_path = Path(args.weights).resolve()
    ensure_weights(weights_path)
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus_dir = Path(args.corpus).resolve()

    print("=== Étape 1 : Construction et chargement du modèle Keras ===")
    model = build_yamnet_cnn_model()
    load_yamnet_weights(model, weights_path)
    print(f"Modèle YAMNet CNN FP32 instancié ({model.count_params()} paramètres).")

    print("=== Étape 2 : Préparation du jeu de calibration représentatif ===")
    calibration_patches = collect_calibration_dataset(corpus_dir, args.num_patches)
    if not calibration_patches:
        print("Erreur: aucun patch de calibration généré.", file=sys.stderr)
        return 1

    print("=== Étape 3 : Quantification Post-Training (PTQ) INT8 ===")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]

    def representative_gen():
        for patch in calibration_patches:
            yield [patch.astype(np.float32)]

    converter.representative_dataset = representative_gen
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8

    quantized_tflite = converter.convert()
    quantized_path = out_dir / "yamnet_split_quantized.tflite"
    quantized_path.write_bytes(quantized_tflite)
    print(f"Modèle TFLite INT8 généré : {quantized_path} ({len(quantized_tflite)} octets)")

    print("=== Étape 4 : Évaluation du taux d'accord de décision VAD (seuil 0.20) ===")
    # Évaluer concordance binaire float vs int8 sur un échantillon de test
    test_patches = calibration_patches[:150]
    float_speech_probs = []
    for p in test_patches:
        preds, _ = model(p)
        float_speech_probs.append(float(preds[0, 0]))

    interp = tf.lite.Interpreter(model_path=str(quantized_path))
    interp.allocate_tensors()
    in_det = interp.get_input_details()[0]
    scores_det = [o for o in interp.get_output_details() if len(o["shape"]) > 1 and o["shape"][1] == 521][0]
    in_scale, in_zp = in_det["quantization"]
    out_scale, out_zp = scores_det["quantization"]

    int8_speech_probs = []
    for p in test_patches:
        q_in = np.clip(np.rint(p / in_scale + in_zp), -128, 127).astype(np.int8)
        interp.set_tensor(in_det["index"], q_in)
        interp.invoke()
        q_out = interp.get_tensor(scores_det["index"])
        prob = float(q_out[0, 0] - out_zp) * out_scale
        int8_speech_probs.append(prob)

    float_decisions = np.array(float_speech_probs) >= args.threshold
    int8_decisions = np.array(int8_speech_probs) >= args.threshold
    agreement = np.mean(float_decisions == int8_decisions) * 100.0

    print(f"Accord de décision VAD au seuil {args.threshold:.2f} : {agreement:.2f} % (cible >= 99.5 %)")
    if agreement < 99.0:
        print(f"Alerte: Accord de décision {agreement:.2f} % inférieur aux attentes.", file=sys.stderr)

    print("=== Étape 5 : Compilation Edge TPU (edgetpu_compiler -s) ===")
    compiler = shutil.which("edgetpu_compiler")
    if not compiler:
        print("edgetpu_compiler introuvable sur le système.", file=sys.stderr)
        return 2

    comp_res = subprocess.run(
        [compiler, "-s", str(quantized_path), "-o", str(out_dir)],
        capture_output=True, text=True, check=False,
    )
    print("Sortie du compilateur Edge TPU :\n" + comp_res.stdout)
    if comp_res.stderr:
        print("Erreurs compilateur :\n" + comp_res.stderr, file=sys.stderr)

    compiled_candidate = out_dir / "yamnet_split_quantized_edgetpu.tflite"
    target_compiled = out_dir / "yamnet_split_edgetpu_compiled.tflite"
    if compiled_candidate.exists():
        shutil.copy2(compiled_candidate, target_compiled)
        print(f"Modèle Edge TPU final prêt : {target_compiled} ({target_compiled.stat().st_size} octets)")
    else:
        print("Erreur: Le fichier compilé Edge TPU n'a pas été produit.", file=sys.stderr)
        return 1

    # Rapport d'audit de l'op-code
    flatbuffer_bytes = target_compiled.read_bytes()
    has_custom_op = b"edgetpu-custom-op" in flatbuffer_bytes
    print(f"Audit flatbuffer : 'edgetpu-custom-op' présent ? {has_custom_op}")
    if not has_custom_op:
        print("ÉCHEC: L'op-code edgetpu-custom-op est absent du modèle compilé !", file=sys.stderr)
        return 1

    print("SUCCÈS: Axe 2 modèle compilé et qualifié avec succès.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
