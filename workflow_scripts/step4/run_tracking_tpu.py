#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script d'analyse du tracking (BlazeFace -> FaceMesh -> Blendshapes) avec Google Coral Edge TPU
Version Ubuntu - Étape 5 (Alternative à MediaPipe/InsightFace CPU)
"""

import os
import sys
import json
import time
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
    from utils.media_filters import split_preserved_media
    from utils.step4_tpu_profiler import (
        StageProfiler,
        merge_reports,
        profiling_capacity,
        resolve_profile_dir,
    )
except ImportError as e:
    logging.critical(f"ERREUR: Impossible d'importer les utilitaires. Vérifiez PYTHONPATH: {e}")
    sys.exit(1)


def _now_ns() -> int:
    """Horodatage monotone (CLOCK_MONOTONIC, comparable entre processus Linux)."""
    return time.perf_counter_ns()


def _record(profiler, stage: str, start_ns: int) -> None:
    """Clôture un étage de mesure ; no-op si le profilage est désactivé."""
    if profiler is not None:
        profiler.add(stage, time.perf_counter_ns() - start_ns)


_FAST_LEVEL = None

# Niveau d'optimisation du pipeline :
#   0 = comportement historique (référence A/B)
#   1 = gains sûrs validés par benchmark (cache d'ancres, cache d'interpréteur,
#       hystérésis du détecteur d'objets, écriture JSON tamponnée)
#   2 = réservé aux optimisations structurelles (transport YUV/PyAV)
def fast_level() -> int:
    """Niveau d'optimisation demandé (lu une fois par processus)."""
    global _FAST_LEVEL
    if _FAST_LEVEL is None:
        try:
            _FAST_LEVEL = max(0, min(int(os.environ.get("STEP4_TPU_FAST", "1")), 2))
        except (TypeError, ValueError):
            _FAST_LEVEL = 1
    return _FAST_LEVEL


def object_detection_min_missing_frames() -> int:
    """Nombre de frames consécutives sans visage avant d'invoquer le détecteur d'objets.

    Chaque invocation coûte ~15 ms sur le TPU et évince la SRAM des modèles
    co-compilés BlazeFace/FaceMesh (mesuré : 6 ms/frame en moyenne sans garde-fou).
    """
    default = "25" if fast_level() >= 1 else "1"
    try:
        return max(1, int(os.environ.get("STEP4_TPU_OBJECT_DETECTION_MIN_MISSING", default)))
    except (TypeError, ValueError):
        return 25 if fast_level() >= 1 else 1


# Métadonnées d'interpréteur résolues une fois par modèle (les get_input_details()
# allouaient des dictionnaires à chaque frame).
_INTERP_META = {}

# Le stream JSON était vidé vers le disque à chaque frame (un appel write par frame) :
# on tamponne comme le chemin NDJSON.
_JSON_FLUSH_EVERY = 100 if fast_level() >= 1 else 1


def _interpreter_meta(interpreter):
    meta = _INTERP_META.get(id(interpreter))
    if meta is None:
        input_details = interpreter.get_input_details()[0]
        output_details = interpreter.get_output_details()
        shape = tuple(int(size) for size in input_details['shape'])
        meta = {
            "input_index": int(input_details['index']),
            "input_dtype": input_details['dtype'],
            "input_shape": shape,
            "input_height": shape[1] if len(shape) > 1 else None,
            "input_width": shape[2] if len(shape) > 2 else None,
            "input_tensor_factory": interpreter.tensor(input_details['index']),
            "output_indices": [int(detail['index']) for detail in output_details],
        }
        _INTERP_META[id(interpreter)] = meta
    return meta


def load_profile_json(path):
    """Charge un rapport de profilage écrit par un autre processus (best effort)."""
    try:
        with open(path, 'r', encoding='utf-8') as file_obj:
            return json.load(file_obj)
    except Exception:
        return None


def write_video_profile(profile_path, video_label, parent_profiler, acq_profiler=None, worker_profile_path=None):
    """Écrit le rapport fusionné (parent + thread d'acquisition + worker) d'une vidéo."""
    report = parent_profiler.finalize()
    report["video"] = video_label
    sources = {}
    if acq_profiler is not None:
        sources["acq"] = acq_profiler.finalize()
    if worker_profile_path is not None:
        sources["worker"] = load_profile_json(worker_profile_path)
        if sources["worker"] is not None:
            try:
                os.remove(worker_profile_path)
            except OSError:
                pass
    merge_reports(report, sources)

    profile_path = Path(profile_path)
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(profile_path, 'w', encoding='utf-8') as file_obj:
            json.dump(report, file_obj, indent=2, ensure_ascii=False)
        logging.info(f"Profil vidéo écrit: {profile_path}")
    except Exception as exc:
        logging.error(f"Écriture du profil vidéo impossible: {exc}")


def _sha256_short(path, length=12):
    """Empreinte courte d'un fichier (identifie sans ambiguïté le modèle utilisé)."""
    import hashlib
    try:
        digest = hashlib.sha256()
        with open(path, 'rb') as file_obj:
            for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()[:length]
    except Exception:
        return None


def _git_revision():
    try:
        commit = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True, cwd=str(BASE_DIR), timeout=5, check=False
        ).stdout.strip()
        dirty = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True, text=True, cwd=str(BASE_DIR), timeout=5, check=False
        ).stdout.strip()
        return {"commit": commit or None, "dirty": bool(dirty)}
    except Exception:
        return {"commit": None, "dirty": None}


def build_run_fingerprint(videos, model_paths, delegate_path, pipeline_mode, use_cocompiled):
    """Décrit le run (modèles, matériel, code) pour rendre les mesures auditables."""
    import platform

    step4_env = {key: value for key, value in os.environ.items() if key.startswith(("STEP4_", "ENABLE_CORAL_TPU"))}

    kernel_cmdline = ""
    try:
        with open('/proc/cmdline', 'r', encoding='utf-8') as file_obj:
            kernel_cmdline = file_obj.read().strip()
    except Exception:
        pass

    models = {}
    for name, path in model_paths.items():
        if path is None:
            continue
        path = Path(path)
        models[name] = {
            "path": str(path),
            "exists": path.exists(),
            "size": path.stat().st_size if path.exists() else None,
            "sha256_12": _sha256_short(path) if path.exists() else None,
        }

    try:
        import cv2 as _cv2
        cv2_version = _cv2.__version__
    except Exception:
        cv2_version = None

    try:
        import numba as _numba
        numba_version = _numba.__version__
    except Exception:
        numba_version = None

    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "pipeline_mode": pipeline_mode,
        "cocompiled_models": bool(use_cocompiled),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "numpy": np.__version__,
        "cv2": cv2_version,
        "numba": numba_version,
        "orjson": _HAS_ORJSON,
        "delegate": {"path": str(delegate_path) if delegate_path else None, "exists": Path(delegate_path).exists() if delegate_path else False},
        "models": models,
        "step4_env": step4_env,
        "git": _git_revision(),
        "apex_device": os.path.exists('/dev/apex_0'),
        "kernel_cmdline": kernel_cmdline,
        "videos": [str(path) for path in videos],
    }

VIDEO_EXTENSIONS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')

# --- Répertoire des logs ---
# Le handler est configuré dans main() et non à l'import : les processus 'spawn'
# réimportent ce module et créaient sinon un fichier tpu_tracking_*.log par processus.
LOG_DIR = BASE_DIR / "logs" / "step4"
LOG_DIR.mkdir(parents=True, exist_ok=True)

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
        if _JSON_FLUSH_EVERY <= 1 or self.count % _JSON_FLUSH_EVERY == 0:
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

def _cpu_threads() -> int:
    """Threads TFLite pour les modèles exécutés sur CPU (1 = comportement historique)."""
    try:
        return max(1, int(os.environ.get("STEP4_TPU_CPU_THREADS", "1")))
    except (TypeError, ValueError):
        return 1


def load_tpu_model(model_path: Path, delegate=None):
    """Charge un modèle TFLite sur le delegate TPU ou CPU"""
    import tflite_runtime.interpreter as tflite
    if not model_path.exists():
        logging.warning(f"Modèle manquant: {model_path}. Simulation de son exécution.")
        return None
    try:
        delegates = [delegate] if delegate else []
        # Limiter les threads si l'exécution se fait sur CPU (sans delegate) pour éviter l'oversubscription
        num_threads = _cpu_threads() if not delegate else None
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
        meta = _interpreter_meta(interpreter)
        h, w = meta['input_height'], meta['input_width']
        
        if image.shape[0] != h or image.shape[1] != w:
            input_image = cv2.resize(image, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            input_image = image
            
        if meta['input_dtype'] == np.float32:
            input_image = (input_image.astype(np.float32) / 127.5) - 1.0
            
        meta['input_tensor_factory']()[0][:, :] = input_image
        interpreter.invoke()
        
        output_indices = meta['output_indices']
        tensor_0 = interpreter.get_tensor(output_indices[0])[0]
        tensor_1 = interpreter.get_tensor(output_indices[1])[0]
        
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
        meta = _interpreter_meta(interpreter)
        h, w = meta['input_height'], meta['input_width']
        if image_crop.shape[0] != h or image_crop.shape[1] != w:
            input_image = cv2.resize(image_crop, (w, h), interpolation=cv2.INTER_LINEAR)
        else:
            input_image = image_crop
            
        if meta['input_dtype'] == np.float32:
            input_image = (input_image.astype(np.float32) / 127.5) - 1.0
            
        meta['input_tensor_factory']()[0][:, :] = input_image
        interpreter.invoke()
        
        output = interpreter.get_tensor(meta['output_indices'][0])[0].copy()
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
        
        meta = _interpreter_meta(interpreter)
        
        # 4. Formater pour le tenseur [1, 146, 2]
        input_data = input_146.reshape(meta['input_shape']).astype(meta['input_dtype'], copy=False)
        
        interpreter.set_tensor(meta['input_index'], input_data)
        interpreter.invoke()
        
        logits = interpreter.get_tensor(meta['output_indices'][0]).flatten()
        
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

def run_tracking_pipeline(video_path: Path, blazeface, facemesh, blendshapes, object_detector_tpu, width, height, fps, total_frames, speaking_detector, stream_out, profiler=None):
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

    frame_idx = 0
    
    # Tracking states
    active_objects = {}
    next_id_counter = {"value": 0}

    object_detection_min_missing = object_detection_min_missing_frames()
    frames_without_face = 0

    logging.info(f"Démarrage de la cascade TPU pour {video_path.name}")
    
    while True:
        t_stage = _now_ns()
        raw_image = process.stdout.read(frame_size)
        _record(profiler, "acq_read_pipe", t_stage)
        if len(raw_image) != frame_size:
            break

        t_frame_start = _now_ns()
        image = np.frombuffer(raw_image, dtype=np.uint8).reshape((model_height, model_width, 3))

        current_detections = []

        # 1. Détection (BlazeFace)
        # Mock: detect_face return [ymin, xmin, ymax, xmax] in normalized coordinates (0 to 1)
        t_stage = _now_ns()
        res = detect_face(blazeface, image)
        _record(profiler, "blazeface_tpu", t_stage)

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
            t_stage = _now_ns()
            if eyes:
                right_eye, left_eye = eyes
                transform_params = face_utils.get_affine_transform(right_eye, left_eye, output_size=192)
                face_crop_192 = face_utils.apply_affine_crop(image, transform_params)
            else:
                face_crop_192 = cv2.resize(image, (192, 192))
            _record(profiler, "affine_crop", t_stage)

            # 3. Landmarks (FaceMesh TPU)
            t_stage = _now_ns()
            landmarks = extract_landmarks(facemesh, face_crop_192)
            _record(profiler, "facemesh_tpu", t_stage)

            # 4. Blendshapes (CPU fallback)
            t_stage = _now_ns()
            raw_blendshapes = extract_blendshapes(blendshapes, landmarks)
            _record(profiler, "blendshapes_cpu", t_stage)

            # 5. Filtrage Temporel (One-Euro Filter @njit)
            if frame_idx == 0:
                from utils.one_euro_filter import OneEuroFilterND
                temporal_filter = OneEuroFilterND(dim=52, rate=fps, min_cutoff=1.0, beta=0.007)

            t_stage = _now_ns()
            smoothed_blendshapes = temporal_filter.update(raw_blendshapes).tolist()

            # Convert list to dict with ARKit names
            blendshapes_dict = dict(zip(
                ARKIT_52_BLENDSHAPE_NAMES,
                (float(v) for v in smoothed_blendshapes)
            ))
            _record(profiler, "one_euro", t_stage)

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
        if current_detections:
            frames_without_face = 0
        else:
            frames_without_face += 1

        if not current_detections and object_detector_tpu and frames_without_face >= object_detection_min_missing:
            t_stage = _now_ns()
            meta = _interpreter_meta(object_detector_tpu)
            od_height, od_width = meta['input_height'], meta['input_width']

            if image.shape[0] != od_height or image.shape[1] != od_width:
                img_od = cv2.resize(image, (od_width, od_height), interpolation=cv2.INTER_NEAREST)
            else:
                img_od = image

            if meta['input_dtype'] == np.float32:
                img_od = (img_od.astype(np.float32) / 127.5) - 1.0

            meta['input_tensor_factory']()[0][:, :] = img_od
            object_detector_tpu.invoke()

            output_indices = meta['output_indices']
            boxes = object_detector_tpu.get_tensor(output_indices[0])[0]
            classes = object_detector_tpu.get_tensor(output_indices[1])[0]
            scores = object_detector_tpu.get_tensor(output_indices[2])[0]
            count = int(object_detector_tpu.get_tensor(output_indices[3])[0])

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
            _record(profiler, "object_detector_tpu", t_stage)

        # 7. Apply Tracking and Management
        t_stage = _now_ns()
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
        _record(profiler, "tracking_serial", t_stage)

        t_stage = _now_ns()
        stream_out.add_frame({
            "frame": frame_idx + 1,
            "tracked_objects": tracked_objects
        })
        _record(profiler, "json_write", t_stage)
        _record(profiler, "parent_total", t_frame_start)

        if profiler is not None:
            profiler.count_frame()

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

def _inference_process(shm_name, width, height, fps, blazeface_path, facemesh_path, blendshapes_path, object_detector_path, enable_object_detection, input_queue, output_queue, ipc_lock=None, profile_path=None, video_label="", free_slots=None):
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - INFERENCE - %(message)s')
    logging.info("Starting _inference_process")
    import time
    import numpy as np
    import cv2
    from multiprocessing import shared_memory
    import tflite_runtime.interpreter as tflite

    worker_profiler = StageProfiler(video_label, profiling_capacity(None)) if profile_path else None
    if worker_profiler is not None:
        worker_profiler.start()
        logging.info(f"Profiling du worker activé: {profile_path}")
        
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

        object_detection_min_missing = object_detection_min_missing_frames()
        frames_without_face = 0
        
        while True:
            prof = worker_profiler
            if prof is not None:
                try:
                    prof.gauge("queue_fill", input_queue.qsize())
                except (NotImplementedError, OSError):
                    pass
                t_wait = _now_ns()
            item = input_queue.get()
            if item is None:
                output_queue.put(None)
                break

            t_frame_start = _now_ns()
            if prof is not None:
                prof.add("queue_wait", t_frame_start - t_wait)

            frame_idx = item[0]
            buffer_idx = item[1]
            tracked_objects_metadata = item[2]
            t_acq_ns = item[3] if len(item) > 3 else 0

            # Zero-copy read
            image = shared_array[buffer_idx]
            slot_released = False
            
            # The rest is the inference logic, similar to before
            current_detections = []
            
            if image.shape[0] != height or image.shape[1] != width:
                input_image = cv2.resize(image, (width, height), interpolation=cv2.INTER_NEAREST)
            else:
                input_image = image

            t_stage = _now_ns()
            res = detect_face(blazeface, input_image)
            _record(prof, "blazeface_tpu", t_stage)

            if res != (None, None):
                raw_bbox, eyes = res
                ymin, xmin, ymax, xmax = raw_bbox
                
                bbox_xmin = int(xmin * width)
                bbox_ymin = int(ymin * height)
                bbox_width = int((xmax - xmin) * width)
                bbox_height = int((ymax - ymin) * height)
                centroid_x = int(bbox_xmin + bbox_width / 2)
                centroid_y = int(bbox_ymin + bbox_height / 2)

                t_stage = _now_ns()
                if eyes:
                    right_eye, left_eye = eyes
                    transform_params = face_utils.get_affine_transform(right_eye, left_eye, output_size=192)
                    face_crop_192 = face_utils.apply_affine_crop(image, transform_params)
                else:
                    face_crop_192 = cv2.resize(image, (192, 192))
                _record(prof, "affine_crop", t_stage)

                # Dernier accès aux pixels de la frame (le bloc détecteur d'objets est
                # ignoré dès qu'un visage est détecté) : le slot peut être recyclé.
                if free_slots is not None:
                    free_slots.put(buffer_idx)
                    slot_released = True

                t_stage = _now_ns()
                landmarks = extract_landmarks(facemesh, face_crop_192)
                _record(prof, "facemesh_tpu", t_stage)

                t_stage = _now_ns()
                raw_blendshapes = extract_blendshapes(blendshapes, landmarks)
                _record(prof, "blendshapes_cpu", t_stage)

                t_stage = _now_ns()
                smoothed_blendshapes = temporal_filter.update(raw_blendshapes).tolist()
                
                blendshapes_dict = dict(zip(
                    ARKIT_52_BLENDSHAPE_NAMES,
                    (float(v) for v in smoothed_blendshapes)
                ))
                _record(prof, "one_euro", t_stage)
                
                current_detections.append({
                    "centroid": (centroid_x, centroid_y),
                    "bbox": (bbox_xmin, bbox_ymin, bbox_width, bbox_height),
                    "blendshapes": blendshapes_dict,
                    "source_detector": "face_landmarker",
                    "confidence": 1.0
                })
            
            if current_detections:
                frames_without_face = 0
            else:
                frames_without_face += 1

            if not current_detections and object_detector_tpu and frames_without_face >= object_detection_min_missing:
                t_stage = _now_ns()
                meta = _interpreter_meta(object_detector_tpu)
                od_height, od_width = meta['input_height'], meta['input_width']
                if image.shape[0] != od_height or image.shape[1] != od_width:
                    img_od = cv2.resize(image, (od_width, od_height), interpolation=cv2.INTER_NEAREST)
                else:
                    img_od = image
                    
                if meta['input_dtype'] == np.float32:
                    img_od = (img_od.astype(np.float32) / 127.5) - 1.0
                    
                meta['input_tensor_factory']()[0][:, :] = img_od
                object_detector_tpu.invoke()
                
                output_indices = meta['output_indices']
                boxes = object_detector_tpu.get_tensor(output_indices[0])[0]
                classes = object_detector_tpu.get_tensor(output_indices[1])[0]
                scores = object_detector_tpu.get_tensor(output_indices[2])[0]
                count = int(object_detector_tpu.get_tensor(output_indices[3])[0])
                
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
                _record(prof, "object_detector_tpu", t_stage)

            # Libération du slot SHM sur les frames sans visage : le détecteur d'objets
            # a été le dernier consommateur des pixels.
            if free_slots is not None and not slot_released:
                free_slots.put(buffer_idx)

            payload = {
                "frame_idx": frame_idx,
                "current_detections": current_detections,
                "tracked_objects_metadata": tracked_objects_metadata # jaw open threshold etc will be done in parent
            }
            if prof is not None:
                _record(prof, "worker_total", t_frame_start)
                prof.count_frame()
                payload["t_acq_ns"] = t_acq_ns
            output_queue.put(payload)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        output_queue.put(e)
    finally:
        if worker_profiler is not None:
            try:
                worker_profiler.stop()
                worker_profiler.write(Path(profile_path))
                logging.info(f"Profil worker écrit: {profile_path}")
            except Exception as exc:
                logging.error(f"Écriture du profil worker impossible: {exc}")
        try:
            shm.close()
        except:
            pass

def run_tracking_pipeline_multiprocessing(video_path, blazeface_path, facemesh_path, blendshapes_path, object_detector_path, enable_object_detection, width, height, fps, total_frames, speaking_detector, stream_out, profile_path=None, video_label=""):
    RING_BUFFER_SIZE = 8
    frame_size = width * height * 3
    shm_size = RING_BUFFER_SIZE * frame_size

    parent_profiler = None
    acq_profiler = None
    worker_profile_path = None
    if profile_path is not None:
        capacity = profiling_capacity(total_frames)
        parent_profiler = StageProfiler(f"{video_label}:parent", capacity)
        acq_profiler = StageProfiler(f"{video_label}:acq", capacity)
        worker_profile_path = Path(profile_path).with_suffix(".worker.json")

    shm = mp.shared_memory.SharedMemory(create=True, size=shm_size)
    shared_array = np.ndarray((RING_BUFFER_SIZE, height, width, 3), dtype=np.uint8, buffer=shm.buf)
    
    input_queue = mp.Queue(maxsize=RING_BUFFER_SIZE)
    output_queue = mp.Queue(maxsize=RING_BUFFER_SIZE)
    ipc_lock = mp.Lock()

    # Protocole de jetons : un slot ne peut être réécrit par l'acquisition qu'une fois
    # libéré par le worker (sinon le worker lisait une zone en cours d'écrasement, ce qui
    # rendait les sorties non déterministes d'un run à l'autre).
    free_slots = None
    if fast_level() >= 1:
        free_slots = mp.Queue(maxsize=RING_BUFFER_SIZE)
        for slot_index in range(RING_BUFFER_SIZE):
            free_slots.put(slot_index)

    inference_proc = mp.Process(target=_inference_process, args=(
        shm.name, width, height, fps, blazeface_path, facemesh_path, blendshapes_path, object_detector_path, enable_object_detection, input_queue, output_queue, ipc_lock, worker_profile_path, video_label, free_slots
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
                t_stage = _now_ns()
                raw_frame = process.stdout.read(frame_size)
                _record(acq_profiler, "acq_read_pipe", t_stage)
                if len(raw_frame) != frame_size:
                    logging.info(f"Acquisition finished at frame {frame_idx}")
                    break

                buffer_idx = free_slots.get() if free_slots is not None else frame_idx % RING_BUFFER_SIZE
                # Zero-copy write
                t_stage = _now_ns()
                shared_array[buffer_idx] = np.frombuffer(raw_frame, dtype=np.uint8).reshape((height, width, 3))
                _record(acq_profiler, "acq_shm_write", t_stage)

                if frame_idx % 25 == 0:
                    logging.info(f"Acquisition pushed frame {frame_idx} to queue")

                t_stage = _now_ns()
                if acq_profiler is not None:
                    input_queue.put((frame_idx, buffer_idx, None, _now_ns()))
                else:
                    input_queue.put((frame_idx, buffer_idx, None))
                _record(acq_profiler, "acq_push", t_stage)
                if acq_profiler is not None:
                    acq_profiler.count_frame()
                frame_idx += 1
            input_queue.put(None)
        except Exception as e:
            logging.error(f"Acquisition error: {e}")
            input_queue.put(None)

    acq_thread = threading.Thread(target=_acquisition_thread)
    if parent_profiler is not None:
        parent_profiler.start()
    acq_thread.start()
    
    try:
        while True:
            item = output_queue.get()
            if item is None:
                break
            if isinstance(item, Exception):
                raise item

            t_frame_start = _now_ns()
            frame_idx = item["frame_idx"]
            current_detections = item["current_detections"]

            t_stage = _now_ns()
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
            _record(parent_profiler, "tracking_serial", t_stage)

            t_stage = _now_ns()
            stream_out.add_frame({
                "frame": frame_idx + 1,
                "tracked_objects": tracked_objects
            })
            _record(parent_profiler, "json_write", t_stage)

            if parent_profiler is not None:
                parent_profiler.gauge("active_objects", len(active_objects))
                t_acq_ns = item.get("t_acq_ns") or 0
                if t_acq_ns:
                    parent_profiler.add("e2e_frame", _now_ns() - t_acq_ns)
                parent_profiler.add("parent_total", _now_ns() - t_frame_start)
                parent_profiler.count_frame()

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

        if parent_profiler is not None:
            parent_profiler.stop()
            write_video_profile(profile_path, video_label, parent_profiler, acq_profiler, worker_profile_path)

    return final_frame_count

def main():
    mp.set_start_method('spawn', force=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos_json_path", help="Chemin JSON des vidéos à traiter.")
    parser.add_argument("--out", type=str, default="tracking_output.json", help="Chemin vers le fichier de sortie JSON")
    parser.add_argument("--ndjson", action="store_true", help="Utiliser le format de sortie NDJSON")
    parser.add_argument("--sequential", action="store_true", help="Désactiver le mode multi-thread et utiliser le pipeline séquentiel")
    parser.add_argument("--device", type=str, default="TPU", choices=["CPU", "TPU"], help="Force le device à utiliser (défaut: TPU)")
    parser.add_argument("--profile-dir", type=str, default=None, help="Répertoire des rapports de profilage par étage (active le benchmark)")
    args = parser.parse_args()

    log_file = LOG_DIR / f"tpu_tracking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.info("--- Démarrage de l'analyse Tracking TPU (Cascade) ---")

    profile_dir = resolve_profile_dir(args.profile_dir)
    if profile_dir is not None:
        profile_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Profilage par étage activé: {profile_dir}")
    
    assets_dir = BASE_DIR / "assets"
    
    cocompiled_dir = assets_dir / "cocompiled"
    use_cocompiled = (
        cocompiled_dir.exists() and
        os.environ.get('STEP4_COCOMPILED_MODELS', '1') != '0'
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
    
    enable_object_detection = os.environ.get('STEP4_ENABLE_OBJECT_DETECTION', '0') == '1'

    delegate_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'tmp_lib', 'usr', 'lib', 'x86_64-linux-gnu', 'libedgetpu.so.1'))
    if not os.path.exists(delegate_path):
        delegate_path = 'libedgetpu.so.1'

    if args.sequential:
        try:
            import tflite_runtime.interpreter as tflite
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

        if profile_dir is not None and any(model is None for model in (blazeface, facemesh, blendshapes)):
            logging.critical(
                "Profilage annulé: un modèle est indisponible (interpréteur None) — le pipeline tournerait en simulation."
            )
            sys.exit(2)
    else:
        blazeface = facemesh = blendshapes = object_detector_tpu = None

        if profile_dir is not None:
            missing_models = [
                str(path) for path in (blazeface_path, facemesh_path, blendshapes_path)
                if not Path(path).exists()
            ]
            if missing_models:
                logging.critical(
                    "Profilage annulé: modèle(s) manquant(s) %s — le pipeline tournerait en simulation.",
                    ", ".join(missing_models)
                )
                sys.exit(2)

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

        # Scan de secours : écarter les logos .mov préservés (alpha conservé pour l'étape 8)
        videos, preserved_logos = split_preserved_media(videos)
        if preserved_logos:
            logging.info(
                f"{len(preserved_logos)} .mov logo(s) préservé(s) ignoré(s) par le tracking (alpha conservé pour l'étape 8)."
            )
    total_videos = len(videos)
    
    if total_videos == 0:
        return

    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")
    print(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}", flush=True)

    if profile_dir is not None:
        try:
            fingerprint = build_run_fingerprint(
                videos,
                model_paths={
                    "blazeface": blazeface_path,
                    "facemesh": facemesh_path,
                    "blendshapes": blendshapes_path,
                    "object_detector": object_detector_path if enable_object_detection else None,
                },
                delegate_path=delegate_path,
                pipeline_mode="sequential" if args.sequential else "multiprocessing",
                use_cocompiled=use_cocompiled,
            )
            fingerprint_path = profile_dir / "run_fingerprint.json"
            with open(fingerprint_path, 'w', encoding='utf-8') as file_obj:
                json.dump(fingerprint, file_obj, indent=2, ensure_ascii=False)
            logging.info(f"Fingerprint du run écrit: {fingerprint_path}")
        except Exception as exc:
            logging.error(f"Fingerprint du run impossible: {exc}")

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

            video_profile_path = profile_dir / f"{video_path.stem}.json" if profile_dir is not None else None

            if args.sequential:
                sequential_profiler = None
                if video_profile_path is not None:
                    sequential_profiler = StageProfiler(video_path.stem, profiling_capacity(vid_total_frames))
                    sequential_profiler.start()
                frame_count = run_tracking_pipeline(
                    video_path, blazeface, facemesh, blendshapes, object_detector_tpu,
                    width=vid_width, height=vid_height, fps=vid_fps, total_frames=vid_total_frames,
                    speaking_detector=speaking_detector, stream_out=stream_out,
                    profiler=sequential_profiler
                )
                if sequential_profiler is not None:
                    sequential_profiler.stop()
                    write_video_profile(video_profile_path, video_path.stem, sequential_profiler)
            else:
                frame_count = run_tracking_pipeline_multiprocessing(
                    video_path, blazeface_path, facemesh_path, blendshapes_path, object_detector_path, enable_object_detection,
                    width=vid_width, height=vid_height, fps=vid_fps, total_frames=vid_total_frames,
                    speaking_detector=speaking_detector, stream_out=stream_out,
                    profile_path=video_profile_path, video_label=video_path.stem
                )
            stream_out.close()
                
            logging.info(f"Succès: {output_json.name} créé avec {frame_count} frames.")
            successful_count += 1
            
        except Exception as e:
            logging.exception(f"Échec de l'analyse tracking pour {video_path.name}: {e}")

    logging.info(f"--- Analyse terminée. {successful_count}/{total_videos} réussie(s). ---")

if __name__ == "__main__":
    main()
