#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Worker de tracking vidéo pour OpenCV 5.0 DNN (STEP 5)

Ce module fournit le worker de traitement vidéo exploitant :
  - Accélération HAL et KleidiCV (AArch64) ou AVX2/AVX-512 (x86)
  - Chargement des modèles BlazeFace/FaceMesh en FP16 natif
    pour maximiser le débit vectoriel SIMD sur CPU
  - cv2.setNumThreads(1) obligatoire pour éviter la contention

Usage :
  Ce module est importé par run_tracking_cv5.py et ne doit pas être
  exécuté directement. Il est conçu pour être utilisé dans un
  processus spawné (pas de fork).
"""

import os
import sys
import logging
import numpy as np
import cv2
from pathlib import Path

# --- Configuration ---
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
ONNX_MODELS_DIR = BASE_DIR / "assets" / "models" / "onnx"


def init_worker():
    """Initialisation du worker : throttle threads OpenCV.

    CRITICAL: Doit être appelé au début de chaque processus spawné
    pour éviter l'oversubscription quand plusieurs workers tournent
    en parallèle avec TFLite et OpenCV.
    """
    cv2.setNumThreads(1)
    logging.info(
        f"Worker PID={os.getpid()} initialisé. "
        f"OpenCV {cv2.__version__}, threads={cv2.getNumThreads()}"
    )


def load_model_fp16(model_name):
    """Charge un modèle ONNX avec hint FP16 pour le dispatching SIMD, avec fallback ONNX Runtime."""
    model_path = ONNX_MODELS_DIR / model_name
    if not model_path.exists():
        logging.warning(f"Modèle ONNX manquant pour FP16: {model_path}")
        return None

    # 1. Tentative avec OpenCV DNN (uniquement si le moteur OpenCV 5.0 ENGINE_NEW est disponible)
    if hasattr(cv2.dnn, 'ENGINE_NEW'):
        try:
            net = cv2.dnn.readNetFromONNX(str(model_path))
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

            try:
                net.setEngineType(cv2.dnn.ENGINE_NEW)
            except Exception:
                pass

            # Activer le mode FP16 si supporté par le backend
            if hasattr(cv2.dnn, 'DNN_TARGET_CPU_FP16'):
                try:
                    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU_FP16)
                    logging.info(f"Modèle {model_name} chargé en FP16 natif (SIMD vectorisé)")
                except Exception:
                    logging.info(f"FP16 non supporté pour {model_name}, fallback FP32")

            logging.info(f"Modèle chargé avec OpenCV 5.0 DNN: {model_name} (worker PID={os.getpid()})")
            return net

        except Exception as dnn_err:
            logging.warning(f"Échec de chargement de {model_name} en FP16 avec OpenCV DNN ({dnn_err}). Passage au fallback ONNX Runtime...")
    else:
        logging.info(f"Moteur OpenCV 5.0 (ENGINE_NEW) non disponible. Utilisation directe du fallback ONNX Runtime pour {model_name} (worker PID={os.getpid()})...")

    # 2. Fallback ONNX Runtime
    try:
        class ORTDNNNet:
            """Wrapper imitant l'API cv2.dnn.Net pour un remplacement transparent par ONNX Runtime."""
            def __init__(self, path):
                import onnxruntime as ort
                opts = ort.SessionOptions()
                # Limiter le multi-threading pour éviter la contention CPU
                opts.intra_op_num_threads = 1
                opts.inter_op_num_threads = 1
                opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
                self.session = ort.InferenceSession(str(path), sess_options=opts, providers=['CPUExecutionProvider'])
                self.input_name = self.session.get_inputs()[0].name
                self.output_names = [o.name for o in self.session.get_outputs()]
                self.inputs = {}

            def setInput(self, blob, name=""):
                # Détecter si le modèle attend NHWC et que le blob fourni est NCHW
                # Les inputs d'ONNX Runtime convertis de TFLite attendent [1, H, W, 3]
                input_spec = self.session.get_inputs()[0]
                expected_shape = input_spec.shape
                
                # S'assurer que le blob est un tableau numpy
                blob = np.asarray(blob)
                
                if len(blob.shape) == 4 and len(expected_shape) == 4:
                    # Si le blob est NCHW [B, 3, H, W] mais le modèle attend NHWC [B, H, W, 3]
                    if blob.shape[1] == 3 and expected_shape[3] == 3:
                        blob = np.transpose(blob, (0, 2, 3, 1)).copy()
                    # Si le blob est NCHW [B, 1, H, W] mais le modèle attend NHWC [B, H, W, 1]
                    elif blob.shape[1] == 1 and expected_shape[3] == 1:
                        blob = np.transpose(blob, (0, 2, 3, 1)).copy()
                
                self.inputs[name or self.input_name] = blob

            def forward(self, outputNameOrList=None):
                if outputNameOrList:
                    if isinstance(outputNameOrList, str):
                        outputs = self.session.run([outputNameOrList], self.inputs)
                        return outputs[0]
                    else:
                        return self.session.run(list(outputNameOrList), self.inputs)
                else:
                    outputs = self.session.run(self.output_names, self.inputs)
                    return outputs[0]

            def getUnconnectedOutLayersNames(self):
                return self.output_names

        net = ORTDNNNet(model_path)
        logging.info(f"Modèle {model_name} chargé via ONNX Runtime (fallback, worker PID={os.getpid()})")
        return net
    except Exception as ort_err:
        logging.error(f"Erreur fatale : Impossible de charger {model_name} en FP16 via OpenCV DNN ou ONNX Runtime. Erreur ORT: {ort_err}")
        return None


def preprocess_blazeface(image, target_size=(128, 128)):
    """Prépare une image pour l'inférence BlazeFace.

    Utilise cv2.dnn.blobFromImage pour un preprocessing vectorisé
    (exploit HAL SIMD d'OpenCV 5.0).

    Args:
        image: frame RGB (H, W, 3) uint8
        target_size: (width, height) cible

    Returns:
        blob float32 prêt pour setInput
    """
    return cv2.dnn.blobFromImage(
        image,
        scalefactor=1.0 / 127.5,
        size=target_size,
        mean=(127.5, 127.5, 127.5),
        swapRB=False
    )


def preprocess_facemesh(image_crop, target_size=(192, 192)):
    """Prépare un crop de visage pour l'inférence FaceMesh.

    Args:
        image_crop: crop du visage RGB (H, W, 3) uint8
        target_size: (width, height) cible

    Returns:
        blob float32 prêt pour setInput
    """
    resized = cv2.resize(image_crop, target_size, interpolation=cv2.INTER_LINEAR)
    return cv2.dnn.blobFromImage(
        resized,
        scalefactor=1.0 / 127.5,
        size=target_size,
        mean=(127.5, 127.5, 127.5),
        swapRB=False
    )


def run_inference_blazeface(net, blob):
    """Exécute l'inférence BlazeFace et retourne les sorties brutes.

    Args:
        net: cv2.dnn.Net (BlazeFace ONNX)
        blob: blob preprocessé

    Returns:
        tuple (classificators, regressors) ou None en cas d'erreur
    """
    if net is None:
        return None

    try:
        net.setInput(blob)
        output_names = net.getUnconnectedOutLayersNames()
        outputs = net.forward(output_names)

        if len(outputs) < 2:
            return None

        # Identifier les tenseurs par leur forme en retirant la dimension batch si présente
        out0 = outputs[0][0] if len(outputs[0].shape) == 3 else outputs[0]
        out1 = outputs[1][0] if len(outputs[1].shape) == 3 else outputs[1]

        if out0.shape[-1] == 1:
            return out0.flatten(), out1
        else:
            return out1.flatten(), out0

    except Exception as e:
        logging.error(f"Erreur inférence BlazeFace: {e}")
        return None


def run_inference_facemesh(net, blob):
    """Exécute l'inférence FaceMesh et retourne les landmarks.

    Args:
        net: cv2.dnn.Net (FaceMesh ONNX)
        blob: blob preprocessé

    Returns:
        array (468, 3) ou None
    """
    if net is None:
        return None

    try:
        net.setInput(blob)
        output = net.forward()
        return output.reshape(-1, 3)

    except Exception as e:
        logging.error(f"Erreur inférence FaceMesh: {e}")
        return None


def get_opencv_build_info():
    """Retourne les informations de build OpenCV utiles pour le diagnostic.

    Permet de vérifier les flags HAL, SIMD, et FP16 au runtime.
    """
    info = {
        "version": cv2.__version__,
        "build_info_snippet": "",
    }

    build_info = cv2.getBuildInformation()

    # Extraire les lignes pertinentes
    relevant_keywords = ["CPU_DISPATCH", "HAL", "SIMD", "FP16", "AVX", "NEON", "KleidiCV"]
    lines = build_info.split('\n')
    relevant_lines = []
    for line in lines:
        for kw in relevant_keywords:
            if kw.lower() in line.lower():
                relevant_lines.append(line.strip())
                break

    info["build_info_snippet"] = "\n".join(relevant_lines[:20])
    return info


if __name__ == "__main__":
    # Diagnostic mode: affiche les capabilities OpenCV quand lancé directement
    print(f"OpenCV version: {cv2.__version__}")
    print(f"Threads: {cv2.getNumThreads()}")
    print(f"ONNX models dir: {ONNX_MODELS_DIR}")
    print(f"ONNX models found: {list(ONNX_MODELS_DIR.glob('*.onnx')) if ONNX_MODELS_DIR.exists() else 'N/A'}")
    print()

    build_info = get_opencv_build_info()
    print("Build info (relevant):")
    print(build_info["build_info_snippet"])
