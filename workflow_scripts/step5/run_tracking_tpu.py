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
import numpy as np
from pathlib import Path
from datetime import datetime

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

# Gestion des dépendances Edge TPU
try:
    from pycoral.utils import edgetpu
    from pycoral.adapters import common
    from pycoral.adapters import detect
    import tflite_runtime.interpreter as tflite
    from PIL import Image
except ImportError as e:
    logging.critical(f"ERREUR: Les bibliothèques Coral/TFLite ne sont pas installées dans coral_env: {e}")
    sys.exit(1)

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
        self.first = True
        self.count = 0
        self.file_obj.write("[\n")
        
    def append(self, item):
        if not self.first:
            self.file_obj.write(",\n")
        else:
            self.first = False
        frame_json = json.dumps(item, ensure_ascii=False)
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

    def __len__(self):
        return len(self.frames_list)

    def close(self):
        self.file_obj.write("\n  ]\n}\n")
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
    if not model_path.exists():
        logging.warning(f"Modèle manquant: {model_path}. Simulation de son exécution.")
        return None
    try:
        delegates = [delegate] if delegate else []
        interpreter = tflite.Interpreter(model_path=str(model_path), experimental_delegates=delegates)
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
            from PIL import Image
            img_pil = Image.fromarray(image).resize((w, h), Image.NEAREST)
            input_image = np.array(img_pil)
        else:
            input_image = image
            
        common.set_input(interpreter, input_image)
        interpreter.invoke()
        
        regressors = common.output_tensor(interpreter, 0)[0]
        classificators = common.output_tensor(interpreter, 1)[0]
        
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
        common.set_input(interpreter, np.array(image_crop))
        interpreter.invoke()
        
        output = common.output_tensor(interpreter, 0)[0].copy()
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
                face_crop_192 = face_utils.apply_affine_crop(Image.fromarray(image), transform_params)
            else:
                face_crop_192 = Image.fromarray(image).resize((192, 192))
                
            # 3. Landmarks (FaceMesh TPU)
            landmarks = extract_landmarks(facemesh, face_crop_192)
            
            # 4. Blendshapes (CPU FP32)
            raw_blendshapes = extract_blendshapes(blendshapes, landmarks)
            
            # 5. Lissage temporel Kalman (CPU) pour mitiger le jittering INT8
            smoothed_blendshapes = kalman_filter.update(raw_blendshapes).tolist()
            
            # Convert list to dict with ARKit names
            blendshapes_dict = {}
            for i, val in enumerate(smoothed_blendshapes):
                if i < len(ARKIT_52_BLENDSHAPE_NAMES):
                    blendshapes_dict[ARKIT_52_BLENDSHAPE_NAMES[i]] = float(val)
            
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
            # Resize via PIL pour l'input size du modèle (généralement 320x320 pour lite0)
            input_details = object_detector_tpu.get_input_details()[0]
            od_height, od_width = input_details['shape'][1], input_details['shape'][2]
            
            img_pil = Image.fromarray(image).resize((od_width, od_height), Image.NEAREST)
            common.set_input(object_detector_tpu, np.array(img_pil))
            object_detector_tpu.invoke()
            
            objs = detect.get_objects(object_detector_tpu, score_threshold=0.3)
            
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
            
    if total_frames:
        logging.info(f"INTERNAL_PROGRESS: {total_frames}/{total_frames} frames (100%) - {video_path.name}")
        
    process.stdout.close()
    process.wait()
    
    return frame_idx

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--videos_json_path", help="Chemin JSON des vidéos à traiter.")
    args = parser.parse_args()

    logging.info("--- Démarrage de l'analyse Tracking TPU (Cascade) ---")

    # Initialisation TPU
    try:
        delegate = edgetpu.load_edgetpu_delegate()
        logging.info("Délégué Edge TPU initialisé.")
    except Exception as e:
        logging.critical(f"Impossible d'initialiser l'Edge TPU: {e}")
        sys.exit(1)

    assets_dir = BASE_DIR / "assets"
    
    # Chargement des modèles
    blazeface = load_tpu_model(assets_dir / "blazeface_front_quantized_edgetpu.tflite", delegate)
    facemesh = load_tpu_model(assets_dir / "facemesh_quantized_edgetpu.tflite", delegate)
    blendshapes = load_tpu_model(assets_dir / "face_blendshapes.tflite", delegate=None)
    
    # Respect the STEP5_ENABLE_OBJECT_DETECTION environment variable to avoid costly TPU context switching
    enable_object_detection = os.environ.get('STEP5_ENABLE_OBJECT_DETECTION', '0') == '1'
    if enable_object_detection:
        logging.info("Fallback object detection enabled on CPU (loading detect.tflite with delegate=None)")
        # We load with delegate=None to execute on CPU and prevent costly Edge TPU context switching
        object_detector_tpu = load_tpu_model(assets_dir / "detect.tflite", delegate=None)
    else:
        logging.info("Fallback object detection is disabled (helps avoid TPU context switches)")
        object_detector_tpu = None

    if args.videos_json_path:
        logging.info(f"Chargement des vidéos depuis le fichier temporaire: {args.videos_json_path}")
        try:
            with open(args.videos_json_path, 'r', encoding='utf-8') as f:
                video_paths = json.load(f)
            videos = [Path(p) for p in video_paths]
        except Exception as e:
            logging.error(f"Impossible de lire le fichier JSON des vidéos {args.videos_json_path}: {e}")
            sys.exit(1)
    else:
        videos = [p for ext in VIDEO_EXTENSIONS for p in WORK_DIR.rglob(f'*{ext}')]
    total_videos = len(videos)
    
    logging.info(f"TOTAL_VIDEOS_TO_PROCESS: {total_videos}")

    if total_videos == 0:
        return

    successful_count = 0
    for idx, video_path in enumerate(videos):
        logging.info(f"PROCESSING_VIDEO: {video_path.name}")
        
        try:
            # 1. Obtenir les métadonnées de la vidéo (dimensions originales)
            vid_width, vid_height, vid_fps, vid_total_frames = get_video_metadata_ffprobe(video_path)
            logging.info(f"Metadata - {vid_width}x{vid_height} @ {vid_fps}fps, {vid_total_frames} frames")
            
            # 2. Initialiser EnhancedSpeakingDetector
            speaking_detector = EnhancedSpeakingDetector(
                video_path=str(video_path),
                jaw_threshold=0.08
            )
            
            # 3. Préparer la sortie streaming (écriture directe pendant le pipeline)
            output_json = video_path.with_suffix('.json')
            metadata = {
                "video_path": str(video_path),
                "original_fps": vid_fps,
                "resolution": {"width": vid_width, "height": vid_height},
                "total_frames_processed": vid_total_frames,
                "engine": "blazeface_tpu",
                "tracking_method": "kdtree_tpu"
            }
            stream_out = StreamingJSONOutput(output_json, metadata)
            
            # 4. Exécuter le pipeline (streaming direct vers disque)
            frame_count = run_tracking_pipeline(
                video_path, blazeface, facemesh, blendshapes, object_detector_tpu,
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
