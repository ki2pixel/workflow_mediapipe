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
            env_max_width = "1280"
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


def create_face_engine(engine_name: str, use_gpu: bool = False):
    """
    Factory function to create face tracking engines.
    
    Args:
        engine_name: Name of the engine (default is MediaPipe when empty/mediapipe)
        use_gpu: If True, enable GPU acceleration for supported engines
    
    Returns:
        Engine instance or None for MediaPipe (handled separately in workers)
    """
    normalized = (engine_name or "").strip().lower()
    if not normalized or normalized in {"mediapipe", "mediapipe_landmarker"}:
        return None
    if normalized == "insightface":
        return InsightFaceEngine(use_gpu=use_gpu)
    raise ValueError(f"Unsupported tracking engine: {engine_name}")
