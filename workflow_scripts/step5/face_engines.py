import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

# Load .env file BEFORE reading any environment variables (critical for multiprocessing workers)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass  # dotenv not available, rely on system env vars

logger = logging.getLogger(__name__)

ARKIT_52_BLENDSHAPE_NAMES = [
    "browDownLeft",
    "browDownRight",
    "browInnerUp",
    "browOuterUpLeft",
    "browOuterUpRight",
    "cheekPuff",
    "cheekSquintLeft",
    "cheekSquintRight",
    "eyeBlinkLeft",
    "eyeBlinkRight",
    "eyeLookDownLeft",
    "eyeLookDownRight",
    "eyeLookInLeft",
    "eyeLookInRight",
    "eyeLookOutLeft",
    "eyeLookOutRight",
    "eyeLookUpLeft",
    "eyeLookUpRight",
    "eyeSquintLeft",
    "eyeSquintRight",
    "eyeWideLeft",
    "eyeWideRight",
    "jawForward",
    "jawLeft",
    "jawOpen",
    "jawRight",
    "mouthClose",
    "mouthDimpleLeft",
    "mouthDimpleRight",
    "mouthFrownLeft",
    "mouthFrownRight",
    "mouthFunnel",
    "mouthLeft",
    "mouthLowerDownLeft",
    "mouthLowerDownRight",
    "mouthPressLeft",
    "mouthPressRight",
    "mouthPucker",
    "mouthRight",
    "mouthRollLower",
    "mouthRollUpper",
    "mouthShrugLower",
    "mouthShrugUpper",
    "mouthSmileLeft",
    "mouthSmileRight",
    "mouthStretchLeft",
    "mouthStretchRight",
    "mouthUpperUpLeft",
    "mouthUpperUpRight",
    "noseSneerLeft",
    "noseSneerRight",
    "tongueOut",
]


def _parse_optional_positive_int(raw: Optional[str]) -> Optional[int]:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except Exception:
        return None
    if value <= 0:
        return None
    return value


def _apply_jawopen_scale(blendshapes: Optional[dict], scale: float) -> Optional[dict]:
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


def _openseeface_logit_arr(p: np.ndarray, factor: float = 16.0) -> np.ndarray:
    p = np.clip(p, 0.0000001, 0.9999999)
    return np.log(p / (1 - p)) / float(factor)


class OpenSeeFaceEngine:
    def __init__(
        self,
        models_dir: Optional[str] = None,
        model_id: Optional[int] = None,
        detection_threshold: Optional[float] = None,
        max_faces: Optional[int] = None,
        use_gpu: bool = False,
    ):
        self._lock = threading.Lock()

        try:
            import onnxruntime as ort
        except ImportError as e:
            raise RuntimeError(
                "OpenSeeFace engine requires onnxruntime. Install it in tracking_env."
            ) from e

        self._ort = ort
        self._use_gpu = use_gpu
        self._frame_counter = 0
        self._last_detections = []

        self._enable_profiling = os.environ.get("STEP5_ENABLE_PROFILING", "0").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        self._profiling_stats = {
            "resize_total": 0.0,
            "detect_total": 0.0,
            "landmarks_total": 0.0,
            "post_total": 0.0,
            "frame_count": 0,
        }

        env_models_dir = os.environ.get("STEP5_OPENSEEFACE_MODELS_DIR")
        models_dir_raw = models_dir or (env_models_dir.strip() if env_models_dir else "")
        if models_dir_raw:
            self._models_dir_explicit = True
            models_dir_candidate = Path(models_dir_raw)
            if models_dir_candidate.is_absolute() and models_dir_candidate.exists():
                self._models_dir = models_dir_candidate
            elif models_dir_candidate.exists():
                self._models_dir = models_dir_candidate.resolve()
            else:
                step5_dir = Path(__file__).resolve().parent
                project_root = step5_dir.parent.parent
                resolved_models_dir = None
                for c in [project_root / models_dir_candidate, step5_dir / models_dir_candidate]:
                    if c.exists():
                        resolved_models_dir = c
                        break
                self._models_dir = (resolved_models_dir or models_dir_candidate).resolve()
        else:
            self._models_dir_explicit = False
            step5_dir = Path(__file__).resolve().parent
            self._models_dir = step5_dir / "models" / "engines" / "openseeface"

        env_model_id = os.environ.get("STEP5_OPENSEEFACE_MODEL_ID")
        self._model_id = int(model_id if model_id is not None else (env_model_id or "1"))

        env_detect_every = os.environ.get("STEP5_OPENSEEFACE_DETECT_EVERY_N")
        env_blendshapes_throttle = os.environ.get("STEP5_BLENDSHAPES_THROTTLE_N")
        detect_every_raw = env_detect_every if (env_detect_every is not None and env_detect_every.strip()) else env_blendshapes_throttle
        self._detect_every_n = max(1, int(detect_every_raw or "1"))

        env_max_faces = os.environ.get("STEP5_OPENSEEFACE_MAX_FACES")
        self._max_faces = max(1, int(max_faces if max_faces is not None else (env_max_faces or "1")))

        env_detection_threshold = os.environ.get("STEP5_OPENSEEFACE_DETECTION_THRESHOLD")
        self._detection_threshold = float(
            detection_threshold if detection_threshold is not None else (env_detection_threshold or "0.6")
        )

        env_jaw_scale = os.environ.get("STEP5_OPENSEEFACE_JAWOPEN_SCALE")
        self._jaw_open_scale = float(env_jaw_scale or "1.0")

        try:
            cv2.setNumThreads(1)
        except Exception:
            pass

        env_openseeface_max_width = os.environ.get("STEP5_OPENSEEFACE_MAX_WIDTH")
        self._max_detection_width = max(
            1,
            int(
                (env_openseeface_max_width.strip() if env_openseeface_max_width else "")
                or os.environ.get("STEP5_YUNET_MAX_WIDTH", "640")
            ),
        )

        detection_override_path = os.environ.get("STEP5_OPENSEEFACE_DETECTION_MODEL_PATH")
        landmark_override_path = os.environ.get("STEP5_OPENSEEFACE_LANDMARK_MODEL_PATH")

        self._detection_model_path = self._resolve_model_path(
            detection_override_path,
            default_filename="mnv3_detection_opt.onnx",
        )
        self._landmark_model_path = self._resolve_model_path(
            landmark_override_path,
            default_filename=f"lm_model{self._model_id}_opt.onnx",
        )

        if not self._detection_model_path:
            raise RuntimeError(
                "OpenSeeFace detection model not found. Set STEP5_OPENSEEFACE_DETECTION_MODEL_PATH or "
                "STEP5_OPENSEEFACE_MODELS_DIR with mnv3_detection_opt.onnx."
            )
        if not self._landmark_model_path:
            raise RuntimeError(
                "OpenSeeFace landmark model not found. Set STEP5_OPENSEEFACE_LANDMARK_MODEL_PATH or "
                "STEP5_OPENSEEFACE_MODELS_DIR with lm_model{N}_opt.onnx."
            )

        intra_threads = int(os.environ.get("STEP5_ONNX_INTRA_OP_THREADS", "2"))
        inter_threads = int(os.environ.get("STEP5_ONNX_INTER_OP_THREADS", "1"))

        # Configure ONNX providers (GPU or CPU)
        available_providers = ort.get_available_providers()
        logger.info(f"[OpenSeeFace] Available ONNXRuntime providers: {available_providers}")

        if use_gpu:
            providers = ["CUDAExecutionProvider"]
            logger.info("[OpenSeeFace] Attempting to use CUDA provider for GPU inference (no CPU fallback)")
        else:
            providers = ["CPUExecutionProvider"]

        detection_sess_options = ort.SessionOptions()
        detection_sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        if use_gpu:
            try:
                detection_sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
                detection_sess_options.add_session_config_entry("session.disable_contrib_ops", "1")
                detection_sess_options.add_session_config_entry("session.disable_prepacking", "1")
                detection_sess_options.add_session_config_entry("session.disable_aot_function_inlining", "1")
                logger.info("[OpenSeeFace] Disabled contrib/fused ops to improve CUDA compatibility")
            except Exception as cfg_err:
                logger.warning("[OpenSeeFace] Failed to set session config entries: %s", cfg_err)
        detection_sess_options.intra_op_num_threads = max(1, int(intra_threads))
        detection_sess_options.inter_op_num_threads = max(1, int(inter_threads))
        detection_sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

        def _create_session(model_path: Path, sess_options: "ort.SessionOptions", provider_list: list[str]):
            return ort.InferenceSession(
                str(model_path),
                sess_options=sess_options,
                providers=provider_list,
            )

        try:
            self._detection_session = _create_session(self._detection_model_path, detection_sess_options, providers)
        except Exception as session_error:
            logger.exception(
                "[OpenSeeFace] Failed to create detection session with providers %s: %s",
                providers,
                session_error,
            )
            if use_gpu:
                logger.warning("[OpenSeeFace] Falling back to CPUExecutionProvider due to CUDA initialization failure")
                providers = ["CPUExecutionProvider"]
                self._use_gpu = False
                self._detection_session = _create_session(self._detection_model_path, detection_sess_options, providers)
            else:
                raise
        self._detection_input_name = self._detection_session.get_inputs()[0].name
        
        # Log active provider
        active_provider = self._detection_session.get_providers()[0]
        logger.info(f"[OpenSeeFace] Detection session using provider: {active_provider}")
        if use_gpu and active_provider != "CUDAExecutionProvider":
            logger.error("[OpenSeeFace] CUDA provider requested but not active despite GPU mode (should have failed)")

        landmark_sess_options = ort.SessionOptions()
        landmark_sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        landmark_sess_options.intra_op_num_threads = max(1, int(intra_threads))
        landmark_sess_options.inter_op_num_threads = max(1, int(inter_threads))
        landmark_sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

        try:
            self._landmark_session = ort.InferenceSession(
                str(self._landmark_model_path),
                sess_options=landmark_sess_options,
                providers=providers,
            )
        except Exception as session_error:
            logger.exception(
                "[OpenSeeFace] Failed to create landmark session with providers %s: %s",
                providers,
                session_error,
            )
            raise
        self._landmark_input_name = self._landmark_session.get_inputs()[0].name
        
        active_provider_lm = self._landmark_session.get_providers()[0]
        logger.info(f"[OpenSeeFace] Landmark session using provider: {active_provider_lm}")

        self._mean = np.float32(np.array([0.485, 0.456, 0.406]))
        self._std = np.float32(np.array([0.229, 0.224, 0.225]))
        mean = (self._mean / self._std)
        std = (self._std * 255.0)
        self._mean = -mean
        self._std = 1.0 / std

        self._mean_224 = np.tile(self._mean, [224, 224, 1])
        self._std_224 = np.tile(self._std, [224, 224, 1])

        self._res = 224.0
        self._out_res = 27.0
        self._out_res_i = int(self._out_res) + 1
        self._logit_factor = 16.0

    def _resolve_model_path(self, override_path: Optional[str], default_filename: str) -> Optional[Path]:
        if override_path:
            candidate = Path(override_path)
            if candidate.is_absolute() and candidate.exists():
                return candidate
            if candidate.exists():
                return candidate.resolve()

            step5_dir = Path(__file__).resolve().parent
            project_root = step5_dir.parent.parent
            for c in [project_root / candidate, step5_dir / candidate]:
                if c.exists():
                    return c

        candidate = self._models_dir / default_filename
        if candidate.exists():
            return candidate

        if getattr(self, "_models_dir_explicit", False):
            return None

        step5_dir = Path(__file__).resolve().parent
        fallback_candidates = [
            step5_dir / "models" / "engines" / "openseeface" / default_filename,
            step5_dir / "models" / default_filename,
        ]
        for fallback in fallback_candidates:
            if fallback.exists():
                return fallback

        return None

    def _preprocess_detection(self, frame_bgr: np.ndarray) -> np.ndarray:
        resized = cv2.resize(frame_bgr, (224, 224), interpolation=cv2.INTER_LINEAR)
        rgb = resized[:, :, ::-1].astype(np.float32)
        im = rgb * self._std_224 + self._mean_224
        im = np.expand_dims(im, 0)
        im = np.transpose(im, (0, 3, 1, 2))
        return np.ascontiguousarray(im)

    def _detect_faces(self, frame_bgr: np.ndarray) -> list[tuple[float, float, float, float, float]]:
        im = self._preprocess_detection(frame_bgr)
        outputs = self._detection_session.run([], {self._detection_input_name: im})
        if not outputs or len(outputs) < 2:
            return []
        out_map = np.array(outputs[0])
        maxpool = np.array(outputs[1])
        if out_map.ndim != 4 or maxpool.ndim != 4:
            return []
        out_map[0, 0, out_map[0, 0] != maxpool[0, 0]] = 0

        detections = np.flip(np.argsort(out_map[0, 0].flatten()))
        results = []
        for det in detections[0 : self._max_faces]:
            y = int(det // 56)
            x = int(det % 56)
            conf = float(out_map[0, 0, y, x])
            radius = float(out_map[0, 1, y, x]) * 112.0
            x_px = float(x * 4)
            y_px = float(y * 4)
            if conf < self._detection_threshold:
                break
            results.append((x_px - radius, y_px - radius, 2 * radius, 2 * radius, conf))

        if not results:
            return []

        results_np = np.array([r[:4] for r in results], dtype=np.float32)
        results_np[:, [0, 2]] *= (frame_bgr.shape[1] / 224.0)
        results_np[:, [1, 3]] *= (frame_bgr.shape[0] / 224.0)
        scaled = []
        for i, (x, y, w, h) in enumerate(results_np.tolist()):
            scaled.append((x, y, w, h, float(results[i][4])))
        return scaled

    def _preprocess_landmarks(
        self,
        frame_bgr: np.ndarray,
        crop: tuple[int, int, int, int],
    ) -> tuple[np.ndarray, tuple[int, int, float, float]]:
        x1, y1, x2, y2 = crop
        im = frame_bgr[y1:y2, x1:x2, ::-1].astype(np.float32)
        im = cv2.resize(im, (int(self._res), int(self._res)), interpolation=cv2.INTER_LINEAR)
        im = im * np.tile(self._std, [int(self._res), int(self._res), 1]) + np.tile(
            self._mean, [int(self._res), int(self._res), 1]
        )
        im = np.expand_dims(im, 0)
        im = np.transpose(im, (0, 3, 1, 2))
        im = np.ascontiguousarray(im)

        scale_x = float(x2 - x1) / float(self._res)
        scale_y = float(y2 - y1) / float(self._res)
        return im, (x1, y1, scale_x, scale_y)

    def _decode_landmarks(self, tensor: np.ndarray, crop_info: tuple[int, int, float, float]) -> tuple[float, np.ndarray]:
        crop_x1, crop_y1, scale_x, scale_y = crop_info
        res = self._res - 1

        c0, c1, c2 = 66, 132, 198
        t_main = tensor[0:c0].reshape((c0, self._out_res_i * self._out_res_i))
        t_m = t_main.argmax(1)
        indices = np.expand_dims(t_m, 1)
        t_conf = np.take_along_axis(t_main, indices, 1).reshape((c0,))

        t_off_x = np.take_along_axis(
            tensor[c0:c1].reshape((c0, self._out_res_i * self._out_res_i)),
            indices,
            1,
        ).reshape((c0,))
        t_off_y = np.take_along_axis(
            tensor[c1:c2].reshape((c0, self._out_res_i * self._out_res_i)),
            indices,
            1,
        ).reshape((c0,))
        t_off_x = res * _openseeface_logit_arr(t_off_x, self._logit_factor)
        t_off_y = res * _openseeface_logit_arr(t_off_y, self._logit_factor)

        t_x = crop_y1 + scale_y * (res * np.floor(t_m / self._out_res_i) / self._out_res + t_off_x)
        t_y = crop_x1 + scale_x * (res * np.floor(np.mod(t_m, self._out_res_i)) / self._out_res + t_off_y)
        avg_conf = float(np.average(t_conf))
        lms_yx_conf = np.stack([t_x, t_y, t_conf], 1)
        if np.isnan(lms_yx_conf).any():
            lms_yx_conf[np.isnan(lms_yx_conf).any(axis=1)] = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        return avg_conf, lms_yx_conf

    def _compute_jaw_open(self, landmarks_xy: np.ndarray) -> float:
        if landmarks_xy.shape[0] < 66:
            return 0.0

        norm_distance_y = float(
            np.mean(
                [
                    landmarks_xy[27, 1] - landmarks_xy[28, 1],
                    landmarks_xy[28, 1] - landmarks_xy[29, 1],
                    landmarks_xy[29, 1] - landmarks_xy[30, 1],
                ]
            )
        )
        denom = max(abs(norm_distance_y), 1e-6)

        upper = float(np.mean(landmarks_xy[[59, 60, 61], 1], axis=0))
        lower = float(np.mean(landmarks_xy[[63, 64, 65], 1], axis=0))
        mouth_open_ratio = abs(upper - lower) / denom
        return float(np.clip(mouth_open_ratio * self._jaw_open_scale, 0.0, 1.0))

    def _build_arkit_blendshapes(self, jaw_open: float) -> dict:
        out = {}
        for name in ARKIT_52_BLENDSHAPE_NAMES:
            out[name] = 0.0
        out["jawOpen"] = float(jaw_open)
        return out

    def detect(self, frame_bgr):
        self._frame_counter += 1
        if (self._frame_counter % self._detect_every_n) != 0:
            return list(self._last_detections)

        if frame_bgr is None or getattr(frame_bgr, "shape", None) is None:
            self._last_detections = []
            return []

        orig_h, orig_w = frame_bgr.shape[:2]

        t_resize_start = time.perf_counter() if self._enable_profiling else 0.0
        work_frame = frame_bgr
        scale_x = 1.0
        scale_y = 1.0

        if orig_w > self._max_detection_width:
            detect_w = self._max_detection_width
            scale_factor = detect_w / float(orig_w)
            detect_h = max(1, int(orig_h * scale_factor))
            work_frame = cv2.resize(frame_bgr, (detect_w, detect_h), interpolation=cv2.INTER_LINEAR)
            scale_x = orig_w / float(detect_w)
            scale_y = orig_h / float(detect_h)

        if self._enable_profiling:
            self._profiling_stats["resize_total"] += time.perf_counter() - t_resize_start

        work_h, work_w = work_frame.shape[:2]

        t_detect_start = time.perf_counter() if self._enable_profiling else 0.0
        faces = self._detect_faces(work_frame)
        if self._enable_profiling:
            self._profiling_stats["detect_total"] += time.perf_counter() - t_detect_start
        if not faces:
            self._last_detections = []
            return []

        detections = []
        for (x, y, bw, bh, conf) in faces:
            t_landmarks_start = time.perf_counter() if self._enable_profiling else 0.0
            x1 = int(max(0, x - 0.1 * bw))
            y1 = int(max(0, y - 0.125 * bh))
            x2 = int(min(work_w, x + bw + 0.1 * bw))
            y2 = int(min(work_h, y + bh + 0.125 * bh))
            if x2 - x1 < 4 or y2 - y1 < 4:
                continue

            with self._lock:
                input_tensor, crop_info = self._preprocess_landmarks(work_frame, (x1, y1, x2, y2))
                out = self._landmark_session.run([], {self._landmark_input_name: input_tensor})[0]

            if out is None:
                continue

            if out.ndim == 4:
                tensor = out[0]
            else:
                tensor = out

            avg_conf, lms_yx_conf = self._decode_landmarks(np.asarray(tensor), crop_info)

            if self._enable_profiling:
                self._profiling_stats["landmarks_total"] += time.perf_counter() - t_landmarks_start

            landmarks_xy = np.stack([lms_yx_conf[:, 1], lms_yx_conf[:, 0]], axis=1)

            t_post_start = time.perf_counter() if self._enable_profiling else 0.0
            if scale_x != 1.0 or scale_y != 1.0:
                landmarks_xy = landmarks_xy.astype(np.float32, copy=True)
                landmarks_xy[:, 0] *= float(scale_x)
                landmarks_xy[:, 1] *= float(scale_y)
                logger.debug(f"OpenSeeFace upscale: landmarks rescaled by x={scale_x:.2f}, y={scale_y:.2f}")

            x_min = int(max(0, np.min(landmarks_xy[:, 0])))
            y_min = int(max(0, np.min(landmarks_xy[:, 1])))
            x_max = int(min(orig_w - 1, np.max(landmarks_xy[:, 0])))
            y_max = int(min(orig_h - 1, np.max(landmarks_xy[:, 1])))
            bbox_w = max(0, x_max - x_min)
            bbox_h = max(0, y_max - y_min)

            centroid = (x_min + (bbox_w // 2), y_min + (bbox_h // 2))
            jaw_open = self._compute_jaw_open(landmarks_xy)

            landmarks_xyz = np.zeros((int(lms_yx_conf.shape[0]), 3), dtype=np.float32)
            landmarks_xyz[:, 0] = landmarks_xy[:, 0]
            landmarks_xyz[:, 1] = landmarks_xy[:, 1]

            detections.append(
                {
                    "bbox": (x_min, y_min, bbox_w, bbox_h),
                    "centroid": centroid,
                    "source_detector": "face_landmarker",
                    "label": "face",
                    "confidence": float(avg_conf if avg_conf > 0 else conf),
                    "landmarks": landmarks_xyz.tolist(),
                    "blendshapes": self._build_arkit_blendshapes(jaw_open),
                }
            )

            if self._enable_profiling:
                self._profiling_stats["post_total"] += time.perf_counter() - t_post_start

        self._last_detections = detections

        if self._enable_profiling:
            self._profiling_stats["frame_count"] += 1
            if (self._profiling_stats["frame_count"] % 20) == 0:
                self._log_profiling_stats()

        return detections

    def _log_profiling_stats(self) -> None:
        frame_count = int(self._profiling_stats.get("frame_count", 0) or 0)
        if frame_count <= 0:
            return

        resize_ms = (self._profiling_stats["resize_total"] / frame_count) * 1000.0
        detect_ms = (self._profiling_stats["detect_total"] / frame_count) * 1000.0
        landmarks_ms = (self._profiling_stats["landmarks_total"] / frame_count) * 1000.0
        post_ms = (self._profiling_stats["post_total"] / frame_count) * 1000.0

        logger.info(
            "[PROFILING] OpenSeeFace after %s frames: resize=%.2fms/frame, detect=%.2fms/frame, "
            "landmarks=%.2fms/frame, post=%.2fms/frame",
            frame_count,
            resize_ms,
            detect_ms,
            landmarks_ms,
            post_ms,
        )


class InsightFaceEngine:
    def __init__(
        self,
        model_name: Optional[str] = None,
        det_size: Optional[int] = None,
        use_gpu: bool = False,
    ):
        if not use_gpu:
            raise RuntimeError(
                "InsightFace engine is GPU-only. Set STEP5_ENABLE_GPU=1, include 'insightface' in STEP5_GPU_ENGINES, "
                "and run with use_gpu=True."
            )

        self._lock = threading.Lock()
        self._use_gpu = True

        try:
            import onnxruntime as ort
        except ImportError as e:
            raise RuntimeError(
                "InsightFace engine requires onnxruntime in insightface_env. Install it (and onnxruntime-gpu) in that venv."
            ) from e

        available_providers = ort.get_available_providers()
        logger.info(f"[InsightFace] Available ONNXRuntime providers: {available_providers}")
        if "CUDAExecutionProvider" not in available_providers:
            raise RuntimeError(
                "InsightFace engine requires CUDAExecutionProvider (onnxruntime-gpu). "
                "Install onnxruntime-gpu in insightface_env and ensure CUDA libs are available."
            )

        try:
            from insightface.app import FaceAnalysis
        except ImportError as e:
            raise RuntimeError(
                "InsightFace engine requires the 'insightface' Python package inside insightface_env."
            ) from e

        self._enable_profiling = os.environ.get("STEP5_ENABLE_PROFILING", "0").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        self._profiling_stats = {
            "resize_total": 0.0,
            "detect_total": 0.0,
            "post_total": 0.0,
            "frame_count": 0,
        }

        env_max_faces = os.environ.get("STEP5_INSIGHTFACE_MAX_FACES")
        self._max_faces = _parse_optional_positive_int(env_max_faces)

        env_max_width = os.environ.get("STEP5_INSIGHTFACE_MAX_WIDTH")
        if env_max_width is None or env_max_width.strip() == "":
            env_max_width = os.environ.get("STEP5_YUNET_MAX_WIDTH", "1280")
        self._max_detection_width = max(1, int(str(env_max_width).strip() or "1280"))

        env_detect_every = os.environ.get("STEP5_INSIGHTFACE_DETECT_EVERY_N")
        if env_detect_every is None or env_detect_every.strip() == "":
            env_detect_every = os.environ.get("STEP5_BLENDSHAPES_THROTTLE_N", "1")
        self._detect_every_n = max(1, int(str(env_detect_every).strip() or "1"))

        self._jaw_open_scale = float(os.environ.get("STEP5_INSIGHTFACE_JAWOPEN_SCALE", "1.0"))

        env_model_name = os.environ.get("STEP5_INSIGHTFACE_MODEL_NAME")
        self._model_name = (model_name or (env_model_name.strip() if env_model_name else "") or "antelopev2")

        env_det_size = os.environ.get("STEP5_INSIGHTFACE_DET_SIZE")
        det_size_value = det_size
        if det_size_value is None:
            try:
                det_size_value = int(str(env_det_size).strip()) if env_det_size else 640
            except Exception:
                det_size_value = 640
        self._det_size = max(64, int(det_size_value))

        ctx_id_raw = os.environ.get("STEP5_INSIGHTFACE_CTX_ID")
        try:
            ctx_id = int(str(ctx_id_raw).strip()) if ctx_id_raw else 0
        except Exception:
            ctx_id = 0
        if ctx_id < 0:
            ctx_id = 0

        providers = ["CUDAExecutionProvider"]
        insightface_root_raw = os.environ.get("INSIGHTFACE_HOME", "").strip()
        insightface_root = str(Path(insightface_root_raw or "~/.insightface").expanduser())

        allowed_modules_env = os.environ.get("STEP5_INSIGHTFACE_ALLOWED_MODULES", "").strip()
        allowed_modules = None
        if allowed_modules_env:
            allowed_modules = [m.strip() for m in allowed_modules_env.split(",") if m.strip()]
            if "detection" not in allowed_modules:
                raise RuntimeError(
                    "STEP5_INSIGHTFACE_ALLOWED_MODULES must include 'detection' (required by FaceAnalysis)."
                )

        try:
            self._app = FaceAnalysis(
                name=self._model_name,
                root=insightface_root,
                providers=providers,
                allowed_modules=allowed_modules,
            )
        except FileExistsError as e:
            model_dir = Path(insightface_root) / "models" / self._model_name
            quarantine_suffix = f"corrupt_{int(time.time())}"
            quarantine_dir = model_dir.with_name(f"{model_dir.name}.{quarantine_suffix}")
            try:
                if model_dir.exists():
                    model_dir.rename(quarantine_dir)
                    logger.warning(
                        "[InsightFace] Model cache directory already exists but download attempted; "
                        "quarantined %s -> %s and retrying initialization.",
                        model_dir,
                        quarantine_dir,
                    )
            except Exception as rename_err:
                raise RuntimeError(
                    f"InsightFace model cache appears corrupted at {model_dir}. "
                    f"Automatic quarantine failed ({rename_err}). "
                    "Please remove or rename the directory and retry."
                ) from e

            self._app = FaceAnalysis(
                name=self._model_name,
                root=insightface_root,
                providers=providers,
                allowed_modules=allowed_modules,
            )
        self._app.prepare(ctx_id=ctx_id, det_size=(self._det_size, self._det_size))

        self._frame_counter = 0
        self._last_detections = []

        logger.info(
            f"[InsightFace] Initialized model_name={self._model_name}, det_size={self._det_size}, "
            f"max_width={self._max_detection_width}, max_faces={self._max_faces}, detect_every_n={self._detect_every_n}"
        )

    def _build_arkit_blendshapes(self, jaw_open: float) -> dict:
        out = {}
        for name in ARKIT_52_BLENDSHAPE_NAMES:
            out[name] = 0.0
        out["jawOpen"] = float(jaw_open)
        return out

    def _compute_jaw_open_from_dlib68(self, landmarks_68: np.ndarray) -> float:
        lm = np.asarray(landmarks_68, dtype=np.float32)
        if lm.ndim != 2 or lm.shape[0] < 68:
            return 0.0
        try:
            upper_inner = float(np.mean(lm[60:65, 1], axis=0))
            lower_inner = float(np.mean(lm[65:68, 1], axis=0))
            mouth_open = abs(lower_inner - upper_inner)

            nose_y = float(lm[33, 1])
            chin_y = float(lm[8, 1])
            denom = max(abs(chin_y - nose_y), 1e-6)
            ratio = (mouth_open / denom) * float(self._jaw_open_scale)
            return float(np.clip(ratio, 0.0, 1.0))
        except Exception:
            return 0.0

    def _get_face_landmarks_68(self, face_obj) -> Optional[np.ndarray]:
        candidates = [
            "landmark_3d_68",
            "landmark_2d_68",
        ]
        for attr in candidates:
            try:
                val = getattr(face_obj, attr, None)
            except Exception:
                val = None
            if val is None:
                try:
                    val = face_obj.get(attr) if hasattr(face_obj, "get") else None
                except Exception:
                    val = None
            if val is None:
                continue

            lm = np.asarray(val)
            if lm.ndim != 2 or lm.shape[0] < 68:
                continue
            if lm.shape[1] >= 2:
                return lm[:, :2].astype(np.float32)
        return None

    def detect(self, frame_bgr):
        self._frame_counter += 1
        if (self._frame_counter % self._detect_every_n) != 0:
            return list(self._last_detections)

        if frame_bgr is None or getattr(frame_bgr, "shape", None) is None:
            self._last_detections = []
            return []

        orig_h, orig_w = frame_bgr.shape[:2]
        work_frame = frame_bgr
        scale_x = 1.0
        scale_y = 1.0

        t_resize_start = time.perf_counter() if self._enable_profiling else 0.0
        if orig_w > self._max_detection_width:
            detect_w = self._max_detection_width
            scale_factor = detect_w / float(orig_w)
            detect_h = max(1, int(orig_h * scale_factor))
            work_frame = cv2.resize(frame_bgr, (detect_w, detect_h), interpolation=cv2.INTER_LINEAR)
            scale_x = orig_w / float(detect_w)
            scale_y = orig_h / float(detect_h)
        if self._enable_profiling:
            self._profiling_stats["resize_total"] += time.perf_counter() - t_resize_start

        t_detect_start = time.perf_counter() if self._enable_profiling else 0.0
        try:
            with self._lock:
                faces = self._app.get(work_frame)
        except Exception as e:
            logger.warning("[InsightFace] Detection failed: %s", e)
            self._last_detections = []
            return []
        if self._enable_profiling:
            self._profiling_stats["detect_total"] += time.perf_counter() - t_detect_start

        if not faces:
            self._last_detections = []
            return []

        if self._max_faces is not None:
            faces = faces[: self._max_faces]

        detections = []
        t_post_start = time.perf_counter() if self._enable_profiling else 0.0
        for face in faces:
            bbox = None
            try:
                bbox = getattr(face, "bbox", None)
            except Exception:
                bbox = None
            if bbox is None:
                try:
                    bbox = face.get("bbox") if hasattr(face, "get") else None
                except Exception:
                    bbox = None
            if bbox is None:
                continue

            bbox_arr = np.asarray(bbox, dtype=np.float32).reshape(-1)
            if bbox_arr.size < 4:
                continue

            x1, y1, x2, y2 = [float(v) for v in bbox_arr[:4]]
            if scale_x != 1.0 or scale_y != 1.0:
                x1 *= float(scale_x)
                x2 *= float(scale_x)
                y1 *= float(scale_y)
                y2 *= float(scale_y)

            x1_i = max(0, int(x1))
            y1_i = max(0, int(y1))
            x2_i = min(int(orig_w), int(x2))
            y2_i = min(int(orig_h), int(y2))
            if x2_i <= x1_i or y2_i <= y1_i:
                continue

            bbox_w = int(x2_i - x1_i)
            bbox_h = int(y2_i - y1_i)
            centroid = (x1_i + (bbox_w // 2), y1_i + (bbox_h // 2))

            try:
                score = float(getattr(face, "det_score", 1.0))
            except Exception:
                score = 1.0

            landmarks_68 = self._get_face_landmarks_68(face)
            if landmarks_68 is not None and (scale_x != 1.0 or scale_y != 1.0):
                landmarks_68 = landmarks_68.astype(np.float32, copy=True)
                landmarks_68[:, 0] *= float(scale_x)
                landmarks_68[:, 1] *= float(scale_y)

            jaw_open = self._compute_jaw_open_from_dlib68(landmarks_68) if landmarks_68 is not None else 0.0
            blendshapes = self._build_arkit_blendshapes(jaw_open)

            detections.append(
                {
                    "bbox": (x1_i, y1_i, bbox_w, bbox_h),
                    "centroid": centroid,
                    "source_detector": "face_landmarker",
                    "label": "face",
                    "confidence": score,
                    "landmarks": landmarks_68.tolist() if landmarks_68 is not None else [],
                    "blendshapes": blendshapes,
                }
            )

        if self._enable_profiling:
            self._profiling_stats["post_total"] += time.perf_counter() - t_post_start
            self._profiling_stats["frame_count"] += 1
            if (self._profiling_stats["frame_count"] % 20) == 0:
                frame_count = int(self._profiling_stats.get("frame_count", 0) or 0)
                if frame_count > 0:
                    resize_ms = (self._profiling_stats["resize_total"] / frame_count) * 1000.0
                    detect_ms = (self._profiling_stats["detect_total"] / frame_count) * 1000.0
                    post_ms = (self._profiling_stats["post_total"] / frame_count) * 1000.0
                    logger.info(
                        "[PROFILING] InsightFace after %s frames: resize=%.2fms/frame, detect=%.2fms/frame, post=%.2fms/frame",
                        frame_count,
                        resize_ms,
                        detect_ms,
                        post_ms,
                    )

        self._last_detections = detections
        return detections


class OpenCVHaarFaceEngine:
    def __init__(self, cascade_path: Optional[str] = None):
        self._lock = threading.Lock()
        self._cascade_path = cascade_path or os.environ.get("STEP5_OPENCV_HAAR_CASCADE_PATH")
        if not self._cascade_path:
            self._cascade_path = str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")

        self._max_faces = _parse_optional_positive_int(os.environ.get("STEP5_OPENCV_MAX_FACES"))

        self._classifier = cv2.CascadeClassifier(self._cascade_path)
        if self._classifier.empty():
            raise RuntimeError(f"Unable to load Haar cascade: {self._cascade_path}")

    def detect(self, frame_bgr):
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        with self._lock:
            faces = self._classifier.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30),
            )

        if self._max_faces is not None:
            faces = faces[: self._max_faces]

        detections = []
        for (x, y, w, h) in faces:
            x_i = int(x)
            y_i = int(y)
            w_i = int(w)
            h_i = int(h)
            detections.append(
                {
                    "bbox": (x_i, y_i, w_i, h_i),
                    "centroid": (x_i + (w_i // 2), y_i + (h_i // 2)),
                    "source_detector": "face_landmarker",
                    "label": "face",
                    "confidence": 1.0,
                    "blendshapes": None,
                }
            )

        return detections


class OpenCVYuNetFaceEngine:
    def __init__(
        self,
        model_path: Optional[str] = None,
        score_threshold: float = 0.7,
        nms_threshold: float = 0.3,
        top_k: int = 5000,
        use_gpu: bool = False,
    ):
        self._lock = threading.Lock()
        self._use_gpu = use_gpu
        if use_gpu:
            logger.info(
                "YuNet detection currently repose sur cv2.FaceDetectorYN (CPU). "
                "Le flag GPU optimise uniquement les composants aval (FaceMesh/PyFeat)."
            )
        
        # Force OpenCV to use single thread to avoid contention with multiprocessing
        cv2.setNumThreads(1)
        
        # Configure downscaling for performance (coordinates will be rescaled to original)
        self._max_detection_width = int(os.environ.get("STEP5_YUNET_MAX_WIDTH", "640"))
        logger.info(f"YuNet downscale enabled: max_width={self._max_detection_width}px (coordinates auto-rescaled to original resolution)")

        self._max_faces = _parse_optional_positive_int(os.environ.get("STEP5_OPENCV_MAX_FACES"))
        
        self._model_path = model_path or os.environ.get("STEP5_YUNET_MODEL_PATH")
        if not self._model_path:
            raise RuntimeError("Missing STEP5_YUNET_MODEL_PATH (YuNet model .onnx)")

        self._model_path = self._resolve_model_path(self._model_path)
        if not Path(self._model_path).exists():
            raise RuntimeError(f"YuNet ONNX model not found: {self._model_path}")

        if not hasattr(cv2, "FaceDetectorYN"):
            raise RuntimeError("cv2.FaceDetectorYN is not available (opencv-contrib-python required)")

        self._score_threshold = float(score_threshold)
        self._nms_threshold = float(nms_threshold)
        self._top_k = int(top_k)

        self._detector = cv2.FaceDetectorYN.create(
            self._model_path,
            "",
            (320, 320),
            self._score_threshold,
            self._nms_threshold,
            self._top_k,
        )

    def _resolve_model_path(self, model_path: str) -> str:
        candidate = Path(model_path)
        if candidate.is_absolute():
            return str(candidate)

        if candidate.exists():
            return str(candidate)

        step5_dir = Path(__file__).resolve().parent
        project_root = step5_dir.parent.parent

        candidates = [
            project_root / candidate,
            step5_dir / candidate,
        ]
        for c in candidates:
            if c.exists():
                return str(c)

        return str(candidate)

    def detect(self, frame_bgr):
        orig_height, orig_width = frame_bgr.shape[:2]
        
        # Downscale for detection if needed
        if orig_width > self._max_detection_width:
            scale_factor = self._max_detection_width / orig_width
            detect_width = self._max_detection_width
            detect_height = int(orig_height * scale_factor)
            frame_resized = cv2.resize(frame_bgr, (detect_width, detect_height), interpolation=cv2.INTER_LINEAR)
        else:
            frame_resized = frame_bgr
            detect_width = orig_width
            detect_height = orig_height
            scale_factor = 1.0
        
        with self._lock:
            self._detector.setInputSize((detect_width, detect_height))
            _, faces = self._detector.detect(frame_resized)

        detections = []
        if faces is None:
            return detections

        # Rescale coordinates to original resolution
        rescale = orig_width / detect_width
        if scale_factor != 1.0:
            logger.debug(f"YuNet upscale: {detect_width}x{detect_height} -> {orig_width}x{orig_height} (rescale={rescale:.2f})")
        
        face_limit = self._max_faces
        for idx, row in enumerate(faces):
            if face_limit is not None and idx >= face_limit:
                break
            x, y, w, h = row[:4]
            score = float(row[-1]) if len(row) >= 15 else 0.0
            
            # Rescale to original coordinates
            x_orig = int(max(0, x * rescale))
            y_orig = int(max(0, y * rescale))
            w_orig = int(max(0, w * rescale))
            h_orig = int(max(0, h * rescale))
            
            detections.append(
                {
                    "bbox": (x_orig, y_orig, w_orig, h_orig),
                    "centroid": (x_orig + (w_orig // 2), y_orig + (h_orig // 2)),
                    "source_detector": "face_landmarker",
                    "label": "face",
                    "confidence": score,
                    "blendshapes": None,
                }
            )

        return detections


class OpenCVYuNetPyFeatEngine:
    def __init__(
        self,
        yunet_model_path: Optional[str] = None,
        facemesh_model_path: Optional[str] = None,
        pyfeat_model_path: Optional[str] = None,
        score_threshold: float = 0.7,
        nms_threshold: float = 0.3,
        top_k: int = 5000,
        use_gpu: bool = False,
    ):
        self._lock = threading.Lock()
        self._use_gpu = use_gpu
        
        # Debug: log environment variable values
        profiling_env = os.environ.get("STEP5_ENABLE_PROFILING", "NOT_SET")
        throttle_env = os.environ.get("STEP5_BLENDSHAPES_THROTTLE_N", "NOT_SET")
        logger.info(f"[DEBUG] STEP5_ENABLE_PROFILING={profiling_env}, STEP5_BLENDSHAPES_THROTTLE_N={throttle_env}")
        
        self._enable_profiling = os.environ.get("STEP5_ENABLE_PROFILING", "0").strip() in {"1", "true", "yes"}
        logger.info(f"[DEBUG] Profiling enabled: {self._enable_profiling}")
        
        self._profiling_stats = {
            "yunet_total": 0.0,
            "roi_extraction": 0.0,
            "facemesh_total": 0.0,
            "pyfeat_total": 0.0,
            "frame_count": 0
        }
        
        # Blendshapes throttling: compute every N frames to reduce CPU cost
        self._blendshapes_throttle_n = max(1, int(os.environ.get("STEP5_BLENDSHAPES_THROTTLE_N", "1")))
        logger.info(f"[DEBUG] Blendshapes throttle N: {self._blendshapes_throttle_n}")
        self._frame_counter = 0
        self._last_blendshapes_cache = {}  # object_id -> blendshapes dict

        self._jaw_open_scale = float(os.environ.get("STEP5_OPENCV_JAWOPEN_SCALE", "1.0"))
        
        self._yunet = OpenCVYuNetFaceEngine(
            model_path=yunet_model_path,
            score_threshold=score_threshold,
            nms_threshold=nms_threshold,
            top_k=top_k,
            use_gpu=use_gpu,
        )
        
        try:
            from onnx_facemesh_detector import ONNXFaceMeshDetector
            self._facemesh_detector = ONNXFaceMeshDetector(
                model_path=facemesh_model_path,
                use_gpu=use_gpu,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize FaceMesh ONNX detector: {e}")
        
        self._blendshape_extractor = None
        strict_pyfeat = os.environ.get("STEP5_PYFEAT_STRICT", "0").strip().lower() in {"1", "true", "yes"}
        try:
            from pyfeat_blendshape_extractor import PyFeatBlendshapeExtractor

            self._blendshape_extractor = PyFeatBlendshapeExtractor(
                model_path=pyfeat_model_path,
                use_gpu=use_gpu,
            )
        except Exception as e:
            if strict_pyfeat:
                raise RuntimeError(f"Failed to initialize py-feat blendshape extractor: {e}")

            logger.warning(
                "py-feat blendshape extractor disabled (continuing without blendshapes): %s",
                e,
            )

    def detect(self, frame_bgr):
        height, width = frame_bgr.shape[:2]
        self._frame_counter += 1
        should_compute_blendshapes = (self._frame_counter % self._blendshapes_throttle_n) == 0
        
        t_start_yunet = time.perf_counter() if self._enable_profiling else 0
        yunet_detections = self._yunet.detect(frame_bgr)
        if self._enable_profiling:
            self._profiling_stats["yunet_total"] += time.perf_counter() - t_start_yunet
        
        detections_with_blendshapes = []
        
        for det in yunet_detections:
            bbox = det["bbox"]
            x, y, w, h = bbox
            
            x_safe = max(0, x)
            y_safe = max(0, y)
            x2_safe = min(width, x + w)
            y2_safe = min(height, y + h)
            
            if x2_safe <= x_safe or y2_safe <= y_safe:
                detections_with_blendshapes.append(det)
                continue
            
            t_start_roi = time.perf_counter() if self._enable_profiling else 0
            face_roi = frame_bgr[y_safe:y2_safe, x_safe:x2_safe]
            if self._enable_profiling:
                self._profiling_stats["roi_extraction"] += time.perf_counter() - t_start_roi
            
            t_start_facemesh = time.perf_counter() if self._enable_profiling else 0
            landmarks_478 = self._facemesh_detector.detect_landmarks(
                face_roi,
                (x_safe, y_safe, x2_safe - x_safe, y2_safe - y_safe)
            )
            if self._enable_profiling:
                self._profiling_stats["facemesh_total"] += time.perf_counter() - t_start_facemesh
            
            blendshapes = None
            if landmarks_478 is not None and self._blendshape_extractor is not None:
                # Use simple bbox center as object identifier for caching
                object_id = f"{x_safe}_{y_safe}_{x2_safe}_{y2_safe}"
                
                if should_compute_blendshapes:
                    t_start_pyfeat = time.perf_counter() if self._enable_profiling else 0
                    blendshapes = self._blendshape_extractor.extract_blendshapes(
                        landmarks_478,
                        width,
                        height,
                    )
                    if self._enable_profiling:
                        self._profiling_stats["pyfeat_total"] += time.perf_counter() - t_start_pyfeat
                    
                    # Cache for next frames
                    if blendshapes is not None:
                        blendshapes_scaled = _apply_jawopen_scale(blendshapes, self._jaw_open_scale)
                        self._last_blendshapes_cache[object_id] = blendshapes_scaled
                        blendshapes = blendshapes_scaled
                else:
                    # Reuse cached blendshapes from previous computation
                    blendshapes = self._last_blendshapes_cache.get(object_id)
                    # If no cache available (first frames), compute anyway
                    if blendshapes is None:
                        t_start_pyfeat = time.perf_counter() if self._enable_profiling else 0
                        blendshapes = self._blendshape_extractor.extract_blendshapes(
                            landmarks_478,
                            width,
                            height,
                        )
                        if self._enable_profiling:
                            self._profiling_stats["pyfeat_total"] += time.perf_counter() - t_start_pyfeat
                        if blendshapes is not None:
                            blendshapes_scaled = _apply_jawopen_scale(blendshapes, self._jaw_open_scale)
                            self._last_blendshapes_cache[object_id] = blendshapes_scaled
                            blendshapes = blendshapes_scaled
            
            detection_with_bs = det.copy()
            detection_with_bs["bbox"] = (x_safe, y_safe, x2_safe - x_safe, y2_safe - y_safe)
            detection_with_bs["landmarks"] = landmarks_478.tolist() if landmarks_478 is not None else []
            detection_with_bs["blendshapes"] = blendshapes
            detections_with_blendshapes.append(detection_with_bs)
        
        if self._enable_profiling:
            self._profiling_stats["frame_count"] += 1
            # Log every 20 frames (compatible with multiprocessing chunk size)
            if self._profiling_stats["frame_count"] % 20 == 0:
                self._log_profiling_stats()
        
        return detections_with_blendshapes
    
    def _log_profiling_stats(self):
        """Log accumulated profiling statistics."""
        fc = self._profiling_stats["frame_count"]
        if fc == 0:
            return
        logger.info(
            f"[PROFILING] After {fc} frames: "
            f"YuNet={self._profiling_stats['yunet_total']/fc*1000:.2f}ms/frame, "
            f"ROI={self._profiling_stats['roi_extraction']/fc*1000:.2f}ms/frame, "
            f"FaceMesh={self._profiling_stats['facemesh_total']/fc*1000:.2f}ms/frame, "
            f"py-feat={self._profiling_stats['pyfeat_total']/fc*1000:.2f}ms/frame"
        )


class EosFaceEngine:
    def __init__(
        self,
        yunet_model_path: Optional[str] = None,
        facemesh_model_path: Optional[str] = None,
    ):
        try:
            import eos as eos_module
        except Exception as e:
            raise RuntimeError(
                "eos engine requires eos-py (install it inside eos_env)."
            ) from e

        self._eos = eos_module
        self._lock = threading.Lock()
        self._frame_counter = 0
        self._last_detections = []

        fit_every_raw = os.environ.get("STEP5_EOS_FIT_EVERY_N")
        if fit_every_raw is None or str(fit_every_raw).strip() == "":
            fit_every_raw = os.environ.get("STEP5_BLENDSHAPES_THROTTLE_N", "1")
        try:
            self._fit_every_n = max(1, int(str(fit_every_raw)))
        except Exception:
            self._fit_every_n = 1

        self._jaw_open_scale = float(os.environ.get("STEP5_EOS_JAWOPEN_SCALE", "1.0"))
        self._max_faces = (
            _parse_optional_positive_int(os.environ.get("STEP5_EOS_MAX_FACES"))
            or _parse_optional_positive_int(os.environ.get("STEP5_OPENCV_MAX_FACES"))
        )
        
        self._max_detection_width = int(os.environ.get("STEP5_EOS_MAX_WIDTH", "1280"))
        self._enable_profiling = os.environ.get("STEP5_ENABLE_PROFILING", "").strip().lower() in {"1", "true", "yes"}
        self._profiling_interval = 20

        self._yunet = OpenCVYuNetFaceEngine(model_path=yunet_model_path)

        try:
            from onnx_facemesh_detector import ONNXFaceMeshDetector
        except Exception as e:
            raise RuntimeError(
                "eos engine requires ONNXFaceMeshDetector dependencies (onnxruntime + FaceMesh model) inside eos_env."
            ) from e

        self._facemesh_detector = ONNXFaceMeshDetector(model_path=facemesh_model_path)

        self._models_dir = os.environ.get("STEP5_EOS_MODELS_DIR")
        self._sfm_model_path_raw = os.environ.get("STEP5_EOS_SFM_MODEL_PATH")
        self._expression_blendshapes_path_raw = os.environ.get("STEP5_EOS_EXPRESSION_BLENDSHAPES_PATH")
        self._landmark_mapper_path_raw = os.environ.get("STEP5_EOS_LANDMARK_MAPPER_PATH")
        self._edge_topology_path_raw = os.environ.get("STEP5_EOS_EDGE_TOPOLOGY_PATH")
        self._model_contour_path_raw = os.environ.get("STEP5_EOS_MODEL_CONTOUR_PATH")
        self._contour_landmarks_path_raw = os.environ.get("STEP5_EOS_CONTOUR_LANDMARKS_PATH")

        self._morphable_model = None
        self._landmark_mapper = None
        self._edge_topology = None
        self._contour_landmarks = None
        self._model_contour = None

        correspondence = [
            (127, 127),
            (234, 234),
            (93, 93),
            (132, 58),
            (58, 172),
            (136, 136),
            (150, 150),
            (176, 176),
            (152, 152),
            (400, 400),
            (379, 379),
            (365, 365),
            (397, 288),
            (361, 361),
            (323, 323),
            (454, 454),
            (356, 356),
            (70, 70),
            (63, 63),
            (105, 105),
            (66, 66),
            (107, 107),
            (336, 336),
            (296, 296),
            (334, 334),
            (293, 293),
            (300, 300),
            (168, 6),
            (197, 195),
            (5, 5),
            (4, 4),
            (75, 75),
            (97, 97),
            (2, 2),
            (326, 326),
            (305, 305),
            (33, 33),
            (160, 160),
            (158, 158),
            (133, 133),
            (153, 153),
            (144, 144),
            (362, 362),
            (385, 385),
            (387, 387),
            (263, 263),
            (373, 373),
            (380, 380),
            (61, 61),
            (39, 39),
            (37, 37),
            (0, 0),
            (267, 267),
            (269, 269),
            (291, 291),
            (321, 321),
            (314, 314),
            (17, 17),
            (84, 84),
            (91, 91),
            (78, 78),
            (82, 82),
            (13, 13),
            (312, 312),
            (308, 308),
            (317, 317),
            (14, 14),
            (87, 87),
        ]

        self._mp2dlib_pairs = np.asarray(correspondence, dtype=np.int32)

    def _resolve_model_path(self, model_path: str) -> str:
        candidate = Path(model_path)
        if candidate.is_absolute() and candidate.exists():
            return str(candidate)
        if candidate.exists():
            return str(candidate)

        step5_dir = Path(__file__).resolve().parent
        project_root = step5_dir.parent.parent

        candidates = [
            project_root / candidate,
            step5_dir / candidate,
        ]
        for c in candidates:
            if c.exists():
                return str(c)

        return str(candidate)

    def _get_models_base_dir(self) -> Path:
        if self._models_dir and str(self._models_dir).strip():
            return Path(self._resolve_model_path(self._models_dir)).resolve()

        step5_dir = Path(__file__).resolve().parent
        models_dir = step5_dir / "models" / "engines" / "eos"
        return models_dir.resolve()

    def _ensure_eos_assets_loaded(self) -> None:
        if self._morphable_model is not None:
            return

        models_base_dir = self._get_models_base_dir()
        sfm_model_path = self._sfm_model_path_raw or str(models_base_dir / "sfm_shape_3448.bin")
        expression_blendshapes_path = self._expression_blendshapes_path_raw or str(
            models_base_dir / "expression_blendshapes_3448.bin"
        )
        landmark_mapper_path = self._landmark_mapper_path_raw or str(models_base_dir / "ibug_to_sfm.txt")
        edge_topology_path = self._edge_topology_path_raw or str(models_base_dir / "sfm_3448_edge_topology.json")
        model_contour_path = self._model_contour_path_raw or str(models_base_dir / "sfm_model_contours.json")
        contour_landmarks_path = self._contour_landmarks_path_raw or landmark_mapper_path

        sfm_model_path = self._resolve_model_path(sfm_model_path)
        expression_blendshapes_path = self._resolve_model_path(expression_blendshapes_path)
        landmark_mapper_path = self._resolve_model_path(landmark_mapper_path)
        edge_topology_path = self._resolve_model_path(edge_topology_path)
        model_contour_path = self._resolve_model_path(model_contour_path)
        contour_landmarks_path = self._resolve_model_path(contour_landmarks_path)

        required_files = {
            "sfm_model": sfm_model_path,
            "expression_blendshapes": expression_blendshapes_path,
            "landmark_mapper": landmark_mapper_path,
            "edge_topology": edge_topology_path,
            "model_contour": model_contour_path,
            "contour_landmarks": contour_landmarks_path,
        }
        missing = [k for k, v in required_files.items() if not Path(v).exists()]
        if missing:
            raise RuntimeError(
                "Missing eos asset files: "
                + ", ".join(missing)
                + ". Configure STEP5_EOS_MODELS_DIR and/or STEP5_EOS_*_PATH variables."
            )

        model = self._eos.morphablemodel.load_model(sfm_model_path)
        blendshapes = self._eos.morphablemodel.load_blendshapes(expression_blendshapes_path)

        self._morphable_model = self._eos.morphablemodel.MorphableModel(
            model.get_shape_model(),
            blendshapes,
            color_model=self._eos.morphablemodel.PcaModel(),
            vertex_definitions=None,
            texture_coordinates=model.get_texture_coordinates(),
        )
        self._landmark_mapper = self._eos.core.LandmarkMapper(landmark_mapper_path)
        self._edge_topology = self._eos.morphablemodel.load_edge_topology(edge_topology_path)
        self._contour_landmarks = self._eos.fitting.ContourLandmarks.load(contour_landmarks_path)
        self._model_contour = self._eos.fitting.ModelContour.load(model_contour_path)

    def _convert_478_to_68(self, landmarks_478: np.ndarray) -> np.ndarray:
        lm = np.asarray(landmarks_478, dtype=np.float32)
        if lm.ndim != 2 or lm.shape[0] < 468:
            raise ValueError(f"Invalid FaceMesh landmarks shape: {lm.shape}")
        if lm.shape[0] < 478:
            last = lm[-1:, :]
            pad = np.repeat(last, 478 - lm.shape[0], axis=0)
            lm = np.concatenate([lm, pad], axis=0)
        return lm[self._mp2dlib_pairs].mean(axis=1)

    def _compute_jaw_open_from_dlib68(self, landmarks_68: np.ndarray) -> float:
        lm = np.asarray(landmarks_68, dtype=np.float32)
        if lm.ndim != 2 or lm.shape[0] < 68:
            return 0.0

        try:
            upper_inner = float(np.mean(lm[60:65, 1], axis=0))
            lower_inner = float(np.mean(lm[65:68, 1], axis=0))
            mouth_open = abs(lower_inner - upper_inner)

            nose_y = float(lm[33, 1])
            chin_y = float(lm[8, 1])
            denom = max(abs(chin_y - nose_y), 1e-6)
            ratio = (mouth_open / denom) * float(self._jaw_open_scale)
            return float(np.clip(ratio, 0.0, 1.0))
        except Exception:
            return 0.0

    def _build_arkit_blendshapes(self, jaw_open: float) -> dict:
        out = {}
        for name in ARKIT_52_BLENDSHAPE_NAMES:
            out[name] = 0.0
        out["jawOpen"] = float(jaw_open)
        return out

    def _safe_to_list(self, value) -> list:
        if value is None:
            return []
        try:
            return [float(x) for x in value]
        except Exception:
            try:
                return [float(x) for x in list(value)]
            except Exception:
                return []

    def detect(self, frame_bgr):
        import time
        
        self._frame_counter += 1
        
        if self._enable_profiling and (self._frame_counter % self._profiling_interval) == 0:
            frame_start_time = time.time()
        else:
            frame_start_time = None
        
        if (self._frame_counter % self._fit_every_n) != 0:
            return list(self._last_detections)

        if frame_bgr is None or getattr(frame_bgr, "shape", None) is None:
            self._last_detections = []
            return []

        orig_height, orig_width = frame_bgr.shape[:2]
        
        if orig_width > self._max_detection_width:
            scale_factor = self._max_detection_width / orig_width
            detect_width = self._max_detection_width
            detect_height = int(orig_height * scale_factor)
            frame_resized = cv2.resize(frame_bgr, (detect_width, detect_height), interpolation=cv2.INTER_LINEAR)
            height, width = detect_height, detect_width
        else:
            frame_resized = frame_bgr
            height, width = orig_height, orig_width
            scale_factor = 1.0

        try:
            self._ensure_eos_assets_loaded()
        except Exception as e:
            logger.error("EOS assets load failed: %s", e)
            self._last_detections = []
            return []
        
        if frame_start_time is not None:
            assets_time = time.time()

        yunet_detections = self._yunet.detect(frame_resized)
        if self._max_faces is not None:
            yunet_detections = yunet_detections[: self._max_faces]
        
        if frame_start_time is not None:
            yunet_time = time.time()

        detections = []
        for det in yunet_detections:
            bbox = det.get("bbox")
            if not bbox or len(bbox) < 4:
                continue

            x, y, w, h = bbox
            
            if scale_factor != 1.0:
                x = int(x / scale_factor)
                y = int(y / scale_factor)
                w = int(w / scale_factor)
                h = int(h / scale_factor)
                logger.debug(f"EOS upscale: bbox rescaled by 1/{scale_factor:.2f} to original resolution")
            
            x_safe = max(0, int(x))
            y_safe = max(0, int(y))
            x2_safe = min(int(orig_width), int(x + w))
            y2_safe = min(int(orig_height), int(y + h))
            if x2_safe <= x_safe or y2_safe <= y_safe:
                continue

            face_roi = frame_bgr[y_safe:y2_safe, x_safe:x2_safe]
            landmarks_478 = self._facemesh_detector.detect_landmarks(
                face_roi,
                (x_safe, y_safe, x2_safe - x_safe, y2_safe - y_safe),
            )
            if landmarks_478 is None:
                continue
            
            if frame_start_time is not None:
                facemesh_time = time.time()

            try:
                landmarks_68 = self._convert_478_to_68(landmarks_478)
            except Exception:
                continue

            jaw_open = self._compute_jaw_open_from_dlib68(landmarks_68)

            try:
                eos_landmarks = []
                for i in range(68):
                    eos_landmarks.append(
                        self._eos.core.Landmark(
                            str(i + 1),
                            [float(landmarks_68[i, 0]), float(landmarks_68[i, 1])],
                        )
                    )

                with self._lock:
                    (
                        _mesh,
                        _pose,
                        shape_coeffs,
                        blendshape_coeffs,
                    ) = self._eos.fitting.fit_shape_and_pose(
                        self._morphable_model,
                        eos_landmarks,
                        self._landmark_mapper,
                        int(orig_width),
                        int(orig_height),
                        self._edge_topology,
                        self._contour_landmarks,
                        self._model_contour,
                    )
            except Exception as e:
                logger.warning("EOS fitting failed: %s", e)
                continue
            
            if frame_start_time is not None:
                eos_fit_time = time.time()

            landmarks_xyz = np.zeros((68, 3), dtype=np.float32)
            landmarks_xyz[:, 0] = landmarks_68[:, 0]
            landmarks_xyz[:, 1] = landmarks_68[:, 1]

            eos_payload = {
                "shape_coeffs": self._safe_to_list(shape_coeffs),
                "expression_coeffs": self._safe_to_list(blendshape_coeffs),
            }

            out_det = dict(det)
            out_det["bbox"] = (x_safe, y_safe, x2_safe - x_safe, y2_safe - y_safe)
            out_det["centroid"] = (x_safe + ((x2_safe - x_safe) // 2), y_safe + ((y2_safe - y_safe) // 2))
            out_det["source_detector"] = "face_landmarker"
            out_det["label"] = "face"
            out_det["landmarks"] = landmarks_xyz.tolist()
            out_det["blendshapes"] = self._build_arkit_blendshapes(jaw_open)
            out_det["eos"] = eos_payload
            detections.append(out_det)

        self._last_detections = detections
        
        if frame_start_time is not None:
            total_time = time.time() - frame_start_time
            assets_duration = (assets_time - frame_start_time) * 1000 if 'assets_time' in locals() else 0
            yunet_duration = (yunet_time - assets_time) * 1000 if 'yunet_time' in locals() and 'assets_time' in locals() else 0
            facemesh_duration = (facemesh_time - yunet_time) * 1000 if 'facemesh_time' in locals() and 'yunet_time' in locals() else 0
            eos_duration = (eos_fit_time - facemesh_time) * 1000 if 'eos_fit_time' in locals() and 'facemesh_time' in locals() else 0
            logger.info(
                f"[PROFILING] Frame {self._frame_counter}: total={total_time*1000:.1f}ms "
                f"(assets={assets_duration:.1f}ms, yunet={yunet_duration:.1f}ms, "
                f"facemesh={facemesh_duration:.1f}ms, eos_fit={eos_duration:.1f}ms, "
                f"faces={len(detections)}, downscale={scale_factor:.2f})"
            )
        
        return detections


def create_face_engine(engine_name: str, use_gpu: bool = False):
    """
    Factory function to create face tracking engines.
    
    Args:
        engine_name: Name of the engine (mediapipe_landmarker, openseeface, etc.)
        use_gpu: If True, enable GPU acceleration for supported engines (v4.2+)
    
    Returns:
        Engine instance or None for MediaPipe (handled separately in workers)
    """
    normalized = (engine_name or "").strip().lower()
    if not normalized or normalized in {"mediapipe", "mediapipe_landmarker"}:
        return None
    if normalized == "openseeface":
        return OpenSeeFaceEngine(use_gpu=use_gpu)
    if normalized == "insightface":
        return InsightFaceEngine(use_gpu=use_gpu)
    if normalized == "eos":
        return EosFaceEngine()
    if normalized == "opencv_haar":
        return OpenCVHaarFaceEngine()
    if normalized == "opencv_yunet":
        return OpenCVYuNetFaceEngine(use_gpu=use_gpu)
    if normalized == "opencv_yunet_pyfeat":
        return OpenCVYuNetPyFeatEngine(use_gpu=use_gpu)
    raise ValueError(f"Unsupported tracking engine: {engine_name}")
