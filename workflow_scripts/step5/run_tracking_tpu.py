#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'analyse du tracking (BlazeFace -> FaceMesh -> Blendshapes) avec Google Coral Edge TPU
Version Ubuntu - Étape 5 (Alternative à MediaPipe/InsightFace CPU)
"""

import os
import sys
import json
import argparse
import logging
import subprocess
import threading
import queue
import multiprocessing as mp
from multiprocessing import shared_memory
import numpy as np
import cv2
from pathlib import Path
from datetime import datetime

try:
    import orjson
    _HAS_ORJSON = True
except ImportError:
    _HAS_ORJSON = False

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

# Gestion des dépendances Edge TPU supprimée globalement pour éviter les crashs (Lazy Load)

# --- Configuration Globale ---
WORK_DIR = Path(os.getcwd())
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).parent.parent
sys.path.append(str(BASE_DIR))

try:
    from utils.tracking_optimizations import apply_tracking_and_management
    from utils.enhanced_speaking_detection import EnhancedSpeakingDetector
    from utils import tpu_facemesh_utils as face_utils
except ImportError as e:
    logging.critical(f"ERREUR: Impossible d'importer les utilitaires. Vérifiez PYTHONPATH: {e}")
    sys.exit(1)

VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')

# --- Configuration du Logger ---
LOG_DIR = BASE_DIR / "logs" / "step5"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"tpu_tracking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

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
        """
        Ferme le tableau et le fichier correctement.
        """
        self.file_obj.write("\n  ]\n}")
        self.file_obj.close()


class StreamingNDJSONOutput:
    """
    Sérialisation en streaming NDJSON (JSON Lines) avec une empreinte mémoire O(1).
    Chaque ligne est un objet JSON indépendant.
    """
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
        """Ajoute une frame au fichier NDJSON."""
        self._write_line(frame_dict)
        self.count += 1
        if self.count % 100 == 0:
            self.file_obj.flush()
            
    def close(self):
        """Ferme le fichier correctement."""
        self.file_obj.close()

class KalmanFilterND:
    """
    Filtre de Kalman vectorisé pour lisser le jittering INT8 sur les N Blendshapes.
    """
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

        # Prédiction
        self.p = self.p + self.q
        
        # Mise à jour
        k = self.p / (self.p + self.r)
        self.x = self.x + k * (measurements - self.x)
        self.p = (1 - k) * self.p
        
        return self.x

def load_tpu_model(model_path: Path, delegate=None):
    """Charge un modèle TFLite sur le delegate TPU ou CPU"""
    import tflite_runtime.interpreter as tflite
    if not model_path.exists():
        logging.warning(f"Modèle manquant: {model_path}. Simulation de son exécution.")
        return None
    try:
        delegates = [delegate] if delegate else []
        # Limiter à 1 thread si l'exécution se fait sur CPU (sans delegate) pour éviter l'oversubscription
        num_threads = 1 if not delegate else None
        interpreter = tflite.Interpreter(
            model_path=str(model_path),
            experimental_delegates=delegates,
            num_threads=num_threads
        )
        interpreter.allocate_tensors()
        return interpreter
    except Exception as e:
        logging.error(f"Impossible de charger le modèle {model_path.name}: {e}")
        return None

def detect_face(interpreter, image):
    """BlazeFace TPU (Detection)"""
    if not interpreter:
        return [0.2, 0.2, 0.8, 0.8], None # Bounding box mock [ymin, xmin, ymax, xmax]
    
    try:
        input_details = interpreter.get_input_details()[0]
        h, w = input_details['shape'][1], input_details['shape'][2]
        
        if image.shape[0] != h or image.shape[1] != w:
            input_image = cv2.resize(image, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            input_image = image
            
        if input_details['dtype'] == np.float32:
            input_image = (input_image.astype(np.float32) / 127.5) - 1.0
            
        interpreter.tensor(input_details['index'])()[0][:, :] = input_image
        interpreter.invoke()
        
        output_details = interpreter.get_output_details()
        tensor_0 = interpreter.get_tensor(output_details[0]['index'])[0]
        tensor_1 = interpreter.get_tensor(output_details[1]['index'])[0]
        
        # Le compilateur Edge TPU peut inverser l'ordre des tenseurs
        if tensor_0.shape[-1] == 1:
            classificators = tensor_0
            regressors = tensor_1
        else:
            regressors = tensor_0
            classificators = tensor_1
        
        scores = 1.0 / (1.0 + np.exp(-classificators.flatten()))
        anchors = face_utils.generate_blazeface_anchors()
        boxes = face_utils.decode_blazeface_boxes(regressors, anchors)
        
        keep, final_boxes, final_scores = face_utils.nms(boxes, scores, score_threshold=0.7)
        if not keep:
            return None, None
            
        best_box = final_boxes[keep[0]]
        xmin, ymin, xmax, ymax = best_box[0:4]
        bbox = [ymin, xmin, ymax, xmax]
        
        right_eye = (best_box[4], best_box[5])
        left_eye = (best_box[6], best_box[7])
        
        return bbox, (right_eye, left_eye)
    except Exception as e:
        logging.error(f"Erreur BlazeFace: {e}")
        return [0.2, 0.2, 0.8, 0.8], None # Bounding box mock [ymin, xmin, ymax, xmax]


def extract_landmarks(interpreter, image_crop):
    """FaceMesh TPU"""
    if not interpreter:
        return np.random.rand(468, 3) # Mock 468 landmarks
        
    try:
        input_details = interpreter.get_input_details()[0]
        h, w = input_details['shape'][1], input_details['shape'][2]
        if image_crop.shape[0] != h or image_crop.shape[1] != w:
            input_image = cv2.resize(image_crop, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            input_image = image_crop
            
        if input_details['dtype'] == np.float32:
            input_image = (input_image.astype(np.float32) / 127.5) - 1.0
            
        interpreter.tensor(input_details['index'])()[0][:, :] = input_image
        interpreter.invoke()
        
        output_details = interpreter.get_output_details()
        output = interpreter.get_tensor(output_details[0]['index'])[0].copy()
        return output.reshape(-1, 3)
    except Exception as e:
        logging.error(f"Erreur FaceMesh: {e}")
        return np.random.rand(468, 3)

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

def extract_blendshapes(interpreter, landmarks):
    """Face Blendshapes CPU avec Padding des 146 points (Stratégie Hybride GPU-less)"""
    if not interpreter:
        return np.zeros(52)
        
    try:
        # Extraire seulement X, Y (ignorer Z)
        points_2d = landmarks[:, :2]
        
        # 1. Extraire les 136 points natifs
        subset_136 = points_2d[BLENDSHAPE_136_INDICES]
        
        # 2. Calculer les 10 points manquants de l'iris via Centroïdes (Padding)
        # Iris Gauche : moyenne entre 386 (haut) et 374 (bas)
        left_iris_centroid = (points_2d[386] + points_2d[374]) / 2.0
        left_iris_padding = np.tile(left_iris_centroid, (5, 1))
        
        # Iris Droit : moyenne entre 159 (haut) et 145 (bas)
        right_iris_centroid = (points_2d[159] + points_2d[145]) / 2.0
        right_iris_padding = np.tile(right_iris_centroid, (5, 1))
        
        # 3. Concaténer pour former les 146 points exacts
        input_146 = np.vstack((subset_136, left_iris_padding, right_iris_padding))
        
        input_details = interpreter.get_input_details()[0]
        
        # 4. Formater pour le tenseur [1, 146, 2]
        input_data = input_146.reshape(input_details['shape']).astype(input_details['dtype'])
        
        interpreter.set_tensor(input_details['index'], input_data)
        interpreter.invoke()
        
        output_details = interpreter.get_output_details()[0]
        logits = interpreter.get_tensor(output_details['index']).flatten()
        
        # Application Sigmoïde (certains modèles retournent déjà des probas, d'autres des logits)
        scores = 1.0 / (1.0 + np.exp(-logits))
        return scores
    except Exception as e:
        logging.error(f"Erreur Blendshapes: {e}")
        return np.zeros(52)

def get_video_metadata_ffprobe(video_path: Path):
    """Récupère les métadonnées vidéo sans cv2 en utilisant ffprobe"""
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

def run_tracking_pipeline(video_path: Path, blazeface, facemesh, blendshapes, object_detector_tpu, width, height, fps, total_frames, speaking_detector, stream_out):
    """
    Exécute la cascade d'inférence TPU sur chaque frame vidéo via FFmpeg.
    """
    model_width, model_height = 256, 256 # Résolution fixée pour simplifier le redimensionnement d'entrée
    
    cmd = [
        'ffmpeg', '-i', str(video_path),
        '-f', 'image2pipe', '-pix_fmt', 'rgb24',
        '-s', f'{model_width}x{model_height}', '-r', str(fps),
        '-vcodec', 'rawvideo', '-loglevel', 'error', '-'
    ]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10**8)
    frame_size = model_width * model_height * 3
    
    kalman_filter = KalmanFilterND(dim=52, process_variance=1e-3, measurement_variance=2e-2)
    
    frame_idx = 0
    
    # Tracking states
    active_objects = {}
    next_id_counter = {"value": 0}
    
    logging.info(f"Démarrage de la cascade TPU pour {video_path.name}")
    
    while True:
        raw_image = process.stdout.read(frame_size)
        if len(raw_image) != frame_size:
            break
            
        image = np.frombuffer(raw_image, dtype=np.uint8).reshape((model_height, model_width, 3))
        
        current_detections = []
        
        # 1. Détection (BlazeFace)
        # Mock: detect_face return [ymin, xmin, ymax, xmax] in normalized coordinates (0 to 1)
        res = detect_face(blazeface, image)
        
        if res != (None, None):
            raw_bbox, eyes = res
            ymin, xmin, ymax, xmax = raw_bbox
            
            # Convert to original video coordinates
            bbox_xmin = int(xmin * width)
            bbox_ymin = int(ymin * height)
            bbox_width = int((xmax - xmin) * width)
            bbox_height = int((ymax - ymin) * height)
            centroid_x = int(bbox_xmin + bbox_width / 2)
            centroid_y = int(bbox_ymin + bbox_height / 2)
            
            # 2. Découpage et Alignement Affine du visage
            if eyes:
                right_eye, left_eye = eyes
                transform_params = face_utils.get_affine_transform(right_eye, left_eye, output_size=192)
                face_crop_192 = face_utils.apply_affine_crop(image, transform_params)
            else:
                face_crop_192 = cv2.resize(image, (192, 192))
                
            # 3. Landmarks (FaceMesh TPU)
            landmarks = extract_landmarks(facemesh, face_crop_192)
            
            # 4. Blendshapes (CPU fallback)
            raw_blendshapes = extract_blendshapes(blendshapes, landmarks)
            
            # 5. Filtrage Temporel (One-Euro Filter @njit)
            if frame_idx == 0:
                from utils.one_euro_filter import OneEuroFilterND
                temporal_filter = OneEuroFilterND(dim=52, rate=fps, min_cutoff=1.0, beta=0.007)
                
            smoothed_blendshapes = temporal_filter.update(raw_blendshapes).tolist()
            
            # Convert list to dict with ARKit names
            blendshapes_dict = dict(zip(
                ARKIT_52_BLENDSHAPE_NAMES,
                (float(v) for v in smoothed_blendshapes)
            ))
            
            # Construct current detections list
            current_detections.append({
                "centroid": (centroid_x, centroid_y),
                "bbox": (bbox_xmin, bbox_ymin, bbox_width, bbox_height),
                "blendshapes": blendshapes_dict,
                "source_detector": "face_landmarker",
                "label": "face",
                "confidence": 0.95
            })
            
        # 6. Object Detection (Fallback conditionnel pour éviter le TPU Context Switch)
        if not current_detections and object_detector_tpu:
            input_details = object_detector_tpu.get_input_details()[0]
            od_height, od_width = input_details['shape'][1], input_details['shape'][2]
            
            # Remplacement de Pillow par OpenCV cv2.resize beaucoup plus rapide sous Linux (vectorisé AVX2)
            img_od = cv2.resize(image, (od_width, od_height), interpolation=cv2.INTER_NEAREST)
            common.set_input(object_detector_tpu, img_od)
            object_detector_tpu.invoke()
            
            objs = detect.get_objects(object_detector_tpu, score_threshold=0.3)
            
            # Filtrage anticipé par slicing (complexité O(1)) pour restreindre les objets suivis
            max_results = 5
            objs = objs[:max_results]
            
            for obj in objs:
                # obj.bbox contains xmin, ymin, xmax, ymax
                o_xmin = int((obj.bbox.xmin / od_width) * width)
                o_ymin = int((obj.bbox.ymin / od_height) * height)
                o_xmax = int((obj.bbox.xmax / od_width) * width)
                o_ymax = int((obj.bbox.ymax / od_height) * height)
                
                # Clip coordinates
                o_xmin = max(0, o_xmin)
                o_ymin = max(0, o_ymin)
                o_xmax = min(width, o_xmax)
                o_ymax = min(height, o_ymax)
                
                o_width_px = o_xmax - o_xmin
                o_height_px = o_ymax - o_ymin
                o_cx = o_xmin + o_width_px // 2
                o_cy = o_ymin + o_height_px // 2
                
                current_detections.append({
                    "centroid": (o_cx, o_cy),
                    "bbox": (o_xmin, o_ymin, o_width_px, o_height_px),
                    "blendshapes": {},
                    "source_detector": "object_detector",
                    "label": f"class_{obj.id}",
                    "confidence": float(obj.score)
                })
        
        # 7. Apply Tracking and Management
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
            logging.info(f"INTERNAL_PROGRESS: {frame_idx}/{total_frames} frames ({progress_percent}%) - {video_path.name}")
            print(f"INTERNAL_PROGRESS: {frame_idx}/{total_frames} frames ({progress_percent}%) - {video_path.name}", flush=True)
            
    if total_frames:
        logging.info(f"INTERNAL_PROGRESS: {total_frames}/{total_frames} frames (100%) - {video_path.name}")
        print(f"INTERNAL_PROGRESS: {total_frames}/{total_frames} frames (100%) - {video_path.name}", flush=True)
        
    process.stdout.close()
    process.wait()
    
    return frame_idx

def _inference_process(shm_name, width, height, fps, blazeface_path, facemesh_path, blendshapes_path, object_detector_path, enable_object_detection, input_queue, output_queue, ipc_lock=None):
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - INFERENCE - %(message)s')
    logging.info("Starting _inference_process")
    import numpy as np
    import cv2
    from multiprocessing import shared_memory
    import tflite_runtime.interpreter as tflite
        
    try:
        if ipc_lock:
            ipc_lock.acquire()
            logging.info("IPC Lock acquired for PCIe initialization.")
        logging.info("Loading delegate...")
        try:
            delegate_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tmp_lib', 'usr', 'lib', 'x86_64-linux-gnu', 'libedgetpu.so.1'))
            if not os.path.exists(delegate_path):
                delegate_path = 'libedgetpu.so.1'
            delegate = tflite.load_delegate(delegate_path)
            logging.info("Delegate loaded.")
        except Exception as e:
            logging.critical(f"Delegate failed: {e}")
            raise e
        blazeface = load_tpu_model(blazeface_path, delegate)
        logging.info("BlazeFace loaded.")
        facemesh = load_tpu_model(facemesh_path, delegate)
        logging.info("FaceMesh loaded.")
        if ipc_lock:
            ipc_lock.release()
            logging.info("IPC Lock released after SRAM allocation.")
            
        blendshapes = load_tpu_model(blendshapes_path, delegate=None)
        logging.info("Blendshapes loaded.")
        
        object_detector_tpu = None
        if enable_object_detection:
            object_detector_tpu = load_tpu_model(object_detector_path, delegate=delegate)
            
        shm = shared_memory.SharedMemory(name=shm_name)
        # Ring buffer size: 8
        shared_array = np.ndarray((8, height, width, 3), dtype=np.uint8, buffer=shm.buf)
        
        from utils.one_euro_filter import OneEuroFilterND
        temporal_filter = OneEuroFilterND(dim=52, rate=fps, min_cutoff=1.0, beta=0.007)
        
        while True:
            item = input_queue.get()
            if item is None:
                output_queue.put(None)
                break
                
            frame_idx, buffer_idx, tracked_objects_metadata = item
            
            # Zero-copy read
            image = shared_array[buffer_idx]
            
            # The rest is the inference logic, similar to before
            current_detections = []
            
            if image.shape[0] != height or image.shape[1] != width:
                input_image = cv2.resize(image, (width, height), interpolation=cv2.INTER_NEAREST)
            else:
                input_image = image
                
            res = detect_face(blazeface, input_image)
            
            if res != (None, None):
                raw_bbox, eyes = res
                ymin, xmin, ymax, xmax = raw_bbox
                
                bbox_xmin = int(xmin * width)
                bbox_ymin = int(ymin * height)
                bbox_width = int((xmax - xmin) * width)
                bbox_height = int((ymax - ymin) * height)
                centroid_x = int(bbox_xmin + bbox_width / 2)
                centroid_y = int(bbox_ymin + bbox_height / 2)
                
                if eyes:
                    right_eye, left_eye = eyes
                    transform_params = face_utils.get_affine_transform(right_eye, left_eye, output_size=192)
                    face_crop_192 = face_utils.apply_affine_crop(image, transform_params)
                else:
                    face_crop_192 = cv2.resize(image, (192, 192))
                    
                landmarks = extract_landmarks(facemesh, face_crop_192)
                raw_blendshapes = extract_blendshapes(blendshapes, landmarks)
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
                    "confidence": 1.0
                })
            
            if not current_detections and object_detector_tpu:
                input_details = object_detector_tpu.get_input_details()[0]
                od_height, od_width = input_details['shape'][1:3]
                if image.shape[0] != od_height or image.shape[1] != od_width:
                    img_od = cv2.resize(image, (od_width, od_height), interpolation=cv2.INTER_NEAREST)
                else:
                    img_od = image
                    
                if input_details['dtype'] == np.float32:
                    img_od = (img_od.astype(np.float32) / 127.5) - 1.0
                    
                object_detector_tpu.tensor(input_details['index'])()[0][:, :] = img_od
                object_detector_tpu.invoke()
                
                output_details = object_detector_tpu.get_output_details()
                boxes = object_detector_tpu.get_tensor(output_details[0]['index'])[0]
                classes = object_detector_tpu.get_tensor(output_details[1]['index'])[0]
                scores = object_detector_tpu.get_tensor(output_details[2]['index'])[0]
                count = int(object_detector_tpu.get_tensor(output_details[3]['index'])[0])
                
                for i in range(min(count, 5)):
                    if scores[i] < 0.3:
                        continue
                        
                    ymin, xmin, ymax, xmax = boxes[i]
                    
                    o_xmin = max(0, int(xmin * width))
                    o_ymin = max(0, int(ymin * height))
                    o_xmax = min(width, int(xmax * width))
                    o_ymax = min(height, int(ymax * height))
                    
                    o_width_px = o_xmax - o_xmin
                    o_height_px = o_ymax - o_ymin
                    o_cx = o_xmin + o_width_px // 2
                    o_cy = o_ymin + o_height_px // 2
                    
                    current_detections.append({
                        "centroid": (o_cx, o_cy),
                        "bbox": (o_xmin, o_ymin, o_width_px, o_height_px),
                        "blendshapes": {},
                        "source_detector": "object_detector",
                        "label": f"class_{int(classes[i])}",
                        "confidence": float(scores[i])
                    })
            
            output_queue.put({
                "frame_idx": frame_idx,
                "current_detections": current_detections,
                "tracked_objects_metadata": tracked_objects_metadata # jaw open threshold etc will be done in parent
            })
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        output_queue.put(e)
    finally:
        try:
            shm.close()
        except:
            pass

def run_tracking_pipeline_multiprocessing(video_path, blazeface_path, facemesh_path, blendshapes_path, object_detector_path, enable_object_detection, width, height, fps, total_frames, speaking_detector, stream_out):
    RING_BUFFER_SIZE = 8
    frame_size = width * height * 3
    shm_size = RING_BUFFER_SIZE * frame_size
    
    shm = mp.shared_memory.SharedMemory(create=True, size=shm_size)
    shared_array = np.ndarray((RING_BUFFER_SIZE, height, width, 3), dtype=np.uint8, buffer=shm.buf)
    
    input_queue = mp.Queue(maxsize=RING_BUFFER_SIZE)
    output_queue = mp.Queue(maxsize=RING_BUFFER_SIZE)
    ipc_lock = mp.Lock()
    
    inference_proc = mp.Process(target=_inference_process, args=(
        shm.name, width, height, fps, blazeface_path, facemesh_path, blendshapes_path, object_detector_path, enable_object_detection, input_queue, output_queue, ipc_lock
    ))
    inference_proc.start()
    logging.info("Inference process spawned")
    
    # Optional FFmpeg pipe size
    # Python 3.10+ supports pipesize in Popen
    import sys
    popen_kwargs = {'stdout': subprocess.PIPE, 'stderr': subprocess.DEVNULL, 'bufsize': 10**8}
    if sys.version_info >= (3, 10):
        popen_kwargs['pipesize'] = 1048576

    command = [
        'ffmpeg', '-i', str(video_path),
        '-f', 'image2pipe',
        '-pix_fmt', 'rgb24',
        '-s', f'{width}x{height}', '-r', str(fps),
        '-vcodec', 'rawvideo', '-'
    ]
    process = subprocess.Popen(command, **popen_kwargs)
    
    active_objects = {}
    next_id_counter = {"value": 0}
    
    final_frame_count = 0
    
    import signal
    import os
    def handle_sigterm(signum, frame):
        logging.info("SIGTERM received. Terminating processes...")
        try:
            if inference_proc and inference_proc.is_alive():
                inference_proc.terminate()
            if process and process.poll() is None:
                process.terminate()
        except Exception:
            pass
        os._exit(0)
    
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    def _acquisition_thread():
        logging.info("Acquisition thread started")
        frame_idx = 0
        try:
            while True:
                raw_frame = process.stdout.read(frame_size)
                if len(raw_frame) != frame_size:
                    logging.info(f"Acquisition finished at frame {frame_idx}")
                    break
                
                buffer_idx = frame_idx % RING_BUFFER_SIZE
                # Zero-copy write
                shared_array[buffer_idx] = np.frombuffer(raw_frame, dtype=np.uint8).reshape((height, width, 3))
                
                if frame_idx % 25 == 0:
                    logging.info(f"Acquisition pushed frame {frame_idx} to queue")
                
                input_queue.put((frame_idx, buffer_idx, None))
                frame_idx += 1
            input_queue.put(None)
        except Exception as e:
            logging.error(f"Acquisition error: {e}")
            input_queue.put(None)

    acq_thread = threading.Thread(target=_acquisition_thread)
    acq_thread.start()
    
    try:
        while True:
            item = output_queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item
                
            frame_idx = item["frame_idx"]
            current_detections = item["current_detections"]
            
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
            
            final_frame_count = frame_idx + 1
            if final_frame_count % 25 == 0:
                progress_percent = int((final_frame_count / total_frames) * 100) if total_frames else 0
                logging.info(f"INTERNAL_PROGRESS: {final_frame_count}/{total_frames} frames ({progress_percent}%) - {video_path.name}")
                print(f"INTERNAL_PROGRESS: {final_frame_count}/{total_frames} frames ({progress_percent}%) - {video_path.name}", flush=True)
                
    except Exception as e:
        logging.error(f"Erreur durant l'inférence: {e}")
    finally:
        acq_thread.join()
        inference_proc.join()
        process.stdout.close()
        process.wait()
        
        shm.close()
        shm.unlink()
        
    return final_frame_count

def main():
    mp.set_start_method('spawn', force=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos_json_path", help="Chemin JSON des vidéos à traiter.")
    parser.add_argument("--out", type=str, default="tracking_output.json", help="Chemin vers le fichier de sortie JSON")
    parser.add_argument("--ndjson", action="store_true", help="Utiliser le format de sortie NDJSON")
    parser.add_argument("--sequential", action="store_true", help="Désactiver le mode multi-thread et utiliser le pipeline séquentiel")
    parser.add_argument("--device", type=str, default="TPU", choices=["CPU", "TPU"], help="Force le device à utiliser (défaut: TPU)")
    args = parser.parse_args()

    logging.info("--- Démarrage de l'analyse Tracking TPU (Cascade) ---")

    assets_dir = BASE_DIR / "assets"
    
    cocompiled_dir = assets_dir / "cocompiled"
    use_cocompiled = (
        cocompiled_dir.exists() and
        os.environ.get('STEP5_COCOMPILED_MODELS', '1') != '0'
    )
    
    if use_cocompiled:
        blazeface_path = cocompiled_dir / "blazeface_front_quantized_edgetpu.tflite"
        facemesh_path = cocompiled_dir / "facemesh_quantized_edgetpu.tflite"
        if blazeface_path.exists() and facemesh_path.exists():
            logging.info("Using co-compiled models (shared SRAM cache)")
        else:
            use_cocompiled = False
            
    if not use_cocompiled:
        blazeface_path = assets_dir / "blazeface_front_quantized_edgetpu.tflite"
        facemesh_path = assets_dir / "facemesh_quantized_edgetpu.tflite"
        logging.info("Using standard models (separate SRAM loading)")
    
    blendshapes_path = assets_dir / "face_blendshapes.tflite"
    object_detector_path = assets_dir / "detect_edgetpu.tflite"
    
    enable_object_detection = os.environ.get('STEP5_ENABLE_OBJECT_DETECTION', '0') == '1'

    if args.sequential:
        try:
            import tflite_runtime.interpreter as tflite
            delegate_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tmp_lib', 'usr', 'lib', 'x86_64-linux-gnu', 'libedgetpu.so.1'))
            if not os.path.exists(delegate_path):
                delegate_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tmp_lib', 'usr', 'lib', 'x86_64-linux-gnu', 'libedgetpu.so.1'))
            delegate = tflite.load_delegate(delegate_path)
            logging.info("Délégué Edge TPU initialisé.")
        except Exception as e:
            logging.critical(f"Impossible d'initialiser l'Edge TPU: {e}")
            sys.exit(1)
            
        blazeface = load_tpu_model(blazeface_path, delegate)
        facemesh = load_tpu_model(facemesh_path, delegate)
        blendshapes = load_tpu_model(blendshapes_path, delegate=None)
        
        object_detector_tpu = None
        if enable_object_detection:
            logging.info("Fallback object detection enabled on CPU")
            object_detector_tpu = load_tpu_model(object_detector_path, delegate=None)
    else:
        blazeface = facemesh = blendshapes = object_detector_tpu = None

    if args.videos_json_path:
        logging.info(f"Chargement des vidéos depuis le fichier temporaire: {args.videos_json_path}")
        try:
            with open(args.videos_json_path, 'r', encoding='utf-8') as f:
                video_paths = json.load(f)
            videos = [Path(p) for p in video_paths]
        except Exception as e:
            logging.error(f"Impossible de lire le fichier JSON: {e}")
            sys.exit(1)
    else:
        videos = [p for ext in VIDEO_EXTENSIONS for p in WORK_DIR.rglob(f'*{ext}')]
    total_videos = len(videos)
    
    if total_videos == 0:
        return

    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")
    print(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}", flush=True)

    successful_count = 0
    for idx, video_path in enumerate(videos):
        logging.info(f"PROCESSING_VIDEO: {video_path.name}")
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
                "engine": "blazeface_tpu",
                "tracking_method": "kdtree_tpu"
            }
            
            if args.ndjson:
                stream_out = StreamingNDJSONOutput(output_json, metadata)
            else:
                stream_out = StreamingJSONOutput(output_json, metadata)
            
            if args.sequential:
                frame_count = run_tracking_pipeline(
                    video_path, blazeface, facemesh, blendshapes, object_detector_tpu,
                    width=vid_width, height=vid_height, fps=vid_fps, total_frames=vid_total_frames,
                    speaking_detector=speaking_detector, stream_out=stream_out
                )
            else:
                frame_count = run_tracking_pipeline_multiprocessing(
                    video_path, blazeface_path, facemesh_path, blendshapes_path, object_detector_path, enable_object_detection,
                    width=vid_width, height=vid_height, fps=vid_fps, total_frames=vid_total_frames,
                    speaking_detector=speaking_detector, stream_out=stream_out
                )
            stream_out.close()
                
            logging.info(f"Succès: {output_json.name} créé avec {frame_count} frames.")
            successful_count += 1
            
        except Exception as e:
            logging.exception(f"Échec de l'analyse tracking pour {video_path.name}: {e}")

    logging.info(f"--- Analyse terminée. {successful_count}/{total_videos} réussie(s). ---")

if __name__ == "__main__":
    main()
