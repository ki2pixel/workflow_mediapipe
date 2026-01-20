#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, argparse, logging, importlib, cv2, numpy as np
import threading, queue, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from utils.tracking_optimizations import apply_tracking_and_management
from utils.resource_manager import safe_video_processing, get_video_metadata, resource_tracker
from utils.enhanced_speaking_detection import EnhancedSpeakingDetector

from face_engines import create_face_engine
from object_detector_registry import ObjectDetectorRegistry

mp = None


def _ensure_mediapipe_loaded(required: bool = False):
    """Lazy import Mediapipe to avoid TensorFlow dependency unless needed."""
    global mp
    if mp is not None:
        return mp
    try:
        if not hasattr(np, "complex_"):
            np.complex_ = np.complex128
        mp = importlib.import_module("mediapipe")
        return mp
    except Exception as exc:
        msg = f"MediaPipe import failed: {exc}"
        if required:
            logging.error(msg)
            raise
        logging.warning(msg)
        return None

# Configuration du logger
log_dir = Path(__file__).resolve().parent.parent.parent / "logs" / "step5"
log_dir.mkdir(parents=True, exist_ok=True)
worker_type_str = "GPU" if "--use_gpu" in sys.argv else "CPU"
video_name_for_log = Path(sys.argv[1]).stem if len(sys.argv) > 1 else "unknown"
log_file = log_dir / f"worker_{worker_type_str}_{video_name_for_log}_{os.getpid()}.log"
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s',
                    handlers=[logging.FileHandler(log_file, encoding='utf-8'), logging.StreamHandler(sys.stdout)])

# Limiter le threading interne d'OpenCV pour éviter la contention avec nos propres pools
try:
    cv2.setNumThreads(1)
    cv2.ocl.setUseOpenCL(False)
except Exception:
    # Sécurité: ignorer si non supporté sur la plateforme
    pass


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


class FrameProcessor:
    """Thread-safe frame processor for multi-threaded CPU processing."""

    def __init__(self, landmarker, object_detector, args, enhanced_speaking_detector=None):
        self.landmarker = landmarker
        self.object_detector = object_detector
        self.args = args
        self.enhanced_speaking_detector = enhanced_speaking_detector
        self.lock = threading.Lock()

        self._enable_profiling = _is_truthy_env(os.environ.get("STEP5_ENABLE_PROFILING", "0"))
        self._profiling_stats = {
            "to_rgb_total": 0.0,
            "detect_total": 0.0,
            "post_total": 0.0,
            "frame_count": 0,
        }
        self._blendshapes_throttle_n = max(1, int(os.environ.get("STEP5_BLENDSHAPES_THROTTLE_N", "1")))
        self._jaw_open_scale = float(os.environ.get("STEP5_MEDIAPIPE_JAWOPEN_SCALE", "1.0"))
        self._max_width = _parse_optional_positive_int(os.environ.get("STEP5_MEDIAPIPE_MAX_WIDTH"))
        self._blendshapes_cache = {}

    def process_frame(self, frame_data):
        """Process a single frame and return detection results."""
        frame, frame_idx, timestamp_ms = frame_data

        try:
            orig_h, orig_w = frame.shape[:2]
            work_frame = frame
            scale_to_original = 1.0
            if self._max_width is not None and orig_w > self._max_width:
                scale_factor = float(self._max_width) / float(orig_w)
                work_h = max(1, int(orig_h * scale_factor))
                work_frame = cv2.resize(frame, (int(self._max_width), int(work_h)), interpolation=cv2.INTER_LINEAR)
                scale_to_original = float(orig_w) / float(work_frame.shape[1])

            if self._enable_profiling:
                with self.lock:
                    self._profiling_stats["frame_count"] += 1

            t_to_rgb = time.perf_counter() if self._enable_profiling else 0.0
            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=cv2.cvtColor(work_frame, cv2.COLOR_BGR2RGB)
            )
            if self._enable_profiling:
                with self.lock:
                    self._profiling_stats["to_rgb_total"] += time.perf_counter() - t_to_rgb

            current_detections = []
            face_detected = False

            # Try face detection first
            t_detect = time.perf_counter() if self._enable_profiling else 0.0
            face_result = self.landmarker.detect_for_video(mp_image, timestamp_ms)
            if self._enable_profiling:
                with self.lock:
                    self._profiling_stats["detect_total"] += time.perf_counter() - t_detect

            if face_result.face_landmarks:
                face_detected = True

                for i, landmarks in enumerate(face_result.face_landmarks):
                    t_post = time.perf_counter() if self._enable_profiling else 0.0
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
                        scaled_blendshapes = _apply_jawopen_scale(raw_blendshapes, self._jaw_open_scale)

                        current_frame_num = frame_idx + 1
                        should_update_blendshapes = (self._blendshapes_throttle_n <= 1) or ((current_frame_num % self._blendshapes_throttle_n) == 0)
                        object_id = f"{bbox[0]}_{bbox[1]}_{bbox[2]}_{bbox[3]}"
                        with self.lock:
                            if should_update_blendshapes or object_id not in self._blendshapes_cache:
                                self._blendshapes_cache[object_id] = scaled_blendshapes
                                det["blendshapes"] = scaled_blendshapes
                            else:
                                det["blendshapes"] = self._blendshapes_cache.get(object_id)
                    current_detections.append(det)

                    if self._enable_profiling:
                        with self.lock:
                            self._profiling_stats["post_total"] += time.perf_counter() - t_post

            if self._enable_profiling:
                with self.lock:
                    fc = int(self._profiling_stats.get("frame_count", 0) or 0)
                    if fc > 0 and (fc % 20) == 0:
                        to_rgb_ms = (self._profiling_stats["to_rgb_total"] / fc) * 1000.0
                        detect_ms = (self._profiling_stats["detect_total"] / fc) * 1000.0
                        post_ms = (self._profiling_stats["post_total"] / fc) * 1000.0
                        logging.info(
                            "[PROFILING] MediaPipe after %s frames: to_rgb=%.2fms/frame, detect=%.2fms/frame, post=%.2fms/frame",
                            fc,
                            to_rgb_ms,
                            detect_ms,
                            post_ms,
                        )

            # Use object detection fallback if no faces detected
            if not face_detected and getattr(self.args, 'enable_object_detection', False):
                try:
                    object_result = self.object_detector.detect_for_video(mp_image, timestamp_ms)

                    if object_result.detections:
                        for detection in object_result.detections:
                            bbox = detection.bounding_box
                            x_min = int(bbox.origin_x)
                            y_min = int(bbox.origin_y)
                            width = int(bbox.width)
                            height = int(bbox.height)

                            if scale_to_original != 1.0:
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
                    logging.warning(f"Object detection failed for frame {frame_idx + 1}: {e}")

            return {
                'frame_idx': frame_idx,
                'detections': current_detections,
                'face_detected': face_detected,
                'timestamp_ms': timestamp_ms
            }

        except Exception as e:
            logging.error(f"Error processing frame {frame_idx + 1}: {e}")
            return {
                'frame_idx': frame_idx,
                'detections': [],
                'face_detected': False,
                'timestamp_ms': timestamp_ms,
                'error': str(e)
            }


def process_video_multithreaded(args, video_capture, landmarker, object_detector, enhanced_speaking_detector, total_frames):
    """Process video using multiple threads for CPU workers."""
    logging.info(f"Starting multi-threaded processing with {args.mp_num_workers_internal} workers (bounded queue)")

    # Initialize tracking variables
    tracked_objects = {}
    next_id_counter = {'value': 0}

    # Get video metadata
    fps = video_capture.get(cv2.CAP_PROP_FPS)

    final_output = {
        "metadata": {
            "video_path": args.video_file_path,
            "total_frames": total_frames,
            "fps": fps
        },
        "frames": []
    }

    # Performance tracking
    face_detection_success_count = 0
    frames_processed = 0
    processing_start_time = time.time()

    # Create frame processor
    frame_processor = FrameProcessor(landmarker, object_detector, args, enhanced_speaking_detector)

    # Bounded queue pipeline: un thread lecteur + N threads workers
    q = queue.Queue(maxsize=64)
    results = {}
    results_lock = threading.Lock()

    def worker_loop(worker_id: int):
        nonlocal frames_processed
        completed_local = 0
        while True:
            item = q.get()
            if item is None:
                q.task_done()
                break
            frame, idx, ts_ms = item
            try:
                result = frame_processor.process_frame((frame, idx, ts_ms))
                with results_lock:
                    results[idx] = result
                completed_local += 1
                frames_processed += 1
                if frames_processed % 50 == 0:
                    progress_percent = (frames_processed / total_frames) * 100 if total_frames else 0
                    elapsed_time = time.time() - processing_start_time
                    fps_now = frames_processed / elapsed_time if elapsed_time > 0 else 0
                    print(f"[Progression]|{int(progress_percent)}|{frames_processed}|{total_frames}", flush=True)
                    logging.info(f"MT workers: {frames_processed}/{total_frames} ({progress_percent:.1f}%) - {fps_now:.1f} fps")
            except Exception as e:
                logging.error(f"Frame {idx} processing failed: {e}")
                with results_lock:
                    results[idx] = {
                        'frame_idx': idx,
                        'detections': [],
                        'face_detected': False,
                        'error': str(e)
                    }
            finally:
                # Libérer la référence à la frame pour GC
                del frame
                q.task_done()

    # Lancer les workers
    workers = [threading.Thread(target=worker_loop, args=(i,), daemon=True)
               for i in range(int(args.mp_num_workers_internal))]
    for t in workers:
        t.start()

    # Thread lecteur: lit et pousse les frames dans la queue (bornée)
    frame_read = 0
    logging.info("Reading frames and feeding bounded queue...")
    while video_capture.isOpened():
        ret, frame = video_capture.read()
        if not ret:
            break
        ts_ms = int(video_capture.get(cv2.CAP_PROP_POS_MSEC))
        q.put((frame, frame_read, ts_ms))
        frame_read += 1
        if frame_read % 100 == 0:
            logging.info(f"Read {frame_read} frames...")

    # Envoyer les sentinelles d'arrêt aux workers
    for _ in workers:
        q.put(None)

    # Attendre la fin du traitement
    q.join()
    for t in workers:
        t.join(timeout=1)

    logging.info("Parallel processing complete, applying tracking...")

    # Apply tracking in sequential order (must be sequential for consistency)
    for frame_idx in sorted(results.keys()):
        result = results[frame_idx]

        if result.get('face_detected', False):
            face_detection_success_count += 1

        # Apply tracking and management
        tracked_for_frame = apply_tracking_and_management(
            tracked_objects, result['detections'], next_id_counter,
            args.mp_max_distance_tracking, args.mp_frames_unseen_deregister,
            args.speaking_detection_jaw_open_threshold,
            enhanced_speaking_detector=enhanced_speaking_detector,
            current_frame_num=frame_idx + 1
        )

        # Add to final output
        final_output["frames"].append({
            "frame": frame_idx + 1,
            "tracked_objects": tracked_for_frame if tracked_for_frame else []
        })

    # Calculate final statistics
    face_detection_rate = (face_detection_success_count / frames_processed * 100) if frames_processed > 0 else 0
    processing_time = time.time() - processing_start_time

    logging.info("Multi-threaded processing summary:")
    logging.info(f"  Total frames processed: {frames_processed}")
    logging.info(f"  Frames with faces: {face_detection_success_count}")
    logging.info(f"  Face detection success rate: {face_detection_rate:.2f}%")
    logging.info(f"  Processing time: {processing_time:.2f} seconds")
    logging.info(f"  Average FPS: {frames_processed / processing_time:.2f}")
    logging.info(f"  Object detection fallback used: {getattr(args, 'enable_object_detection', False)}")
    logging.info(f"  Total frames exported: {len(final_output['frames'])}")

    return final_output


def main(args):
    """Traite une vidéo de manière séquentielle (un seul thread)."""
    worker_type = "GPU" if args.use_gpu else "CPU"
    logging.info(f"Démarrage du traitement séquentiel {worker_type} pour: {Path(args.video_file_path).name}")
    logging.info(f"LD_LIBRARY_PATH (worker) = {os.environ.get('LD_LIBRARY_PATH', '')}")
    logging.info(f"INSIGHTFACE_HOME (worker) = {os.environ.get('INSIGHTFACE_HOME', '')}")

    engine_name = getattr(args, 'tracking_engine', None)
    use_gpu_flag = bool(getattr(args, 'use_gpu', False))
    face_engine = None
    if engine_name:
        try:
            face_engine = create_face_engine(engine_name, use_gpu=use_gpu_flag)
        except Exception as e:
            logging.exception(f"Failed to initialize tracking engine '{engine_name}': {e}")
            sys.exit(1)

    final_output = None
    total_frames = 0

    if face_engine is not None:
        logging.info(f"Using OpenCV tracking engine: {engine_name}")
        try:
            with safe_video_processing(args.video_file_path) as (video_capture, temp_manager):
                fps = video_capture.get(cv2.CAP_PROP_FPS)
                total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))

                object_detector = None
                object_options = None
                mp_module = None
                ObjectDetector = None
                object_detection_workers = max(1, int(getattr(args, 'mp_num_workers_internal', 1) or 1))
                if args.use_gpu and getattr(args, 'enable_object_detection', False):
                    logging.info(
                        "Object detection fallback workers (GPU face engine mode): %s",
                        object_detection_workers,
                    )
                if getattr(args, 'enable_object_detection', False):
                    try:
                        mp_module = _ensure_mediapipe_loaded(required=False)
                        if mp_module is None:
                            raise RuntimeError("mediapipe is not available (lazy import failed)")

                        BaseOptions = mp_module.tasks.BaseOptions
                        VisionRunningMode = mp_module.tasks.vision.RunningMode
                        ObjectDetector = mp_module.tasks.vision.ObjectDetector
                        ObjectDetectorOptions = mp_module.tasks.vision.ObjectDetectorOptions

                        delegate = BaseOptions.Delegate.CPU
                        models_dir = Path(args.models_dir)
                        object_detector_model_name = (
                            getattr(args, 'object_detector_model', None)
                            or os.environ.get('STEP5_OBJECT_DETECTOR_MODEL', 'efficientdet_lite2')
                        )
                        object_detector_model_path = (
                            getattr(args, 'object_detector_model_path', None)
                            or os.environ.get('STEP5_OBJECT_DETECTOR_MODEL_PATH')
                        )
                        object_model_path = ObjectDetectorRegistry.resolve_model_path(
                            model_name=object_detector_model_name,
                            models_dir=models_dir,
                            override_path=object_detector_model_path,
                        )
                        logging.info(
                            f"Using object detector (face_engine mode): {object_detector_model_name} at {object_model_path}"
                        )
                        object_options = ObjectDetectorOptions(
                            base_options=BaseOptions(model_asset_path=str(object_model_path), delegate=delegate),
                            running_mode=VisionRunningMode.IMAGE,
                            max_results=getattr(args, 'object_max_results', 5),
                            score_threshold=getattr(args, 'object_score_threshold', 0.4),
                        )
                        object_detector = ObjectDetector.create_from_options(object_options)
                        if object_detection_workers > 1:
                            logging.info(
                                "Object detection fallback: using one MediaPipe ObjectDetector instance per thread (IMAGE mode)."
                            )
                    except Exception as e:
                        logging.warning(
                            f"Failed to initialize object detector (face_engine mode); continuing without it: {e}"
                        )
                        object_detector = None
                        object_options = None
                        mp_module = None
                        ObjectDetector = None

                final_output = {
                    "metadata": {
                        "video_path": args.video_file_path,
                        "total_frames": total_frames,
                        "fps": fps,
                        "tracking_engine": engine_name,
                    },
                    "frames": [],
                }

                tracked_objects, next_id_counter = {}, {'value': 0}

                resource_id = resource_tracker.register_resource(
                    video_capture, 'video_capture', f"Processing {Path(args.video_file_path).name}"
                )

                try:
                    enhanced_speaking_detector = None
                    if getattr(args, 'speaking_detection_enabled', True):
                        try:
                            enhanced_speaking_detector = EnhancedSpeakingDetector(
                                video_path=args.video_file_path,
                                jaw_threshold=args.speaking_detection_jaw_open_threshold,
                            )
                            logging.info("Enhanced speaking detection initialized successfully")
                        except Exception as e:
                            logging.warning(f"Failed to initialize enhanced speaking detector: {e}")
                            enhanced_speaking_detector = None

                    object_tasks = None
                    object_results = {}
                    object_results_lock = threading.Lock()
                    object_worker_threads = []

                    def _object_worker_loop(worker_id: int):
                        thread_object_detector = None
                        if object_options is not None and ObjectDetector is not None:
                            try:
                                thread_object_detector = ObjectDetector.create_from_options(object_options)
                            except Exception as e:
                                logging.warning(
                                    "Object detection failed to initialize detector for worker %s (face_engine mode): %s",
                                    worker_id,
                                    e,
                                )
                                thread_object_detector = None
                        while True:
                            task = object_tasks.get() if object_tasks is not None else None
                            if task is None:
                                try:
                                    if thread_object_detector is not None and hasattr(thread_object_detector, 'close'):
                                        thread_object_detector.close()
                                except Exception:
                                    pass
                                if object_tasks is not None:
                                    object_tasks.task_done()
                                break
                            frame_local, frame_idx_local, timestamp_ms_local = task
                            try:
                                if mp_module is None or thread_object_detector is None:
                                    raise RuntimeError("object detector is not available for object detection fallback")
                                mp_image = mp_module.Image(
                                    image_format=mp_module.ImageFormat.SRGB,
                                    data=cv2.cvtColor(frame_local, cv2.COLOR_BGR2RGB)
                                )
                                object_result = thread_object_detector.detect(mp_image)
                                detections_out = []
                                if object_result.detections:
                                    for detection in object_result.detections:
                                        bbox = detection.bounding_box
                                        x_min = int(bbox.origin_x)
                                        y_min = int(bbox.origin_y)
                                        width = int(bbox.width)
                                        height = int(bbox.height)
                                        centroid = (x_min + width // 2, y_min + height // 2)
                                        best_category = detection.categories[0] if detection.categories else None
                                        label = best_category.category_name if best_category else "object"
                                        confidence = best_category.score if best_category else 0.0
                                        detections_out.append(
                                            {
                                                "bbox": (x_min, y_min, width, height),
                                                "centroid": centroid,
                                                "source_detector": "object_detector",
                                                "label": label,
                                                "confidence": confidence,
                                                "blendshapes": None,
                                                "is_speaking": None,
                                            }
                                        )
                                with object_results_lock:
                                    object_results[frame_idx_local] = detections_out
                            except Exception as e:
                                logging.warning(
                                    f"Object detection failed for frame {frame_idx_local + 1} (face_engine mode): {e}"
                                )
                                with object_results_lock:
                                    object_results[frame_idx_local] = []
                            finally:
                                del frame_local
                                object_tasks.task_done()

                    enable_object_fallback = bool(getattr(args, 'enable_object_detection', False))
                    enable_object_threads = bool(object_detector is not None and object_detection_workers > 1 and enable_object_fallback)
                    if enable_object_threads:
                        object_tasks = queue.Queue(maxsize=max(1, object_detection_workers) * 2)
                        for i in range(int(object_detection_workers)):
                            t = threading.Thread(target=_object_worker_loop, args=(i,), daemon=True)
                            object_worker_threads.append(t)
                            t.start()

                    frame_idx = 0
                    frame_detections = {}
                    while video_capture.isOpened():
                        ret, frame = video_capture.read()
                        if not ret:
                            break

                        current_detections = face_engine.detect(frame)
                        frame_idx += 1
                        if frame_idx % 50 == 0:
                            progress_percent = int((frame_idx / total_frames) * 90) if total_frames else 0
                            print(f"[Progression]|{progress_percent}|{frame_idx}|{total_frames}", flush=True)

                        if (not current_detections) and object_detector is not None and enable_object_fallback:
                            if enable_object_threads and object_tasks is not None:
                                object_tasks.put((frame, frame_idx - 1, None))
                            else:
                                try:
                                    if mp_module is None:
                                        raise RuntimeError("mediapipe is not available for object detection fallback")
                                    mp_image = mp_module.Image(
                                        image_format=mp_module.ImageFormat.SRGB,
                                        data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                    )
                                    object_result = object_detector.detect(mp_image)
                                    if object_result.detections:
                                        for detection in object_result.detections:
                                            bbox = detection.bounding_box
                                            x_min = int(bbox.origin_x)
                                            y_min = int(bbox.origin_y)
                                            width = int(bbox.width)
                                            height = int(bbox.height)
                                            centroid = (x_min + width // 2, y_min + height // 2)
                                            best_category = detection.categories[0] if detection.categories else None
                                            label = best_category.category_name if best_category else "object"
                                            confidence = best_category.score if best_category else 0.0
                                            current_detections.append(
                                                {
                                                    "bbox": (x_min, y_min, width, height),
                                                    "centroid": centroid,
                                                    "source_detector": "object_detector",
                                                    "label": label,
                                                    "confidence": confidence,
                                                    "blendshapes": None,
                                                    "is_speaking": None,
                                                }
                                            )
                                except Exception as e:
                                    logging.warning(
                                        f"Object detection failed for frame {frame_idx} (face_engine mode): {e}"
                                    )

                        frame_detections[frame_idx - 1] = list(current_detections)
                        del frame

                    if enable_object_threads and object_tasks is not None:
                        object_tasks.join()
                        for _ in object_worker_threads:
                            object_tasks.put(None)
                        object_tasks.join()
                        for t in object_worker_threads:
                            t.join(timeout=1)

                    for frame_idx_out in range(total_frames):
                        current_detections = frame_detections.get(frame_idx_out, [])
                        if (not current_detections) and object_detector is not None and enable_object_fallback:
                            with object_results_lock:
                                current_detections = list(object_results.get(frame_idx_out, []))

                        tracked_for_frame = apply_tracking_and_management(
                            tracked_objects,
                            current_detections,
                            next_id_counter,
                            args.mp_max_distance_tracking,
                            args.mp_frames_unseen_deregister,
                            args.speaking_detection_jaw_open_threshold,
                            enhanced_speaking_detector=enhanced_speaking_detector,
                            current_frame_num=frame_idx_out + 1,
                        )
                        final_output["frames"].append(
                            {
                                "frame": frame_idx_out + 1,
                                "tracked_objects": tracked_for_frame if tracked_for_frame else [],
                            }
                        )
                        if (frame_idx_out + 1) % 50 == 0:
                            progress_percent = 90 + int(((frame_idx_out + 1) / total_frames) * 10) if total_frames else 100
                            print(f"[Progression]|{progress_percent}|{frame_idx_out + 1}|{total_frames}", flush=True)

                    frame_idx = total_frames

                    if total_frames and frame_idx < total_frames:
                        for fill_idx in range(frame_idx, total_frames):
                            tracked_for_frame = apply_tracking_and_management(
                                tracked_objects,
                                [],
                                next_id_counter,
                                args.mp_max_distance_tracking,
                                args.mp_frames_unseen_deregister,
                                args.speaking_detection_jaw_open_threshold,
                                enhanced_speaking_detector=enhanced_speaking_detector,
                                current_frame_num=fill_idx + 1,
                            )
                            final_output["frames"].append(
                                {
                                    "frame": fill_idx + 1,
                                    "tracked_objects": tracked_for_frame if tracked_for_frame else [],
                                }
                            )
                finally:
                    try:
                        if object_detector is not None and hasattr(object_detector, 'close'):
                            object_detector.close()
                    except Exception:
                        pass
                    resource_tracker.unregister_resource(resource_id)

        except Exception as e:
            logging.error(f"Error processing video {args.video_file_path} with OpenCV engine: {e}")
            raise

        output_path = Path(args.video_file_path).with_suffix('.json')
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_output, f, indent=2, ensure_ascii=False)
            logging.info(f"Traitement terminé. JSON sauvegardé: {output_path.name}")
            print(f"[Progression]|100|{total_frames}|{total_frames}", flush=True)
        except Exception as e:
            logging.error(f"Failed to save output file {output_path}: {e}")
            raise
        return

    mp_module = _ensure_mediapipe_loaded(required=True)
    BaseOptions = mp_module.tasks.BaseOptions
    VisionRunningMode = mp_module.tasks.vision.RunningMode
    FaceLandmarker = mp_module.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp_module.tasks.vision.FaceLandmarkerOptions
    ObjectDetector = mp_module.tasks.vision.ObjectDetector
    ObjectDetectorOptions = mp_module.tasks.vision.ObjectDetectorOptions

    delegate = BaseOptions.Delegate.GPU if args.use_gpu else BaseOptions.Delegate.CPU
    models_dir = Path(args.models_dir)
    face_model_candidates = [
        models_dir / "face_detectors" / "mediapipe" / "face_landmarker_v2_with_blendshapes.task",
        models_dir / "face_landmarker_v2_with_blendshapes.task",
    ]
    face_model_path = next((p for p in face_model_candidates if p.exists()), face_model_candidates[0])
    
    if not face_model_path.exists():
        logging.error(f"Modèle FaceLandmarker non trouvé: {face_model_path}");
        sys.exit(1)
    
    # Resolve object detector model using registry
    object_detector_model_name = getattr(args, 'object_detector_model', 'efficientdet_lite2')
    try:
        object_model_path = ObjectDetectorRegistry.resolve_model_path(
            model_name=object_detector_model_name,
            models_dir=models_dir,
            override_path=getattr(args, 'object_detector_model_path', None)
        )
        logging.info(f"Using object detector: {object_detector_model_name} at {object_model_path}")
    except (ValueError, FileNotFoundError) as e:
        logging.error(f"Failed to resolve object detector model: {e}")
        sys.exit(1)

    face_options = FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(face_model_path), delegate=delegate),
        running_mode=VisionRunningMode.VIDEO,
        num_faces=int(_parse_optional_positive_int(os.environ.get("STEP5_MEDIAPIPE_MAX_FACES")) or args.mp_landmarker_num_faces),
        min_face_detection_confidence=args.mp_landmarker_min_face_detection_confidence,
        min_face_presence_confidence=args.mp_landmarker_min_face_presence_confidence,
        min_tracking_confidence=args.mp_landmarker_min_tracking_confidence,
        output_face_blendshapes=True
    )

    object_options = ObjectDetectorOptions(
        base_options=BaseOptions(model_asset_path=str(object_model_path), delegate=delegate),
        running_mode=VisionRunningMode.VIDEO,
        max_results=getattr(args, 'object_max_results', 5),
        score_threshold=getattr(args, 'object_score_threshold', 0.5)
    )

    # Use safe video processing with automatic resource cleanup
    try:
        with safe_video_processing(args.video_file_path) as (video_capture, temp_manager):
            # Get video metadata safely
            fps = video_capture.get(cv2.CAP_PROP_FPS)
            total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))

            logging.info(f"Video metadata - FPS: {fps}, Total frames: {total_frames}")

            # Register video capture for tracking
            resource_id = resource_tracker.register_resource(
                video_capture, 'video_capture', f"Processing {Path(args.video_file_path).name}"
            )

            try:
                with FaceLandmarker.create_from_options(face_options) as landmarker, \
                     ObjectDetector.create_from_options(object_options) as object_detector:

                    final_output = {
                        "metadata": {
                            "video_path": args.video_file_path,
                            "total_frames": total_frames,
                            "fps": fps
                        },
                        "frames": []
                    }
                    tracked_objects, next_id_counter = {}, {'value': 0}

                    # Fallback tracking variables
                    face_detection_success_count = 0
                    frames_processed = 0
                    use_object_detection_fallback = getattr(args, 'enable_object_detection', False)
                    fallback_threshold = 50  # Check every 50 frames for fallback decision

                    # Initialize enhanced speaking detector
                    enhanced_speaking_detector = None
                    # Speaking detector activé par défaut
                    if getattr(args, 'speaking_detection_enabled', True):
                        try:
                            enhanced_speaking_detector = EnhancedSpeakingDetector(
                                video_path=args.video_file_path,
                                jaw_threshold=args.speaking_detection_jaw_open_threshold
                            )
                            logging.info("Enhanced speaking detection initialized successfully")
                            logging.info(f"Detection stats: {enhanced_speaking_detector.get_detection_stats()}")
                        except Exception as e:
                            logging.warning(f"Failed to initialize enhanced speaking detector: {e}")
                            enhanced_speaking_detector = None

                    # Check if multi-threading should be used (CPU workers with > 1 internal workers)
                    use_multithreading = (not args.use_gpu and
                                        getattr(args, 'mp_num_workers_internal', 1) > 1)

                    if use_multithreading:
                        logging.info(f"Using multi-threaded processing with {args.mp_num_workers_internal} workers")
                        final_output = process_video_multithreaded(
                            args, video_capture, landmarker, object_detector,
                            enhanced_speaking_detector, total_frames
                        )
                    else:
                        logging.info("Using sequential processing")
                        # Sequential processing (original logic)
                        frame_idx = 0
                        while video_capture.isOpened():
                            ret, frame = video_capture.read()
                            if not ret:
                                break

                            mp_image = mp.Image(
                                image_format=mp.ImageFormat.SRGB,
                                data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            )
                            timestamp_ms = int(video_capture.get(cv2.CAP_PROP_POS_MSEC))

                            # Try face detection first
                            face_result = landmarker.detect_for_video(mp_image, timestamp_ms)
                            frames_processed += 1

                            current_detections = []
                            face_detected = False

                            if face_result.face_landmarks:
                                face_detected = True
                                face_detection_success_count += 1

                                for i, landmarks in enumerate(face_result.face_landmarks):
                                    h, w, _ = frame.shape
                                    x_coords = [lm.x * w for lm in landmarks]
                                    y_coords = [lm.y * h for lm in landmarks]
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
                                        det["blendshapes"] = {
                                            cat.category_name: cat.score
                                            for cat in face_result.face_blendshapes[i]
                                        }
                                    current_detections.append(det)

                            # Check if we should enable object detection fallback
                            if frames_processed % fallback_threshold == 0:
                                face_success_rate = face_detection_success_count / frames_processed
                                if face_success_rate < 0.1:  # Less than 10% face detection success
                                    if not use_object_detection_fallback:
                                        logging.info(f"Low face detection rate ({face_success_rate:.2%}). Enabling object detection fallback.")
                                        use_object_detection_fallback = True

                            # Use object detection fallback if no faces detected and fallback is enabled
                            if not face_detected and use_object_detection_fallback:
                                try:
                                    object_result = object_detector.detect_for_video(mp_image, timestamp_ms)

                                    if object_result.detections:
                                        for detection in object_result.detections:
                                            bbox = detection.bounding_box
                                            # MediaPipe object detection returns coordinates already in pixel format
                                            # No conversion needed - use values directly
                                            x_min = int(bbox.origin_x)
                                            y_min = int(bbox.origin_y)
                                            width = int(bbox.width)
                                            height = int(bbox.height)

                                            centroid = (x_min + width // 2, y_min + height // 2)

                                            # Get the best category
                                            best_category = detection.categories[0] if detection.categories else None
                                            label = best_category.category_name if best_category else "object"
                                            confidence = best_category.score if best_category else 0.0

                                            det = {
                                                "bbox": (x_min, y_min, width, height),
                                                "centroid": centroid,
                                                "source_detector": "object_detector",
                                                "label": label,
                                                "confidence": confidence,
                                                "blendshapes": None,  # Not applicable for objects
                                                "is_speaking": None   # Not applicable for objects
                                            }
                                            current_detections.append(det)
                                except Exception as e:
                                    logging.warning(f"Object detection failed for frame {frame_idx + 1}: {e}")

                            tracked_for_frame = apply_tracking_and_management(
                                tracked_objects, current_detections, next_id_counter,
                                args.mp_max_distance_tracking, args.mp_frames_unseen_deregister,
                                args.speaking_detection_jaw_open_threshold,
                                enhanced_speaking_detector=enhanced_speaking_detector,
                                current_frame_num=frame_idx + 1
                            )

                            # Always export frame data to maintain consistent structure
                            # Even if no objects are tracked, we include the frame with empty tracked_objects
                            final_output["frames"].append({
                                "frame": frame_idx + 1,
                                "tracked_objects": tracked_for_frame if tracked_for_frame else []
                            })

                            frame_idx += 1
                            if frame_idx % 50 == 0:
                                progress_percent = int((frame_idx / total_frames) * 100)
                                print(f"[Progression]|{progress_percent}|{frame_idx}|{total_frames}", flush=True)

                        # Log processing summary for sequential processing
                        face_success_rate = face_detection_success_count / frames_processed if frames_processed > 0 else 0
                        logging.info(f"Processing summary:")
                        logging.info(f"  Total frames processed: {frames_processed}")
                        logging.info(f"  Frames with faces: {face_detection_success_count}")
                        logging.info(f"  Face detection success rate: {face_success_rate:.2%}")
                        logging.info(f"  Object detection fallback used: {use_object_detection_fallback}")
                        logging.info(f"  Total frames exported: {len(final_output['frames'])}")

            finally:
                # Unregister the video capture resource
                resource_tracker.unregister_resource(resource_id)

    except Exception as e:
        logging.error(f"Error processing video {args.video_file_path}: {e}")
        raise

    # Save output with proper error handling
    output_path = Path(args.video_file_path).with_suffix('.json')
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(final_output, f, indent=2, ensure_ascii=False)
        logging.info(f"Traitement terminé. JSON sauvegardé: {output_path.name}")
        print(f"[Progression]|100|{total_frames}|{total_frames}", flush=True)
    except Exception as e:
        logging.error(f"Failed to save output file {output_path}: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Worker séquentiel pour MediaPipe.")
    parser.add_argument("video_file_path")
    parser.add_argument("--models_dir", required=True)
    parser.add_argument("--use_gpu", action="store_true")
    parser.add_argument("--tracking_engine", default=None, help="Tracking engine: mediapipe_landmarker (default), opencv_haar, opencv_yunet")
    # Conserver les arguments pour la compatibilité avec le manager, même s'ils ne sont pas tous utilisés
    parser.add_argument("--mp_landmarker_num_faces", type=int, default=1)
    parser.add_argument("--mp_landmarker_min_face_detection_confidence", type=float, default=0.5)
    parser.add_argument("--mp_landmarker_min_face_presence_confidence", type=float, default=0.3)
    parser.add_argument("--mp_landmarker_min_tracking_confidence", type=float, default=0.5)
    parser.add_argument("--mp_landmarker_output_blendshapes", action="store_true")
    parser.add_argument("--mp_max_distance_tracking", type=int, default=70)
    parser.add_argument("--mp_frames_unseen_deregister", type=int, default=7)
    parser.add_argument("--speaking_detection_jaw_open_threshold", type=float, default=0.08)
    parser.add_argument("--speaking_detection_enabled", action="store_true", default=True, help="Enable enhanced speaking detection module (enabled by default)")
    # Object detection parameters
    parser.add_argument("--enable_object_detection", action="store_true", help="Enable object detection fallback")
    parser.add_argument("--object_score_threshold", type=float, default=0.5, help="Object detection confidence threshold")
    parser.add_argument("--object_max_results", type=int, default=5, help="Maximum number of objects to detect")
    # Multi-threading parameter for CPU workers
    parser.add_argument("--mp_num_workers_internal", type=int, default=1, help="Number of internal worker threads for CPU processing")

    args, _ = parser.parse_known_args()

    try:
        main(args)
        sys.exit(0)
    except Exception as e:
        logging.error(f"Erreur critique dans le worker: {e}", exc_info=True)
        sys.exit(1)