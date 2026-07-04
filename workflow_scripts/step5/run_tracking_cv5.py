#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'analyse du tracking (BlazeFace -> FaceMesh -> Blendshapes) avec OpenCV 5.0 DNN
Version Expérimentale - Étape 5 (Alternative au pipeline TPU/MediaPipe)

Ce script remplace le runtime TFLite/Edge TPU par le moteur DNN orienté graphe
d'OpenCV 5.0 pour l'inférence BlazeFace et FaceMesh via des modèles ONNX.

Architecture :
  - Multiprocessing via 'spawn' (pas de fork, évite les deadlocks Copy-on-Write)
  - cv2.setNumThreads(1) dans les workers pour éviter l'oversubscription
  - Dispatching HAL SIMD automatique (AVX2/AVX-512/NEON via KleidiCV)
  - Fallback TFLite si les modèles ONNX ne sont pas disponibles

Prérequis :
  - Les modèles ONNX (blazeface.onnx, facemesh.onnx) doivent être dans assets/models/onnx/
  - Le venv tracking_cv5_env doit être activé (opencv-python-headless>=5.0.0)

Activation : USE_OPENCV5_STEP5=true dans .env
"""

import os
import sys
import json
import argparse
import logging
import subprocess
import signal
import multiprocessing as mp
import numpy as np
import cv2
from pathlib import Path
from datetime import datetime
import time

try:
    import orjson
    _HAS_ORJSON = True
except ImportError:
    _HAS_ORJSON = False

# --- Configuration Globale ---
WORK_DIR = Path(os.getcwd())
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
BASE_DIR = SCRIPT_DIR.parent.parent
sys.path.append(str(BASE_DIR))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

try:
    from utils.tracking_optimizations import apply_tracking_and_management
    from utils.enhanced_speaking_detection import EnhancedSpeakingDetector
    from object_detector_registry import ObjectDetectorRegistry
except ImportError as e:
    logging.critical(f"ERREUR: Impossible d'importer les utilitaires. Vérifiez PYTHONPATH: {e}")
    sys.exit(1)

VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')

# --- ARKIT BLENDSHAPES ---
ARKIT_52_BLENDSHAPE_NAMES = [
    'eyeBlinkLeft', 'eyeLookDownLeft', 'eyeLookInLeft', 'eyeLookOutLeft', 'eyeLookUpLeft',
    'eyeSquintLeft', 'eyeWideLeft', 'eyeBlinkRight', 'eyeLookDownRight', 'eyeLookInRight',
    'eyeLookOutRight', 'eyeLookUpRight', 'eyeSquintRight', 'eyeWideRight', 'jawForward',
    'jawLeft', 'jawRight', 'jawOpen', 'mouthClose', 'mouthFunnel', 'mouthPucker',
    'mouthLeft', 'mouthRight', 'mouthSmileLeft', 'mouthSmileRight', 'mouthFrownLeft',
    'mouthFrownRight', 'mouthDimpleLeft', 'mouthDimpleRight', 'mouthStretchLeft',
    'mouthStretchRight', 'mouthRollLower', 'mouthRollUpper', 'mouthShrugLower',
    'mouthShrugUpper', 'mouthPressLeft', 'mouthPressRight', 'mouthLowerDownLeft',
    'mouthLowerDownRight', 'mouthUpperUpLeft', 'mouthUpperUpRight', 'browDownLeft',
    'browDownRight', 'browInnerUp', 'browOuterUpLeft', 'browOuterUpRight', 'cheekPuff',
    'cheekSquintLeft', 'cheekSquintRight', 'noseSneerLeft', 'noseSneerRight', 'tongueOut'
]

BLENDSHAPE_136_INDICES = [
    0, 1, 4, 5, 6, 7, 8, 10, 13, 14, 17, 21, 33, 37, 39, 40, 46, 52, 53, 54, 55,
    58, 61, 63, 65, 66, 67, 70, 78, 80, 81, 82, 84, 87, 88, 91, 93, 95, 103, 105,
    107, 109, 127, 132, 133, 136, 144, 145, 146, 148, 149, 150, 152, 153, 154, 155,
    157, 158, 159, 160, 161, 162, 163, 168, 172, 173, 176, 178, 181, 185, 191, 195,
    197, 234, 246, 249, 251, 263, 267, 269, 270, 276, 282, 283, 284, 285, 288, 291,
    293, 295, 296, 297, 300, 308, 310, 311, 312, 314, 317, 318, 321, 323, 324, 332,
    334, 336, 338, 356, 361, 362, 365, 373, 374, 375, 377, 378, 379, 380, 381, 382,
    384, 385, 386, 387, 388, 389, 390, 397, 398, 400, 402, 405, 409, 415, 454, 466
]

# --- Configuration du Logger ---
LOG_DIR = BASE_DIR / "logs" / "step5"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"tpu_tracking_cv5_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# ONNX model paths
ONNX_MODELS_DIR = BASE_DIR / "assets" / "models" / "onnx"


# =========================================================================
# Streaming JSON Output (copie depuis run_tracking_tpu.py)
# =========================================================================

class StreamingList:
    def __init__(self, file_obj):
        self.file_obj = file_obj
        self.is_first = True
        self.count = 0
        self.file_obj.write("[\n")

    def append(self, item):
        if not self.is_first:
            self.file_obj.write(",\n")
        else:
            self.file_obj.write("\n")
            self.is_first = False

        if _HAS_ORJSON:
            frame_json = orjson.dumps(item, option=orjson.OPT_NON_STR_KEYS).decode('utf-8')
        else:
            frame_json = json.dumps(item)

        self.file_obj.write("    " + frame_json)
        self.count += 1
        self.file_obj.flush()

    def __len__(self):
        return self.count


class StreamingJSONOutput:
    def __init__(self, output_path, metadata):
        self.output_path = output_path
        self.file_obj = open(self.output_path, 'w', encoding='utf-8')
        self.file_obj.write("{\n  \"metadata\": ")
        json.dump(metadata, self.file_obj, indent=2, ensure_ascii=False)
        self.file_obj.write(",\n  \"frames\": ")
        self.frames_list = StreamingList(self.file_obj)

    def __getitem__(self, key):
        if key == "frames":
            return self.frames_list
        raise KeyError(key)

    def add_frame(self, frame_dict):
        self.frames_list.append(frame_dict)

    def close(self):
        self.file_obj.write("\n  ]\n}")
        self.file_obj.close()


class StreamingNDJSONOutput:
    """Sérialisation streaming NDJSON (JSON Lines), empreinte mémoire O(1)."""
    def __init__(self, output_path, metadata):
        self.output_path = output_path
        self.file_obj = open(self.output_path, 'wb' if _HAS_ORJSON else 'w', encoding=None if _HAS_ORJSON else 'utf-8')
        self._write_line(metadata)
        self.count = 0

    def _write_line(self, obj):
        if _HAS_ORJSON:
            self.file_obj.write(orjson.dumps(obj, option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_APPEND_NEWLINE))
        else:
            self.file_obj.write(json.dumps(obj, ensure_ascii=False) + '\n')

    def add_frame(self, frame_dict):
        self._write_line(frame_dict)
        self.count += 1
        if self.count % 100 == 0:
            self.file_obj.flush()

    def close(self):
        self.file_obj.close()


# =========================================================================
# Filtre de Kalman (copie depuis run_tracking_tpu.py)
# =========================================================================

class KalmanFilterND:
    """Filtre de Kalman vectorisé pour lisser le jittering sur les N Blendshapes."""
    def __init__(self, dim=52, process_variance=1e-4, measurement_variance=1e-2):
        self.dim = dim
        self.q = process_variance
        self.r = measurement_variance
        self.p = np.ones(dim)
        self.x = np.zeros(dim)
        self.is_initialized = False

    def update(self, measurements):
        measurements = np.array(measurements, dtype=np.float32)
        if not self.is_initialized:
            self.x = measurements
            self.is_initialized = True
            return self.x
        self.p = self.p + self.q
        k = self.p / (self.p + self.r)
        self.x = self.x + k * (measurements - self.x)
        self.p = (1 - k) * self.p
        return self.x


# =========================================================================
# OpenCV 5.0 DNN Model Loading
# =========================================================================

def get_onnx_input_shape(model_path):
    """Détermine la forme d'entrée attendue [W, H] d'un modèle ONNX."""
    try:
        import onnxruntime as ort
        tmp_sess = ort.InferenceSession(str(model_path), providers=['CPUExecutionProvider'])
        shape = tmp_sess.get_inputs()[0].shape
        if len(shape) >= 4:
            h, w = shape[2], shape[3]
            if isinstance(h, int) and h > 0 and isinstance(w, int) and w > 0:
                return w, h
    except Exception:
        pass
    return 640, 640


class CV5DNNNet:
    """Wrapper imitant l'API cv2.dnn.Net pour ajouter les attributs de taille."""
    def __init__(self, net, path, w, h):
        self.net = net
        self.path = path
        self.input_width = w
        self.input_height = h

    def setInput(self, blob, name=""):
        self.net.setInput(blob, name)

    def forward(self, outputNameOrList=None):
        if outputNameOrList:
            return self.net.forward(outputNameOrList)
        return self.net.forward()

    def getUnconnectedOutLayersNames(self):
        return self.net.getUnconnectedOutLayersNames()


def load_cv5_model(model_name):
    """Charge un modèle ONNX via OpenCV 5.0 DNN avec Fallback ONNX Runtime."""
    if os.path.isabs(model_name) or Path(model_name).exists():
        model_path = Path(model_name)
    else:
        model_path = ONNX_MODELS_DIR / model_name

    if not model_path.exists():
        logging.warning(f"Modèle ONNX manquant: {model_path}")
        return None

    w, h = get_onnx_input_shape(model_path)

    # 1. Tentative avec OpenCV DNN (uniquement si le moteur OpenCV 5.0 ENGINE_NEW est disponible)
    if hasattr(cv2.dnn, 'ENGINE_NEW'):
        try:
            logging.info(f"Tentative de chargement du modèle {model_name} avec OpenCV 5.0 DNN...")
            net = cv2.dnn.readNetFromONNX(str(model_path))
            net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            try:
                net.setEngineType(cv2.dnn.ENGINE_NEW)
            except Exception:
                pass
            logging.info(f"Modèle ONNX chargé via OpenCV 5.0 DNN: {model_name}")
            return CV5DNNNet(net, model_path, w, h)
        except Exception as dnn_err:
            logging.warning(f"Échec de chargement de {model_name} avec OpenCV DNN ({dnn_err}). Passage au fallback ONNX Runtime...")
    else:
        logging.info(f"Moteur OpenCV 5.0 (ENGINE_NEW) non disponible. Utilisation directe du fallback ONNX Runtime pour {model_name}...")

    # 2. Fallback ONNX Runtime
    try:
        class ORTDNNNet:
            """Wrapper imitant l'API cv2.dnn.Net pour un remplacement transparent par ONNX Runtime."""
            def __init__(self, path):
                import onnxruntime as ort
                opts = ort.SessionOptions()
                opts.intra_op_num_threads = 1
                opts.inter_op_num_threads = 1
                opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
                
                available_providers = ort.get_available_providers()
                providers = []
                if os.environ.get('STEP5_ENABLE_GPU', '0') == '1' and 'CUDAExecutionProvider' in available_providers:
                    providers.append('CUDAExecutionProvider')
                providers.append('CPUExecutionProvider')
                
                self.session = ort.InferenceSession(str(path), sess_options=opts, providers=providers)
                active_provider = self.session.get_providers()[0] if hasattr(self.session, 'get_providers') else providers[0]
                logging.info(f"Modèle ONNX {Path(path).name} chargé via ONNX Runtime avec le provider: {active_provider}")
                
                self.input_name = self.session.get_inputs()[0].name
                self.output_names = [o.name for o in self.session.get_outputs()]
                self.inputs = {}
                
                # Récupérer la taille d'entrée attendue
                try:
                    shape = self.session.get_inputs()[0].shape
                    self.input_height = shape[2] if len(shape) > 2 else 640
                    self.input_width = shape[3] if len(shape) > 3 else 640
                    if not isinstance(self.input_height, int) or self.input_height <= 0:
                        self.input_height = 640
                    if not isinstance(self.input_width, int) or self.input_width <= 0:
                        self.input_width = 640
                except Exception:
                    self.input_height = 640
                    self.input_width = 640

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
        logging.info(f"Modèle ONNX chargé via ONNX Runtime (fallback) : {model_name}")
        return net
    except Exception as ort_err:
        logging.error(f"Erreur fatale : Impossible de charger {model_name} via OpenCV DNN ou ONNX Runtime. Erreur ORT: {ort_err}")
        return None


def load_tflite_model(model_path, delegate=None):
    """Charge un modèle TFLite (fallback quand ONNX n'est pas disponible)."""
    try:
        import tflite_runtime.interpreter as tflite
    except ImportError:
        logging.warning("tflite_runtime non disponible pour le fallback.")
        return None

    if not Path(model_path).exists():
        logging.warning(f"Modèle TFLite manquant: {model_path}")
        return None

    try:
        delegates = [delegate] if delegate else []
        num_threads = 1 if not delegate else None
        interpreter = tflite.Interpreter(
            model_path=str(model_path),
            experimental_delegates=delegates,
            num_threads=num_threads
        )
        interpreter.allocate_tensors()
        return interpreter
    except Exception as e:
        logging.error(f"Impossible de charger {model_path}: {e}")
        return None


# =========================================================================
# Face Detection (BlazeFace) via OpenCV 5.0 DNN
# =========================================================================

def detect_face_cv5(net, image):
    """BlazeFace via OpenCV 5.0 DNN (ONNX).

    Args:
        net: cv2.dnn.Net chargé avec BlazeFace ONNX
        image: frame RGB numpy (H, W, 3)

    Returns:
        (bbox [ymin, xmin, ymax, xmax], eyes) ou (None, None)
    """
    if net is None:
        return [0.2, 0.2, 0.8, 0.8], None

    try:
        # BlazeFace attend 128x128 RGB normalisé [-1, 1]
        input_image = cv2.resize(image, (128, 128), interpolation=cv2.INTER_LINEAR)
        blob = cv2.dnn.blobFromImage(
            input_image, scalefactor=1.0/127.5, size=(128, 128),
            mean=(127.5, 127.5, 127.5), swapRB=False
        )
        net.setInput(blob)

        # L'output dépend de l'export ONNX : 2 tenseurs (regressors, classificators)
        output_names = net.getUnconnectedOutLayersNames()
        outputs = net.forward(output_names)

        if len(outputs) < 2:
            logging.warning("BlazeFace DNN: nombre de sorties inattendu, fallback mock")
            return [0.2, 0.2, 0.8, 0.8], None

        # Identifier classificators vs regressors par leur forme en retirant la dimension batch si présente
        out0 = outputs[0][0] if len(outputs[0].shape) == 3 else outputs[0]
        out1 = outputs[1][0] if len(outputs[1].shape) == 3 else outputs[1]

        if out0.shape[-1] == 1:
            classificators = out0.flatten()
            regressors = out1
        else:
            regressors = out0
            classificators = out1.flatten()

        scores = 1.0 / (1.0 + np.exp(-classificators))

        # Import lazy des utilitaires BlazeFace
        try:
            from utils import tpu_facemesh_utils as face_utils
            anchors = face_utils.generate_blazeface_anchors()
            boxes = face_utils.decode_blazeface_boxes(regressors, anchors)
            keep, final_boxes, final_scores = face_utils.nms(boxes, scores, score_threshold=0.7)
        except ImportError:
            logging.warning("tpu_facemesh_utils non disponible, fallback mock")
            return [0.2, 0.2, 0.8, 0.8], None

        if not keep:
            return None, None

        best_box = final_boxes[keep[0]]
        xmin, ymin, xmax, ymax = best_box[0:4]
        bbox = [ymin, xmin, ymax, xmax]

        eyes = None
        if len(best_box) >= 8:
            right_eye = (best_box[4], best_box[5])
            left_eye = (best_box[6], best_box[7])
            eyes = (right_eye, left_eye)

        return bbox, eyes

    except Exception as e:
        logging.error(f"Erreur BlazeFace DNN: {e}")
        return [0.2, 0.2, 0.8, 0.8], None


def extract_landmarks_cv5(net, image_crop):
    """FaceMesh via OpenCV 5.0 DNN (ONNX).

    Args:
        net: cv2.dnn.Net chargé avec FaceMesh ONNX
        image_crop: crop du visage (H, W, 3)

    Returns:
        landmarks array (468, 3)
    """
    if net is None:
        return np.random.rand(468, 3)

    try:
        input_image = cv2.resize(image_crop, (192, 192), interpolation=cv2.INTER_LINEAR)
        blob = cv2.dnn.blobFromImage(
            input_image, scalefactor=1.0/127.5, size=(192, 192),
            mean=(127.5, 127.5, 127.5), swapRB=False
        )
        net.setInput(blob)
        output = net.forward()
        return output.reshape(-1, 3)

    except Exception as e:
        logging.error(f"Erreur FaceMesh DNN: {e}")
        return np.random.rand(468, 3)


def extract_blendshapes_cv5(blendshapes_model, landmarks):
    """Extraction des blendshapes via TFLite CPU (pas d'ONNX pour ce modèle).

    Les blendshapes utilisent un réseau léger qui reste sur TFLite CPU
    car le modèle face_blendshapes.tflite est optimisé pour ce runtime.

    Args:
        blendshapes_model: tflite Interpreter ou None
        landmarks: array (468, 3)

    Returns:
        array de 52 scores blendshapes
    """
    if blendshapes_model is None:
        return np.zeros(52)

    try:
        points_2d = landmarks[:, :2]
        subset_136 = points_2d[BLENDSHAPE_136_INDICES]

        # Calcul des centroïdes iris (même logique que run_tracking_tpu.py)
        left_iris_centroid = (points_2d[386] + points_2d[374]) / 2.0
        left_iris_padding = np.tile(left_iris_centroid, (5, 1))
        right_iris_centroid = (points_2d[159] + points_2d[145]) / 2.0
        right_iris_padding = np.tile(right_iris_centroid, (5, 1))

        input_146 = np.vstack((subset_136, left_iris_padding, right_iris_padding))

        input_details = blendshapes_model.get_input_details()[0]
        input_data = input_146.reshape(input_details['shape']).astype(input_details['dtype'])

        blendshapes_model.set_tensor(input_details['index'], input_data)
        blendshapes_model.invoke()

        output_details = blendshapes_model.get_output_details()[0]
        logits = blendshapes_model.get_tensor(output_details['index']).flatten()
        scores = 1.0 / (1.0 + np.exp(-logits))
        return scores

    except Exception as e:
        logging.error(f"Erreur Blendshapes: {e}")
        return np.zeros(52)



def detect_objects_yolo_cv5(net, image, original_width, original_height, threshold=0.3, nms_threshold=0.45):
    """Détecte les objets avec YOLOv8/v11 ONNX via OpenCV 5.0 DNN ou ORT GPU."""
    if net is None:
        return []

    try:
        input_w = getattr(net, "input_width", 640)
        input_h = getattr(net, "input_height", 640)
        # Redimensionner l'image à la taille d'entrée attendue
        resized = cv2.resize(image, (input_w, input_h))
        
        # Créer le blob (YOLOv8/v11 s'attend à des valeurs normalisées [0, 1])
        blob = cv2.dnn.blobFromImage(resized, scalefactor=1.0/255.0, size=(input_w, input_h), swapRB=False)
        
        net.setInput(blob)
        outputs = net.forward()
        
        # La sortie de YOLOv8/v11 est de la forme [1, 84, 8400] ou [84, 8400]
        if len(outputs.shape) == 3:
            output = outputs[0]  # [84, 8400]
        else:
            output = outputs     # [84, 8400]
            
        # Transposer pour avoir [8400, 84]
        output = output.T  # [8400, 84]
        
        boxes = []
        confidences = []
        class_ids = []
        
        # Les 80 classes COCO par défaut
        COCO_CLASSES = [
            "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
            "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
            "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
            "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
            "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
            "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
            "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
            "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
            "hair drier", "toothbrush"
        ]
        
        for row in output:
            classes_scores = row[4:]
            class_id = np.argmax(classes_scores)
            confidence = classes_scores[class_id]
            
            if confidence > threshold:
                # YOLO coordonnées : x_center, y_center, width, height (normalisées à la taille attendue)
                x_c, y_c, w, h = row[0:4]
                
                # Projeter sur les dimensions de la vidéo d'origine (original_width, original_height)
                x_min = (x_c - w/2) / input_w * original_width
                y_min = (y_c - h/2) / input_h * original_height
                w_orig = w / input_w * original_width
                h_orig = h / input_h * original_height
                
                boxes.append([int(x_min), int(y_min), int(w_orig), int(h_orig)])
                confidences.append(float(confidence))
                class_ids.append(int(class_id))
                
        # Appliquer NMS (Suppression Non Maximale)
        indices = cv2.dnn.NMSBoxes(boxes, confidences, threshold, nms_threshold)
        
        detections = []
        if len(indices) > 0:
            flat_indices = np.array(indices).flatten()
            for i in flat_indices:
                box = boxes[i]
                cid = class_ids[i]
                label = COCO_CLASSES[cid] if cid < len(COCO_CLASSES) else f"object_{cid}"
                
                x_min, y_min, w, h = box
                centroid = (x_min + w // 2, y_min + h // 2)
                
                detections.append({
                    "bbox": (x_min, y_min, w, h),
                    "centroid": centroid,
                    "source_detector": "object_detector",
                    "label": label,
                    "confidence": confidences[i],
                    "blendshapes": None,
                    "is_speaking": None
                })
                
        return detections

    except Exception as e:
        logging.error(f"Erreur détection d'objets YOLOv11: {e}")
        return []


# =========================================================================
# Video Metadata
# =========================================================================

def get_video_metadata_ffprobe(video_path):
    """Récupère les métadonnées vidéo via ffprobe."""
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate,nb_frames',
            '-of', 'json', str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)
        stream_info = info.get('streams', [{}])[0]

        width = int(stream_info.get('width', 1280))
        height = int(stream_info.get('height', 720))

        fps_str = stream_info.get('r_frame_rate', '25/1')
        num, den = map(int, fps_str.split('/'))
        fps = num / den if den > 0 else 25.0

        nb_frames_str = stream_info.get('nb_frames')
        total_frames = int(nb_frames_str) if nb_frames_str else None

        return width, height, fps, total_frames
    except Exception as e:
        logging.warning(f"Impossible de lire les métadonnées de {video_path.name} via ffprobe: {e}")
        return 1280, 720, 25.0, None


# =========================================================================
# Pipeline Principal (Sequential - mode OpenCV 5.0)
# =========================================================================

def run_tracking_pipeline_cv5(video_path, blazeface_net, facemesh_net, blendshapes_model,
                               width, height, fps, total_frames, speaking_detector, stream_out,
                               object_detector_net=None, progress_callback=None):
    """Pipeline de tracking séquentiel avec OpenCV 5.0 DNN.

    Thread safety :
      - cv2.setNumThreads(1) forcé pour éviter l'oversubscription
      - Pas de fork, exécution single-threaded pour l'inférence
    """
    # CRITICAL: Throttle OpenCV threads to avoid contention with other runtimes
    cv2.setNumThreads(1)

    model_width, model_height = 256, 256

    cmd = [
        'ffmpeg', '-i', str(video_path),
        '-f', 'image2pipe', '-pix_fmt', 'rgb24',
        '-s', f'{model_width}x{model_height}', '-r', str(fps),
        '-vcodec', 'rawvideo', '-loglevel', 'error', '-'
    ]

    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**8)
    frame_size = model_width * model_height * 3

    # Filtre temporel
    from utils.one_euro_filter import OneEuroFilterND
    temporal_filter = OneEuroFilterND(dim=52, rate=fps, min_cutoff=1.0, beta=0.007)

    # Import conditionnel de face_utils
    try:
        from utils import tpu_facemesh_utils as face_utils
        has_face_utils = True
    except ImportError:
        has_face_utils = False
        logging.warning("tpu_facemesh_utils non disponible, transformations affines désactivées")

    frame_idx = 0
    active_objects = {}
    next_id_counter = {"value": 0}

    logging.info(f"Démarrage de la cascade OpenCV 5.0 DNN pour {video_path.name}")

    while True:
        raw_image = process.stdout.read(frame_size)
        if len(raw_image) != frame_size:
            break

        image = np.frombuffer(raw_image, dtype=np.uint8).reshape((model_height, model_width, 3))

        current_detections = []

        # 1. Détection (BlazeFace OpenCV 5.0 DNN)
        res = detect_face_cv5(blazeface_net, image)

        if res != (None, None):
            raw_bbox, eyes = res
            ymin, xmin, ymax, xmax = raw_bbox

            bbox_xmin = int(xmin * width)
            bbox_ymin = int(ymin * height)
            bbox_width = int((xmax - xmin) * width)
            bbox_height = int((ymax - ymin) * height)
            centroid_x = int(bbox_xmin + bbox_width / 2)
            centroid_y = int(bbox_ymin + bbox_height / 2)

            # 2. Crop et alignement affine du visage
            if eyes and has_face_utils:
                right_eye, left_eye = eyes
                transform_params = face_utils.get_affine_transform(right_eye, left_eye, output_size=192)
                face_crop_192 = face_utils.apply_affine_crop(image, transform_params)
            else:
                face_crop_192 = cv2.resize(image, (192, 192))

            # 3. Landmarks (FaceMesh OpenCV 5.0 DNN)
            landmarks = extract_landmarks_cv5(facemesh_net, face_crop_192)

            # 4. Blendshapes (TFLite CPU fallback)
            raw_blendshapes = extract_blendshapes_cv5(blendshapes_model, landmarks)

            # 5. Filtrage temporel
            smoothed_blendshapes = temporal_filter.update(raw_blendshapes).tolist()

            blendshapes_dict = dict(zip(
                ARKIT_52_BLENDSHAPE_NAMES,
                (float(v) for v in smoothed_blendshapes)
            ))

            current_detections.append({
                "centroid": (centroid_x, centroid_y),
                "bbox": (bbox_xmin, bbox_ymin, bbox_width, bbox_height),
                "blendshapes": blendshapes_dict,
                "source_detector": "face_landmarker",
                "label": "face",
                "confidence": 0.95
            })
        # 5b. Détection d'objets (YOLOv11 ONNX GPU/CPU) s'il n'y a pas de visage détecté
        enable_object_detection = os.environ.get("STEP5_ENABLE_OBJECT_DETECTION", "1") == "1"
        if not current_detections and enable_object_detection and object_detector_net is not None:
            obj_detections = detect_objects_yolo_cv5(object_detector_net, image, width, height)
            current_detections.extend(obj_detections)

        # 6. Apply Tracking and Management
        tracked_objects = apply_tracking_and_management(
            active_objects=active_objects,
            current_detections=current_detections,
            next_id_counter=next_id_counter,
            distance_threshold=100.0,
            frames_unseen_to_deregister=10,
            speaking_detection_jaw_open_threshold=0.08,
            enhanced_speaking_detector=speaking_detector,
            current_frame_num=frame_idx + 1
        )

        stream_out.add_frame({
            "frame": frame_idx + 1,
            "tracked_objects": tracked_objects
        })

        frame_idx += 1
        if frame_idx % 25 == 0:
            progress_percent = int((frame_idx / total_frames) * 100) if total_frames else 0
            if progress_callback:
                progress_callback(frame_idx, total_frames, progress_percent)
            else:
                logging.info(f"INTERNAL_PROGRESS: {frame_idx}/{total_frames} frames ({progress_percent}%) - {video_path.name}")
                print(f"INTERNAL_PROGRESS: {frame_idx}/{total_frames} frames ({progress_percent}%) - {video_path.name}", flush=True)

    if total_frames:
        if progress_callback:
            progress_callback(total_frames, total_frames, 100)
        else:
            logging.info(f"INTERNAL_PROGRESS: {total_frames}/{total_frames} frames (100%) - {video_path.name}")
            print(f"INTERNAL_PROGRESS: {total_frames}/{total_frames} frames (100%) - {video_path.name}", flush=True)

    process.stdout.close()
    process.wait()

    return frame_idx


# =========================================================================
# Multiprocessing Pipeline (spawn-safe)
# =========================================================================

def _worker_process(video_path_str, blazeface_onnx_path, facemesh_onnx_path, blendshapes_tflite_path,
                    object_detector_onnx_path, width, height, fps, total_frames, output_path, ndjson, result_queue):
    """Worker process (spawned) pour le tracking OpenCV 5.0 DNN.

    CRITICAL: Ce worker est exécuté dans un processus spawné.
    - cv2.setNumThreads(1) pour éviter l'oversubscription
    - Pas de partage d'état avec le processus parent
    """
    import logging
    log_file_worker = LOG_DIR / f"worker_CPU_cv5_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - WORKER_CV5 - %(message)s',
        handlers=[
            logging.FileHandler(log_file_worker, encoding='utf-8')
        ]
    )

    # CRITICAL: Throttle threads
    cv2.setNumThreads(1)

    video_path = Path(video_path_str)

    try:
        # Charger les modèles dans le worker (spawn = pas de partage)
        blazeface_net = load_cv5_model(Path(blazeface_onnx_path).name) if blazeface_onnx_path else None
        facemesh_net = load_cv5_model(Path(facemesh_onnx_path).name) if facemesh_onnx_path else None
        blendshapes_model = load_tflite_model(blendshapes_tflite_path) if blendshapes_tflite_path else None
        object_detector_net = load_cv5_model(str(object_detector_onnx_path)) if object_detector_onnx_path else None

        speaking_detector = EnhancedSpeakingDetector(
            video_path=str(video_path),
            jaw_threshold=0.08
        )

        metadata = {
            "video_path": str(video_path),
            "original_fps": fps,
            "resolution": {"width": width, "height": height},
            "total_frames_processed": total_frames,
            "engine": "opencv5_dnn",
            "tracking_method": "kdtree_cv5"
        }

        if ndjson:
            stream_out = StreamingNDJSONOutput(output_path, metadata)
        else:
            stream_out = StreamingJSONOutput(output_path, metadata)

        def progress_cb(frame_idx, total, pct):
            result_queue.put(("progress", str(video_path), (pct, frame_idx, total)))

        frame_count = run_tracking_pipeline_cv5(
            video_path, blazeface_net, facemesh_net, blendshapes_model,
            width=width, height=height, fps=fps, total_frames=total_frames,
            speaking_detector=speaking_detector, stream_out=stream_out,
            object_detector_net=object_detector_net,
            progress_callback=progress_cb
        )

        stream_out.close()
        result_queue.put(("success", str(video_path), frame_count))

    except Exception as e:
        import traceback
        traceback.print_exc()
        result_queue.put(("error", str(video_path), str(e)))


# =========================================================================
# Main
# =========================================================================

def main():
    # CRITICAL: Force 'spawn' pour éviter les deadlocks fork + OpenCV/TFLite
    mp.set_start_method('spawn', force=True)

    parser = argparse.ArgumentParser(
        description="Analyse du tracking avec OpenCV 5.0 DNN (expérimental)"
    )
    parser.add_argument("--videos_json_path", help="Chemin JSON des vidéos à traiter.")
    parser.add_argument("--out", type=str, default="tracking_output.json", help="Chemin sortie JSON")
    parser.add_argument("--ndjson", action="store_true", help="Format de sortie NDJSON")
    parser.add_argument("--num_workers", type=int, default=1, help="Nombre de workers parallèles (défaut: 1)")
    args = parser.parse_args()

    logging.info("--- Démarrage de l'analyse Tracking OpenCV 5.0 DNN ---")
    logging.info(f"OpenCV version: {cv2.__version__}")
    logging.info(f"Backend: OpenCV DNN (ONNX), Engine: {'ENGINE_NEW' if hasattr(cv2.dnn, 'ENGINE_NEW') else 'LEGACY'}")

    # Modèles
    assets_dir = BASE_DIR / "assets"
    blazeface_onnx = ONNX_MODELS_DIR / "blazeface.onnx"
    facemesh_onnx = ONNX_MODELS_DIR / "facemesh.onnx"
    blendshapes_tflite = assets_dir / "face_blendshapes.tflite"

    # Vérification des modèles ONNX
    models_available = True
    for model_path, name in [(blazeface_onnx, "BlazeFace"), (facemesh_onnx, "FaceMesh")]:
        if not model_path.exists():
            logging.warning(f"Modèle ONNX {name} manquant: {model_path}")
            logging.warning(f"Le tracking fonctionnera en mode dégradé (mock detections)")
            models_available = False

    if not blendshapes_tflite.exists():
        logging.warning(f"Modèle Blendshapes TFLite manquant: {blendshapes_tflite}")

    # Découverte des vidéos
    if args.videos_json_path:
        try:
            with open(args.videos_json_path, 'r', encoding='utf-8') as f:
                video_data = json.load(f)
            
            if isinstance(video_data, dict) and "videos" in video_data:
                logging.info("Legacy videos JSON schema detected")
                video_paths = video_data["videos"]
            elif isinstance(video_data, list):
                video_paths = video_data
            else:
                logging.error("Invalid JSON format. Expected list of video paths or legacy dict.")
                sys.exit(1)
                
            videos = [Path(p) for p in video_paths]
        except Exception as e:
            logging.error(f"Impossible de lire le fichier JSON: {e}")
            sys.exit(1)
    else:
        videos = [p for ext in VIDEO_EXTENSIONS for p in WORK_DIR.rglob(f'*{ext}')]

    total_videos = len(videos)
    if total_videos == 0:
        logging.info("Aucune vidéo à traiter.")
        return

    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")
    print(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}", flush=True)

    # Gestion SIGTERM
    def handle_sigterm(signum, frame):
        logging.info("SIGTERM received. Terminaison...")
        os._exit(0)
    signal.signal(signal.SIGTERM, handle_sigterm)

    t_start = time.perf_counter()
    successful_count = 0

    # Résoudre le modèle de détection d'objets si activé
    enable_object_detection = os.environ.get("STEP5_ENABLE_OBJECT_DETECTION", "1") == "1"
    object_model_path = None
    if enable_object_detection:
        try:
            # En mode CV5, on ignore les configurations TFLite du .env pour rester compatible sans modification
            env_path = os.environ.get('STEP5_OBJECT_DETECTOR_MODEL_PATH', '')
            
            # Pour éviter que ObjectDetectorRegistry.resolve_model_path ne charge le modèle TFLite depuis l'env
            # si celui-ci n'est pas au format ONNX
            if env_path and not env_path.endswith('.onnx'):
                orig_env_val = os.environ.pop('STEP5_OBJECT_DETECTOR_MODEL_PATH', None)
            else:
                orig_env_val = None
                
            override_path = env_path if env_path.endswith('.onnx') else None
            
            model_name = os.environ.get("STEP5_OBJECT_DETECTOR_MODEL", "yolo11n_onnx")
            if not model_name.endswith('_onnx') and model_name != 'nanodet_plus':
                # Forcer un modèle ONNX pour OpenCV 5.0
                model_name = 'yolo11n_onnx'
                
            try:
                object_model_path = ObjectDetectorRegistry.resolve_model_path(
                    model_name=model_name,
                    override_path=override_path
                )
            finally:
                if orig_env_val is not None:
                    os.environ['STEP5_OBJECT_DETECTOR_MODEL_PATH'] = orig_env_val
                    
            logging.info(f"Détecteur d'objets CV5 résolu: {model_name} -> {object_model_path}")
        except Exception as e_res:
            logging.warning(f"Impossible de résoudre le modèle de détection d'objets ONNX: {e_res}. Fallback sans détection d'objets.")

    if args.num_workers <= 1:
        # Mode séquentiel (chargement unique des modèles)
        cv2.setNumThreads(1)

        blazeface_net = load_cv5_model("blazeface.onnx")
        facemesh_net = load_cv5_model("facemesh.onnx")
        blendshapes_model = load_tflite_model(str(blendshapes_tflite))
        object_detector_net = load_cv5_model(str(object_model_path)) if object_model_path else None

        for idx, video_path in enumerate(videos):
            logging.info(f"PROCESSING_VIDEO: {video_path.name}")
            print(f"PROCESSING_VIDEO: {video_path.name}", flush=True)

            try:
                vid_width, vid_height, vid_fps, vid_total_frames = get_video_metadata_ffprobe(video_path)

                speaking_detector = EnhancedSpeakingDetector(
                    video_path=str(video_path),
                    jaw_threshold=0.08
                )

                output_json = video_path.with_suffix('.json')
                metadata = {
                    "video_path": str(video_path),
                    "original_fps": vid_fps,
                    "resolution": {"width": vid_width, "height": vid_height},
                    "total_frames_processed": vid_total_frames,
                    "engine": "opencv5_dnn",
                    "tracking_method": "kdtree_cv5"
                }

                if args.ndjson:
                    stream_out = StreamingNDJSONOutput(output_json, metadata)
                else:
                    stream_out = StreamingJSONOutput(output_json, metadata)

                frame_count = run_tracking_pipeline_cv5(
                    video_path, blazeface_net, facemesh_net, blendshapes_model,
                    width=vid_width, height=vid_height, fps=vid_fps, total_frames=vid_total_frames,
                    speaking_detector=speaking_detector, stream_out=stream_out,
                    object_detector_net=object_detector_net
                )

                stream_out.close()
                logging.info(f"Succès: {output_json.name} créé avec {frame_count} frames.")
                successful_count += 1

            except Exception as e:
                logging.exception(f"Échec de l'analyse tracking pour {video_path.name}: {e}")

    else:
        # Mode multiprocessing (spawn)
        ctx = mp.get_context('spawn')
        result_queue = ctx.Queue()

        active_workers = []
        video_iter = iter(enumerate(videos))

        def launch_next():
            try:
                idx, video_path = next(video_iter)
            except StopIteration:
                return False

            logging.info(f"PROCESSING_VIDEO: {video_path.name}")
            # NOTE: We do not print to stdout here to avoid flickering on the UI.
            # Multi-line progress takes care of displaying currently processing videos.

            vid_width, vid_height, vid_fps, vid_total_frames = get_video_metadata_ffprobe(video_path)
            output_json = video_path.with_suffix('.json')

            p = ctx.Process(target=_worker_process, args=(
                str(video_path),
                str(blazeface_onnx) if blazeface_onnx.exists() else None,
                str(facemesh_onnx) if facemesh_onnx.exists() else None,
                str(blendshapes_tflite) if blendshapes_tflite.exists() else None,
                str(object_model_path) if object_model_path else None,
                vid_width, vid_height, vid_fps, vid_total_frames,
                str(output_json), args.ndjson, result_queue
            ))
            p.start()
            active_workers.append(p)
            return True

        # Lancer les premiers workers
        for _ in range(min(args.num_workers, total_videos)):
            launch_next()

        completed = 0
        active_progress = {}
        active_pcts = {}
        video_indices = {str(v): i + 1 for i, v in enumerate(videos)}

        while completed < total_videos:
            try:
                msg_type, vpath, info = result_queue.get(timeout=300)
                vname = Path(vpath).name

                if msg_type == "progress":
                    pct, frame_idx, total = info
                    abs_idx = video_indices[vpath]
                    active_progress[vname] = f"{vname} ({pct}%) ({abs_idx}/{total_videos})"
                    active_pcts[vname] = pct

                    # Print multi-line progress
                    progress_parts = [status for name, status in sorted(active_progress.items())]
                    if progress_parts:
                        print(f"[Progression-MultiLine]{' || '.join(progress_parts)}", flush=True)

                        # Calculate overall fractional progress based on completed videos and active progresses
                        sum_active_pct = sum(active_pcts.values()) / 100.0
                        overall_progress_pct = int(((completed + sum_active_pct) / total_videos) * 100)
                        # Print overall progress without a filename to update the progress bar smoothly
                        print(f"INTERNAL_PROGRESS: 0/0 frames ({overall_progress_pct}%) - ", flush=True)

                elif msg_type == "success":
                    completed += 1
                    logging.info(f"Succès: {vname} créé avec {info} frames.")
                    if vname in active_progress:
                        del active_progress[vname]
                    if vname in active_pcts:
                        del active_pcts[vname]

                    # Print success line so app_new.py increments files_completed
                    json_name = Path(vpath).with_suffix('.json').name
                    print(f"Succès: {json_name} créé", flush=True)
                    successful_count += 1

                    # Lancer le prochain worker
                    launch_next()

                elif msg_type == "error":
                    completed += 1
                    logging.error(f"Échec pour {vname}: {info}")
                    if vname in active_progress:
                        del active_progress[vname]
                    if vname in active_pcts:
                        del active_pcts[vname]

                    # Print fail line so app_new.py updates state
                    print(f"Échec: {vname} échoué", flush=True)

                    # Lancer le prochain worker
                    launch_next()

            except Exception as e:
                logging.error(f"Erreur queue: {e}")
                break

        # Attendre tous les workers
        for p in active_workers:
            p.join(timeout=10)

    total_elapsed = time.perf_counter() - t_start
    logging.info(
        f"--- Analyse terminée. {successful_count}/{total_videos} réussie(s). "
        f"Temps total: {total_elapsed:.1f}s ---"
    )

    if successful_count < total_videos:
        sys.exit(1)


if __name__ == "__main__":
    main()
