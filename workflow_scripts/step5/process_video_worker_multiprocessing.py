#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced CPU Worker with Multiprocessing Optimization
Combines proven techniques from backup implementations for maximum CPU performance.
"""

import os
import sys
import json
import argparse
import logging
import cv2
import numpy as np
try:
    import mediapipe as mp
except Exception:
    mp = None
import multiprocessing as mp_proc
import time
import math
from pathlib import Path
from functools import partial
from concurrent.futures import ProcessPoolExecutor, as_completed

# Load .env file before anything else (critical for multiprocessing workers)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass  # dotenv not available, rely on system env vars

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from utils.tracking_optimizations import apply_tracking_and_management
from utils.resource_manager import safe_video_processing, get_video_metadata, resource_tracker
from utils.enhanced_speaking_detection import EnhancedSpeakingDetector
from object_detector_registry import ObjectDetectorRegistry

# Configuration du logger
log_dir = Path(__file__).resolve().parent.parent.parent / "logs" / "step5"
log_dir.mkdir(parents=True, exist_ok=True)
worker_type_str = "CPU_MP" if "--mp_num_workers_internal" in sys.argv else "CPU"
video_name_for_log = Path(sys.argv[1]).stem if len(sys.argv) > 1 else "unknown"
log_file = log_dir / f"worker_{worker_type_str}_{video_name_for_log}_{os.getpid()}.log"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s',
                    handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler(sys.stdout)])


def _parse_optional_positive_int(raw):
    if raw is None:
        return None
    raw_str = str(raw).strip()
    if not raw_str:
        return None
    try:
        value = int(raw_str)
    except Exception:
        return None
    if value <= 0:
        return None
    return value


def _is_truthy_env(raw):
    if raw is None:
        return False
    return str(raw).strip().lower() in {"1", "true", "yes"}


def _apply_jawopen_scale(blendshapes, scale):
    if not blendshapes or not isinstance(blendshapes, dict):
        return blendshapes
    try:
        jaw_open_raw = blendshapes.get("jawOpen")
        if jaw_open_raw is None:
            return blendshapes
        jaw_open_scaled = float(jaw_open_raw) * float(scale)
        jaw_open_scaled = float(np.clip(jaw_open_scaled, 0.0, 1.0))
        out = dict(blendshapes)
        out["jawOpen"] = jaw_open_scaled
        return out
    except Exception:
        return blendshapes


# Global variables for worker processes
landmarker_global = None
object_detector_global = None
face_engine_global = None
tracking_engine_type = None


def init_worker_process(models_dir, args_dict):
    """
    Initialize tracking models once per worker process.
    Supports MediaPipe and OpenCV-based engines.
    """
    global landmarker_global, object_detector_global, face_engine_global, tracking_engine_type
    
    worker_pid = os.getpid()
    engine_name = args_dict.get('tracking_engine', '')
    engine_norm = (str(engine_name).strip().lower() if engine_name else "")
    
    logging.info(f"[WORKER-{worker_pid}] Initializing process with engine: {engine_norm or 'mediapipe'}")
    
    try:
        if engine_norm and engine_norm not in {"mediapipe", "mediapipe_landmarker"}:
            # Inject env vars for OpenCV engines (not inherited from parent process)
            if args_dict.get('yunet_model_path'):
                os.environ['STEP5_YUNET_MODEL_PATH'] = args_dict['yunet_model_path']
            if args_dict.get('eos_models_dir'):
                os.environ['STEP5_EOS_MODELS_DIR'] = str(args_dict['eos_models_dir'])
            if args_dict.get('eos_sfm_model_path'):
                os.environ['STEP5_EOS_SFM_MODEL_PATH'] = str(args_dict['eos_sfm_model_path'])
            if args_dict.get('eos_expression_blendshapes_path'):
                os.environ['STEP5_EOS_EXPRESSION_BLENDSHAPES_PATH'] = str(args_dict['eos_expression_blendshapes_path'])
            if args_dict.get('eos_landmark_mapper_path'):
                os.environ['STEP5_EOS_LANDMARK_MAPPER_PATH'] = str(args_dict['eos_landmark_mapper_path'])
            if args_dict.get('eos_edge_topology_path'):
                os.environ['STEP5_EOS_EDGE_TOPOLOGY_PATH'] = str(args_dict['eos_edge_topology_path'])
            if args_dict.get('eos_model_contour_path'):
                os.environ['STEP5_EOS_MODEL_CONTOUR_PATH'] = str(args_dict['eos_model_contour_path'])
            if args_dict.get('eos_contour_landmarks_path'):
                os.environ['STEP5_EOS_CONTOUR_LANDMARKS_PATH'] = str(args_dict['eos_contour_landmarks_path'])
            if args_dict.get('eos_fit_every_n') is not None:
                os.environ['STEP5_EOS_FIT_EVERY_N'] = str(args_dict['eos_fit_every_n'])
            if args_dict.get('eos_max_faces') is not None:
                os.environ['STEP5_EOS_MAX_FACES'] = str(args_dict['eos_max_faces'])
            if args_dict.get('eos_max_width') is not None:
                os.environ['STEP5_EOS_MAX_WIDTH'] = str(args_dict['eos_max_width'])
            if args_dict.get('eos_jawopen_scale') is not None:
                os.environ['STEP5_EOS_JAWOPEN_SCALE'] = str(args_dict['eos_jawopen_scale'])
            if args_dict.get('opencv_max_faces') is not None:
                os.environ['STEP5_OPENCV_MAX_FACES'] = str(args_dict['opencv_max_faces'])
            if args_dict.get('opencv_jawopen_scale') is not None:
                os.environ['STEP5_OPENCV_JAWOPEN_SCALE'] = str(args_dict['opencv_jawopen_scale'])
            if args_dict.get('facemesh_onnx_path'):
                os.environ['STEP5_FACEMESH_ONNX_PATH'] = args_dict['facemesh_onnx_path']
            if args_dict.get('pyfeat_model_path'):
                os.environ['STEP5_PYFEAT_MODEL_PATH'] = args_dict['pyfeat_model_path']
            if args_dict.get('step5_onnx_intra_op_threads'):
                os.environ['STEP5_ONNX_INTRA_OP_THREADS'] = str(args_dict['step5_onnx_intra_op_threads'])
            if args_dict.get('step5_onnx_inter_op_threads'):
                os.environ['STEP5_ONNX_INTER_OP_THREADS'] = str(args_dict['step5_onnx_inter_op_threads'])
            if args_dict.get('openseeface_models_dir'):
                os.environ['STEP5_OPENSEEFACE_MODELS_DIR'] = str(args_dict['openseeface_models_dir'])
            if args_dict.get('openseeface_model_id') is not None:
                os.environ['STEP5_OPENSEEFACE_MODEL_ID'] = str(args_dict['openseeface_model_id'])
            if args_dict.get('openseeface_detection_model_path'):
                os.environ['STEP5_OPENSEEFACE_DETECTION_MODEL_PATH'] = str(args_dict['openseeface_detection_model_path'])
            if args_dict.get('openseeface_landmark_model_path'):
                os.environ['STEP5_OPENSEEFACE_LANDMARK_MODEL_PATH'] = str(args_dict['openseeface_landmark_model_path'])
            if args_dict.get('openseeface_detect_every_n') is not None:
                os.environ['STEP5_OPENSEEFACE_DETECT_EVERY_N'] = str(args_dict['openseeface_detect_every_n'])
            if args_dict.get('openseeface_detection_threshold') is not None:
                os.environ['STEP5_OPENSEEFACE_DETECTION_THRESHOLD'] = str(args_dict['openseeface_detection_threshold'])
            if args_dict.get('openseeface_max_faces') is not None:
                os.environ['STEP5_OPENSEEFACE_MAX_FACES'] = str(args_dict['openseeface_max_faces'])
            if args_dict.get('openseeface_jawopen_scale') is not None:
                os.environ['STEP5_OPENSEEFACE_JAWOPEN_SCALE'] = str(args_dict['openseeface_jawopen_scale'])
            if args_dict.get('object_detector_model'):
                os.environ['STEP5_OBJECT_DETECTOR_MODEL'] = args_dict['object_detector_model']
            if args_dict.get('object_detector_model_path'):
                os.environ['STEP5_OBJECT_DETECTOR_MODEL_PATH'] = args_dict['object_detector_model_path']
            
            
            # Ensure profiling / throttling hints reach OpenCV-based engines
            profiling_enabled = bool(args_dict.get('enable_profiling'))
            os.environ['STEP5_ENABLE_PROFILING'] = "1" if profiling_enabled else "0"

            throttle_raw = args_dict.get('blendshapes_throttle_n', 1)
            try:
                throttle_value = str(max(1, int(throttle_raw or 1)))
            except Exception:
                throttle_value = "1"
            os.environ['STEP5_BLENDSHAPES_THROTTLE_N'] = throttle_value
            
            if engine_norm == "openseeface":
                logging.info(
                    f"[WORKER-{worker_pid}] OpenSeeFace config: "
                    f"model_id={os.environ.get('STEP5_OPENSEEFACE_MODEL_ID')} "
                    f"models_dir={os.environ.get('STEP5_OPENSEEFACE_MODELS_DIR')} "
                    f"detection_model_path={os.environ.get('STEP5_OPENSEEFACE_DETECTION_MODEL_PATH')} "
                    f"landmark_model_path={os.environ.get('STEP5_OPENSEEFACE_LANDMARK_MODEL_PATH')} "
                    f"detect_every_n={os.environ.get('STEP5_OPENSEEFACE_DETECT_EVERY_N')} "
                    f"detection_threshold={os.environ.get('STEP5_OPENSEEFACE_DETECTION_THRESHOLD')} "
                    f"max_faces={os.environ.get('STEP5_OPENSEEFACE_MAX_FACES')} "
                    f"jawopen_scale={os.environ.get('STEP5_OPENSEEFACE_JAWOPEN_SCALE')} "
                    f"max_width={os.environ.get('STEP5_OPENSEEFACE_MAX_WIDTH') or os.environ.get('STEP5_YUNET_MAX_WIDTH')}"
                )

            from face_engines import create_face_engine
            use_gpu = args_dict.get('use_gpu', False)
            face_engine_global = create_face_engine(engine_norm, use_gpu=use_gpu)

            if args_dict.get('enable_object_detection', False):
                try:
                    if mp is None:
                        raise RuntimeError("mediapipe is not available")

                    BaseOptions = mp.tasks.BaseOptions
                    VisionRunningMode = mp.tasks.vision.RunningMode
                    ObjectDetector = mp.tasks.vision.ObjectDetector
                    ObjectDetectorOptions = mp.tasks.vision.ObjectDetectorOptions

                    delegate = BaseOptions.Delegate.CPU

                    object_detector_model_name = args_dict.get('object_detector_model', 'efficientdet_lite2')
                    object_model_path = ObjectDetectorRegistry.resolve_model_path(
                        model_name=object_detector_model_name,
                        models_dir=models_dir,
                        override_path=args_dict.get('object_detector_model_path'),
                    )
                    logging.info(
                        f"[WORKER-{worker_pid}] Using object detector (face_engine mode): "
                        f"{object_detector_model_name} at {object_model_path}"
                    )

                    object_options = ObjectDetectorOptions(
                        base_options=BaseOptions(model_asset_path=str(object_model_path), delegate=delegate),
                        running_mode=VisionRunningMode.VIDEO,
                        max_results=args_dict.get('object_max_results', 5),
                        score_threshold=args_dict.get('object_score_threshold', 0.4),
                    )
                    object_detector_global = ObjectDetector.create_from_options(object_options)
                except Exception as e:
                    logging.error(
                        f"[WORKER-{worker_pid}] Failed to initialize object detector (face_engine mode): {e}"
                    )
                    object_detector_global = None

            tracking_engine_type = "face_engine"
            logging.info(f"[WORKER-{worker_pid}] Initialized {engine_norm} engine")
        else:
            if mp is None:
                raise RuntimeError(
                    "mediapipe is required for the default tracking engine but is not available in this environment"
                )

            BaseOptions = mp.tasks.BaseOptions
            VisionRunningMode = mp.tasks.vision.RunningMode
            FaceLandmarker = mp.tasks.vision.FaceLandmarker
            FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
            ObjectDetector = mp.tasks.vision.ObjectDetector
            ObjectDetectorOptions = mp.tasks.vision.ObjectDetectorOptions
            
            # Configure delegate (CPU or GPU)
            use_gpu = args_dict.get('use_gpu', False)
            if use_gpu:
                try:
                    # Attempt to use GPU delegate for MediaPipe
                    delegate = BaseOptions.Delegate.GPU
                    logging.info(f"[WORKER-{worker_pid}] Attempting to use GPU delegate for MediaPipe")
                except AttributeError:
                    logging.warning(f"[WORKER-{worker_pid}] GPU delegate not available in MediaPipe, falling back to CPU")
                    delegate = BaseOptions.Delegate.CPU
            else:
                delegate = BaseOptions.Delegate.CPU
            face_model_candidates = [
                models_dir / "face_detectors" / "mediapipe" / "face_landmarker_v2_with_blendshapes.task",
                models_dir / "face_landmarker_v2_with_blendshapes.task",
            ]
            face_model_path = next((p for p in face_model_candidates if p.exists()), face_model_candidates[0])
            
            # Resolve object detector model using registry
            object_detector_model_name = args_dict.get('object_detector_model', 'efficientdet_lite2')
            try:
                object_model_path = ObjectDetectorRegistry.resolve_model_path(
                    model_name=object_detector_model_name,
                    models_dir=models_dir,
                    override_path=args_dict.get('object_detector_model_path')
                )
                logging.info(f"[WORKER-{worker_pid}] Using object detector: {object_detector_model_name} at {object_model_path}")
            except (ValueError, FileNotFoundError) as e:
                logging.error(f"[WORKER-{worker_pid}] Failed to resolve object detector model: {e}")
                raise
            
            env_max_faces = _parse_optional_positive_int(args_dict.get('mediapipe_max_faces'))
            num_faces = int(env_max_faces if env_max_faces is not None else (args_dict.get('mp_landmarker_num_faces', 5) or 5))

            face_options = FaceLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(face_model_path), delegate=delegate),
                running_mode=VisionRunningMode.VIDEO,
                num_faces=num_faces,
                min_face_detection_confidence=args_dict.get('mp_landmarker_min_face_detection_confidence', 0.3),
                min_face_presence_confidence=args_dict.get('mp_landmarker_min_face_presence_confidence', 0.2),
                min_tracking_confidence=args_dict.get('mp_landmarker_min_tracking_confidence', 0.3),
                output_face_blendshapes=True
            )
            
            object_options = ObjectDetectorOptions(
                base_options=BaseOptions(model_asset_path=str(object_model_path), delegate=delegate),
                running_mode=VisionRunningMode.VIDEO,
                max_results=args_dict.get('object_max_results', 5),
                score_threshold=args_dict.get('object_score_threshold', 0.4)
            )
            
            landmarker_global = FaceLandmarker.create_from_options(face_options)
            object_detector_global = ObjectDetector.create_from_options(object_options)
            tracking_engine_type = "mediapipe"
            logging.info(f"[WORKER-{worker_pid}] Initialized MediaPipe engine")
        
        logging.info(f"[WORKER-{worker_pid}] Initialization complete")
        
    except Exception as e:
        logging.error(f"[WORKER-{worker_pid}] Initialization failed: {e}")
        landmarker_global = None
        object_detector_global = None
        face_engine_global = None


def process_frame_chunk(chunk_data):
    """
    Process a chunk of frames using the initialized models.
    Returns detection results for all frames in the chunk.
    """
    global landmarker_global, object_detector_global, face_engine_global, tracking_engine_type
    
    worker_pid = os.getpid()
    
    if tracking_engine_type == "face_engine":
        if not face_engine_global:
            logging.error(f"[WORKER-{worker_pid}] Face engine not properly initialized")
            return []
    elif tracking_engine_type == "mediapipe":
        if not landmarker_global:
            logging.error(f"[WORKER-{worker_pid}] MediaPipe not properly initialized")
            return []
    else:
        logging.error(f"[WORKER-{worker_pid}] No tracking engine initialized")
        return []
    
    chunk_start, chunk_end, video_path, args_dict = chunk_data
    results = []
    
    try:
        logging.info(f"[WORKER-{worker_pid}] Processing chunk [{chunk_start}, {chunk_end}] ({chunk_end - chunk_start + 1} frames)")

        enable_profiling = bool(args_dict.get('enable_profiling'))
        profiling_stats = {
            "to_rgb_total": 0.0,
            "detect_total": 0.0,
            "post_total": 0.0,
            "frame_count": 0,
        }
        blendshapes_throttle_n = max(1, int(args_dict.get('blendshapes_throttle_n', 1) or 1))
        jaw_open_scale = float(args_dict.get('mediapipe_jawopen_scale', 1.0) or 1.0)
        max_width = _parse_optional_positive_int(args_dict.get('mediapipe_max_width'))
        blendshapes_cache = {}
        
        # Open video capture for this chunk
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logging.error(f"[WORKER-{worker_pid}] Failed to open video: {video_path}")
            return []
        
        cap.read()
        cap.set(cv2.CAP_PROP_POS_FRAMES, chunk_start)
        
        frames_processed = 0
        for frame_idx in range(chunk_start, chunk_end + 1):
            frames_processed += 1
            
            # Log progression every 10 frames
            if frames_processed % 10 == 0:
                logging.debug(f"[WORKER-{worker_pid}] Chunk [{chunk_start}, {chunk_end}]: processed {frames_processed}/{chunk_end - chunk_start + 1} frames")
            if enable_profiling:
                profiling_stats["frame_count"] += 1
            ret, frame = cap.read()
            if not ret:
                try:
                    cap.release()
                except Exception:
                    pass

                cap = cv2.VideoCapture(video_path)
                if cap.isOpened():
                    cap.read()
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()

                    if (not ret) and frame_idx > 0:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx - 1)
                        cap.read()
                        ret, frame = cap.read()

                    if (not ret) and args_dict.get('fps'):
                        try:
                            cap.set(
                                cv2.CAP_PROP_POS_MSEC,
                                int(frame_idx * 1000 / float(args_dict.get('fps', 25))),
                            )
                            ret, frame = cap.read()
                        except Exception:
                            pass

                if not ret:
                    # Tolerate last frame read failures (common with certain codecs)
                    if frame_idx >= args_dict.get('total_frames', 0) - 1:
                        logging.debug(
                            f"Skipping unreadable frame {frame_idx} (near end of video) "
                            f"for chunk [{chunk_start}, {chunk_end}] in {Path(video_path).name}."
                        )
                    else:
                        logging.warning(
                            f"Failed to read frame {frame_idx} for chunk [{chunk_start}, {chunk_end}] "
                            f"in {Path(video_path).name}."
                        )
                    results.append({
                        'frame_idx': frame_idx,
                        'detections': [],
                        'face_detected': False
                    })

                    next_frame_idx = frame_idx + 1
                    if next_frame_idx <= chunk_end:
                        try:
                            cap.release()
                        except Exception:
                            pass
                        cap = cv2.VideoCapture(video_path)
                        if cap.isOpened():
                            cap.read()
                            cap.set(cv2.CAP_PROP_POS_FRAMES, next_frame_idx)
                    continue
            
            current_detections = []
            face_detected = False
            
            if tracking_engine_type == "face_engine":
                try:
                    detections = face_engine_global.detect(frame)
                    if detections:
                        face_detected = True
                        current_detections.extend(detections)
                except Exception as e:
                    logging.warning(f"Face engine detection failed for frame {frame_idx}: {e}")
            else:
                orig_h, orig_w = frame.shape[:2]
                work_frame = frame
                scale_to_original = 1.0
                if max_width is not None and orig_w > max_width:
                    scale_factor = float(max_width) / float(orig_w)
                    work_h = max(1, int(orig_h * scale_factor))
                    work_frame = cv2.resize(frame, (int(max_width), int(work_h)), interpolation=cv2.INTER_LINEAR)
                    scale_to_original = float(orig_w) / float(work_frame.shape[1])

                t_to_rgb = time.perf_counter() if enable_profiling else 0.0
                mp_image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=cv2.cvtColor(work_frame, cv2.COLOR_BGR2RGB)
                )
                if enable_profiling:
                    profiling_stats["to_rgb_total"] += time.perf_counter() - t_to_rgb

                timestamp_ms = int(frame_idx * 1000 / args_dict.get('fps', 25))
                
                try:
                    t_detect = time.perf_counter() if enable_profiling else 0.0
                    face_result = landmarker_global.detect_for_video(mp_image, timestamp_ms)
                    if enable_profiling:
                        profiling_stats["detect_total"] += time.perf_counter() - t_detect
                    
                    if face_result.face_landmarks:
                        face_detected = True
                        
                        for i, landmarks in enumerate(face_result.face_landmarks):
                            t_post = time.perf_counter() if enable_profiling else 0.0
                            x_coords = [lm.x * orig_w for lm in landmarks]
                            y_coords = [lm.y * orig_h for lm in landmarks]
                            bbox = (
                                int(min(x_coords)), int(min(y_coords)),
                                int(max(x_coords) - min(x_coords)),
                                int(max(y_coords) - min(y_coords))
                            )
                            centroid = (int(np.mean(x_coords)), int(np.mean(y_coords)))
                            
                            det = {
                                "bbox": bbox,
                                "centroid": centroid,
                                "source_detector": "face_landmarker",
                                "label": "face"
                            }
                            
                            if face_result.face_blendshapes:
                                raw_blendshapes = {
                                    cat.category_name: cat.score
                                    for cat in face_result.face_blendshapes[i]
                                }
                                scaled_blendshapes = _apply_jawopen_scale(raw_blendshapes, jaw_open_scale)

                                current_frame_num = frame_idx + 1
                                should_update_blendshapes = (blendshapes_throttle_n <= 1) or ((current_frame_num % blendshapes_throttle_n) == 0)
                                object_id = f"{bbox[0]}_{bbox[1]}_{bbox[2]}_{bbox[3]}"
                                if should_update_blendshapes or object_id not in blendshapes_cache:
                                    blendshapes_cache[object_id] = scaled_blendshapes
                                    det["blendshapes"] = scaled_blendshapes
                                else:
                                    det["blendshapes"] = blendshapes_cache.get(object_id)
                            
                            current_detections.append(det)

                            if enable_profiling:
                                profiling_stats["post_total"] += time.perf_counter() - t_post
                
                except Exception as e:
                    logging.warning(f"Face detection failed for frame {frame_idx}: {e}")

                if enable_profiling:
                    fc = int(profiling_stats.get("frame_count", 0) or 0)
                    if fc > 0 and (fc % 20) == 0:
                        to_rgb_ms = (profiling_stats["to_rgb_total"] / fc) * 1000.0
                        detect_ms = (profiling_stats["detect_total"] / fc) * 1000.0
                        post_ms = (profiling_stats["post_total"] / fc) * 1000.0
                        logging.info(
                            "[PROFILING] MediaPipe after %s frames: to_rgb=%.2fms/frame, detect=%.2fms/frame, post=%.2fms/frame",
                            fc,
                            to_rgb_ms,
                            detect_ms,
                            post_ms,
                        )
            
            # Object detection fallback if no faces detected
            if not face_detected and args_dict.get('enable_object_detection', False) and object_detector_global:
                try:
                    if tracking_engine_type == "face_engine":
                        mp_image = mp.Image(
                            image_format=mp.ImageFormat.SRGB,
                            data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        )
                        timestamp_ms = int(frame_idx * 1000 / args_dict.get('fps', 25))
                    object_result = object_detector_global.detect_for_video(mp_image, timestamp_ms)
                    
                    if object_result.detections:
                        for detection in object_result.detections:
                            bbox = detection.bounding_box
                            x_min = int(bbox.origin_x)
                            y_min = int(bbox.origin_y)
                            width = int(bbox.width)
                            height = int(bbox.height)

                            if tracking_engine_type != "face_engine":
                                x_min = int(max(0, x_min * scale_to_original))
                                y_min = int(max(0, y_min * scale_to_original))
                                width = int(max(0, width * scale_to_original))
                                height = int(max(0, height * scale_to_original))
                            
                            centroid = (x_min + width // 2, y_min + height // 2)
                            
                            best_category = detection.categories[0] if detection.categories else None
                            label = best_category.category_name if best_category else "object"
                            confidence = best_category.score if best_category else 0.0
                            
                            det = {
                                "bbox": (x_min, y_min, width, height),
                                "centroid": centroid,
                                "source_detector": "object_detector",
                                "label": label,
                                "confidence": confidence,
                                "blendshapes": None,
                                "is_speaking": None
                            }
                            current_detections.append(det)
                            
                except Exception as e:
                    logging.warning(f"Object detection failed for frame {frame_idx}: {e}")
            
            results.append({
                'frame_idx': frame_idx,
                'detections': current_detections,
                'face_detected': face_detected
            })
        
        cap.release()
        logging.info(f"[WORKER-{worker_pid}] Chunk [{chunk_start}, {chunk_end}] completed: {len(results)} frames processed")
        return results
        
    except Exception as e:
        logging.error(f"[WORKER-{worker_pid}] CRITICAL ERROR in chunk [{chunk_start}, {chunk_end}]: {type(e).__name__}: {e}")
        import traceback
        logging.error(f"[WORKER-{worker_pid}] Traceback: {traceback.format_exc()}")
        try:
            cap.release()
        except:
            pass
        return []


def process_video_multiprocessing(args, video_capture, total_frames):
    """
    Process video using multiprocessing with frame chunking.
    """
    logging.info(f"Starting multiprocessing with {args.mp_num_workers_internal} workers")
    
    # Get video metadata
    fps = video_capture.get(cv2.CAP_PROP_FPS)
    
    # Prepare arguments for workers
    models_dir = Path(args.models_dir)
    args_dict = {
        'tracking_engine': getattr(args, 'tracking_engine', None),
        'mp_landmarker_num_faces': args.mp_landmarker_num_faces,
        'mp_landmarker_min_face_detection_confidence': args.mp_landmarker_min_face_detection_confidence,
        'mp_landmarker_min_face_presence_confidence': args.mp_landmarker_min_face_presence_confidence,
        'mp_landmarker_min_tracking_confidence': args.mp_landmarker_min_tracking_confidence,
        'object_max_results': getattr(args, 'object_max_results', 5),
        'object_score_threshold': getattr(args, 'object_score_threshold', 0.4),
        'enable_object_detection': getattr(args, 'enable_object_detection', False),
        'fps': fps,
        'enable_profiling': _is_truthy_env(os.environ.get('STEP5_ENABLE_PROFILING', '0')),
        'blendshapes_throttle_n': max(1, int(os.environ.get('STEP5_BLENDSHAPES_THROTTLE_N', '1'))),
        'mediapipe_max_width': os.environ.get('STEP5_MEDIAPIPE_MAX_WIDTH'),
        'mediapipe_max_faces': os.environ.get('STEP5_MEDIAPIPE_MAX_FACES'),
        'mediapipe_jawopen_scale': os.environ.get('STEP5_MEDIAPIPE_JAWOPEN_SCALE', '1.0'),
        # OpenCV engine paths (env vars not inherited by ProcessPoolExecutor)
        'yunet_model_path': os.environ.get('STEP5_YUNET_MODEL_PATH'),
        'opencv_max_faces': os.environ.get('STEP5_OPENCV_MAX_FACES'),
        'opencv_jawopen_scale': os.environ.get('STEP5_OPENCV_JAWOPEN_SCALE'),
        'facemesh_onnx_path': os.environ.get('STEP5_FACEMESH_ONNX_PATH'),
        'pyfeat_model_path': os.environ.get('STEP5_PYFEAT_MODEL_PATH'),
        # ONNX Runtime performance tuning (used by several engines)
        'step5_onnx_intra_op_threads': os.environ.get('STEP5_ONNX_INTRA_OP_THREADS'),
        'step5_onnx_inter_op_threads': os.environ.get('STEP5_ONNX_INTER_OP_THREADS'),
        # OpenSeeFace engine configuration
        'openseeface_models_dir': os.environ.get('STEP5_OPENSEEFACE_MODELS_DIR'),
        'openseeface_model_id': os.environ.get('STEP5_OPENSEEFACE_MODEL_ID'),
        'openseeface_detection_model_path': os.environ.get('STEP5_OPENSEEFACE_DETECTION_MODEL_PATH'),
        'openseeface_landmark_model_path': os.environ.get('STEP5_OPENSEEFACE_LANDMARK_MODEL_PATH'),
        'openseeface_detect_every_n': os.environ.get('STEP5_OPENSEEFACE_DETECT_EVERY_N'),
        'openseeface_detection_threshold': os.environ.get('STEP5_OPENSEEFACE_DETECTION_THRESHOLD'),
        'openseeface_max_faces': os.environ.get('STEP5_OPENSEEFACE_MAX_FACES'),
        'openseeface_jawopen_scale': os.environ.get('STEP5_OPENSEEFACE_JAWOPEN_SCALE'),
        'eos_models_dir': os.environ.get('STEP5_EOS_MODELS_DIR'),
        'eos_sfm_model_path': os.environ.get('STEP5_EOS_SFM_MODEL_PATH'),
        'eos_expression_blendshapes_path': os.environ.get('STEP5_EOS_EXPRESSION_BLENDSHAPES_PATH'),
        'eos_landmark_mapper_path': os.environ.get('STEP5_EOS_LANDMARK_MAPPER_PATH'),
        'eos_edge_topology_path': os.environ.get('STEP5_EOS_EDGE_TOPOLOGY_PATH'),
        'eos_model_contour_path': os.environ.get('STEP5_EOS_MODEL_CONTOUR_PATH'),
        'eos_contour_landmarks_path': os.environ.get('STEP5_EOS_CONTOUR_LANDMARKS_PATH'),
        'eos_fit_every_n': os.environ.get('STEP5_EOS_FIT_EVERY_N'),
        'eos_max_faces': os.environ.get('STEP5_EOS_MAX_FACES'),
        'eos_max_width': os.environ.get('STEP5_EOS_MAX_WIDTH'),
        'eos_jawopen_scale': os.environ.get('STEP5_EOS_JAWOPEN_SCALE'),
        'object_detector_model': getattr(args, 'object_detector_model', None) or os.environ.get('STEP5_OBJECT_DETECTOR_MODEL'),
        'object_detector_model_path': getattr(args, 'object_detector_model_path', None) or os.environ.get('STEP5_OBJECT_DETECTOR_MODEL_PATH'),
        'total_frames': total_frames,
    }
    
    # Create frame chunks (adaptive chunk size to keep CPU workers saturated)
    # If chunk_size is provided (>0), honor it; otherwise, derive adaptively.
    provided_chunk_size = int(getattr(args, 'chunk_size', 400))
    if provided_chunk_size <= 0:
        # Target ~5 chunks per worker, minimum 20 chunks overall.
        mp_workers = max(1, int(getattr(args, 'mp_num_workers_internal', 1)))
        target_chunks = max(mp_workers * 5, 20)
        # Compute chunk size from total frames and clamp to avoid too fine granularity.
        adaptive_chunk = int(math.ceil(total_frames / max(1, target_chunks)))
        # Allow small chunks to reach ~5x workers (e.g., ~75 chunks for ~1600 frames & 15 workers)
        # Bounds can be overridden via args.chunk_min/chunk_max if provided.
        min_bound = int(getattr(args, 'chunk_min', 20) or 20)
        max_bound = int(getattr(args, 'chunk_max', 400) or 400)
        if min_bound > max_bound:
            min_bound, max_bound = max_bound, min_bound
        chunk_size = max(min_bound, min(max_bound, adaptive_chunk))
        logging.info(
            f"Adaptive chunking enabled: total_frames={total_frames}, workers={mp_workers}, "
            f"target_chunks={target_chunks}, bounds=[{min_bound},{max_bound}], selected_chunk_size={chunk_size}"
        )
    else:
        chunk_size = provided_chunk_size
        logging.info(f"Using provided chunk_size={chunk_size}")

    chunks = []
    
    for start_frame in range(0, total_frames, chunk_size):
        end_frame = min(start_frame + chunk_size - 1, total_frames - 1)
        chunks.append((start_frame, end_frame, args.video_file_path, args_dict))
    
    logging.info(f"Created {len(chunks)} chunks for processing (chunk_size={chunk_size})")
    
    # Process chunks using multiprocessing
    all_results = {}
    face_detection_count = 0
    processing_start_time = time.time()
    
    # Use ProcessPoolExecutor for better resource management
    with ProcessPoolExecutor(
        max_workers=args.mp_num_workers_internal,
        initializer=init_worker_process,
        initargs=(models_dir, args_dict)
    ) as executor:
        
        # Submit all chunks
        future_to_chunk = {executor.submit(process_frame_chunk, chunk): chunk for chunk in chunks}
        
        completed_chunks = 0
        # Throttle progress logs to ~10% intervals
        progress_every = max(1, len(chunks) // 10)
        for future in as_completed(future_to_chunk):
            chunk = future_to_chunk[future]
            try:
                chunk_results = future.result()
                
                # Store results by frame index
                for result in chunk_results:
                    all_results[result['frame_idx']] = result
                    if result['face_detected']:
                        face_detection_count += 1
                
                completed_chunks += 1
                
                # Progress logging (throttled)
                if completed_chunks % progress_every == 0:
                    progress_percent = (completed_chunks / len(chunks)) * 100
                    elapsed_time = time.time() - processing_start_time
                    fps_rate = (completed_chunks * chunk_size) / elapsed_time if elapsed_time > 0 else 0
                    print(f"[Progression]|{int(progress_percent)}|{min(completed_chunks * chunk_size, total_frames)}|{total_frames}")
                    logging.info(f"Multiprocessing: {completed_chunks}/{len(chunks)} chunks ({progress_percent:.1f}%) - {fps_rate:.1f} fps (chunk_size={chunk_size})")
                    
            except Exception as e:
                logging.error(f"Chunk processing failed: {e}")
    
    logging.info("Multiprocessing complete, applying sequential tracking...")
    
    # Apply tracking sequentially (must be sequential for consistency)
    tracked_objects = {}
    next_id_counter = {'value': 0}
    final_output = {
        "metadata": {
            "video_path": args.video_file_path,
            "total_frames": total_frames,
            "fps": fps
        },
        "frames": []
    }
    
    # Initialize enhanced speaking detector
    enhanced_speaking_detector = None
    try:
        enhanced_speaking_detector = EnhancedSpeakingDetector(
            video_path=args.video_file_path,
            jaw_threshold=args.speaking_detection_jaw_open_threshold
        )
        logging.info("Enhanced speaking detection initialized")
    except Exception as e:
        logging.warning(f"Failed to initialize enhanced speaking detector: {e}")
    
    missing_frame_count = 0
    first_missing_frame = None
    for frame_idx in range(total_frames):
        result = all_results.get(frame_idx)
        if result is None:
            missing_frame_count += 1
            if first_missing_frame is None:
                first_missing_frame = frame_idx
            detections = []
        else:
            detections = result.get('detections', [])
        
        tracked_for_frame = apply_tracking_and_management(
            tracked_objects, detections, next_id_counter,
            args.mp_max_distance_tracking, args.mp_frames_unseen_deregister,
            args.speaking_detection_jaw_open_threshold,
            enhanced_speaking_detector=enhanced_speaking_detector,
            current_frame_num=frame_idx + 1
        )
        
        final_output["frames"].append({
            "frame": frame_idx + 1,
            "tracked_objects": tracked_for_frame if tracked_for_frame else []
        })

    if missing_frame_count > 0:
        logging.warning(
            f"Missing detection results for {missing_frame_count}/{total_frames} frames "
            f"(first missing frame index: {first_missing_frame}). Output remains dense with empty tracked_objects." 
        )
    
    # Calculate final statistics
    face_detection_rate = (face_detection_count / total_frames * 100) if total_frames > 0 else 0
    processing_time = time.time() - processing_start_time
    
    logging.info("Multiprocessing summary:")
    logging.info(f"  Total frames expected: {total_frames}")
    logging.info(f"  Total frames with detection results: {len(all_results)}")
    logging.info(f"  Frames with faces: {face_detection_count}")
    logging.info(f"  Face detection success rate: {face_detection_rate:.2f}%")
    logging.info(f"  Processing time: {processing_time:.2f} seconds")
    logging.info(f"  Average FPS: {total_frames / processing_time:.2f}")
    logging.info(f"  Total frames exported: {len(final_output['frames'])}")
    
    return final_output


def main(args):
    """Main processing function with multiprocessing support."""
    engine_norm = (str(getattr(args, 'tracking_engine', '') or '').strip().lower())
    
    worker_type = "CPU_MULTIPROCESSING" if getattr(args, 'mp_num_workers_internal', 1) > 1 else "CPU"
    logging.info(f"Starting {worker_type} processing for: {Path(args.video_file_path).name}")
    
    # Use safe video processing with automatic resource cleanup
    try:
        with safe_video_processing(args.video_file_path) as (video_capture, temp_manager):
            # Get video metadata safely
            fps = video_capture.get(cv2.CAP_PROP_FPS)
            total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
            
            logging.info(f"Video metadata - FPS: {fps}, Total frames: {total_frames}")
            
            # Check if multiprocessing should be used
            use_multiprocessing = (not getattr(args, 'use_gpu', False) and 
                                 getattr(args, 'mp_num_workers_internal', 1) > 1)
            
            if use_multiprocessing:
                final_output = process_video_multiprocessing(args, video_capture, total_frames)
            else:
                # Fallback to sequential processing (existing implementation)
                logging.info("Using sequential processing (fallback)")
                # ... existing sequential logic would go here
                return False
                
    except Exception as e:
        logging.error(f"Error processing video {args.video_file_path}: {e}")
        raise
    
    # Save output
    output_path = Path(args.video_file_path).with_suffix('.json')
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        logging.info(f"Processing complete. JSON saved: {output_path.name}")
        print(f"[Progression]|100|{total_frames}|{total_frames}", flush=True)
    except Exception as e:
        logging.error(f"Failed to save output file {output_path}: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhanced CPU Worker with Multiprocessing")
    parser.add_argument("video_file_path")
    parser.add_argument("--models_dir", required=True)
    parser.add_argument("--use_gpu", action="store_true")
    parser.add_argument("--tracking_engine", default=None, help="Tracking engine: mediapipe_landmarker (default), opencv_haar, opencv_yunet, opencv_yunet_pyfeat, openseeface")
    parser.add_argument("--mp_landmarker_num_faces", type=int, default=5)
    parser.add_argument("--mp_landmarker_min_face_detection_confidence", type=float, default=0.3)
    parser.add_argument("--mp_landmarker_min_face_presence_confidence", type=float, default=0.2)
    parser.add_argument("--mp_landmarker_min_tracking_confidence", type=float, default=0.3)
    parser.add_argument("--mp_max_distance_tracking", type=int, default=80)
    parser.add_argument("--mp_frames_unseen_deregister", type=int, default=7)
    parser.add_argument("--speaking_detection_jaw_open_threshold", type=float, default=0.08)
    parser.add_argument("--enable_object_detection", action="store_true")
    parser.add_argument("--object_score_threshold", type=float, default=0.4)
    parser.add_argument("--object_max_results", type=int, default=5)
    parser.add_argument("--mp_num_workers_internal", type=int, default=1)
    parser.add_argument("--chunk_size", type=int, default=0, help="Chunk size (frames) for multiprocessing splitting; 0=adaptive")
    parser.add_argument("--chunk_min", type=int, default=None, help="Minimum chunk size when adaptive is used")
    parser.add_argument("--chunk_max", type=int, default=None, help="Maximum chunk size when adaptive is used")
    
    args, _ = parser.parse_known_args()
    
    try:
        mp_proc.freeze_support()  # Required for Windows compatibility
        main(args)
        sys.exit(0)
    except Exception as e:
        logging.error(f"Critical error in worker: {e}", exc_info=True)
        sys.exit(1)
