import logging
import os
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class ONNXFaceMeshDetector:
    def __init__(self, model_path: Optional[str] = None, use_gpu: bool = False):
        self._model_path = model_path or os.environ.get("STEP5_FACEMESH_ONNX_PATH")
        self._model_path = self._resolve_model_path(self._model_path)
        
        if not self._model_path:
            self._model_path = self._find_mediapipe_facemesh_model()
        
        self._model_path = self._resolve_model_path(self._model_path)

        if not self._model_path or not Path(self._model_path).exists():
            raise RuntimeError(
                f"FaceMesh ONNX model not found. "
                f"Set STEP5_FACEMESH_ONNX_PATH or place face_landmark.onnx under models/face_landmarks/"
            )

        try:
            import onnxruntime as ort
            self._ort = ort
            
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            
            # Configure threading for optimal CPU performance
            intra_threads = int(os.environ.get("STEP5_ONNX_INTRA_OP_THREADS", "2"))
            inter_threads = int(os.environ.get("STEP5_ONNX_INTER_OP_THREADS", "1"))
            sess_options.intra_op_num_threads = intra_threads
            sess_options.inter_op_num_threads = inter_threads
            
            # Enable memory optimizations
            sess_options.enable_cpu_mem_arena = True
            sess_options.enable_mem_pattern = True
            
            providers = []
            if use_gpu:
                providers.append('CUDAExecutionProvider')
            providers.append('CPUExecutionProvider')
            
            self._session = ort.InferenceSession(
                self._model_path,
                sess_options=sess_options,
                providers=providers
            )
            active_providers = self._session.get_providers()
            
            logger.info(
                f"ONNX Runtime configured: intra_threads={intra_threads}, inter_threads={inter_threads}, "
                f"use_gpu={use_gpu}"
            )
            logger.info("FaceMesh ONNX providers active: %s", active_providers)
            
            self._input_name = self._session.get_inputs()[0].name
            self._input_shape = self._session.get_inputs()[0].shape
            self._output_names = [output.name for output in self._session.get_outputs()]
            
            logger.info(f"FaceMesh ONNX model loaded: {self._model_path}")
            logger.info(f"Input shape: {self._input_shape}, Outputs: {self._output_names}")
        except ImportError:
            raise RuntimeError(
                "onnxruntime is required for ONNX FaceMesh. "
                "Install with: pip install onnxruntime"
            )
        except Exception as e:
            logger.error(f"Failed to load ONNX FaceMesh model: {e}")
            raise

    def _find_mediapipe_facemesh_model(self) -> Optional[str]:
        search_paths = [
            Path(__file__).parent / "models" / "face_landmarks" / "opencv" / "face_landmark.onnx",
            Path(__file__).parent / "models" / "face_landmarks" / "opencv" / "face_landmarker.onnx",
            Path(__file__).parent / "models" / "face_landmarks" / "opencv" / "facemesh.onnx",
            Path(__file__).parent / "models" / "face_landmark.onnx",
            Path(__file__).parent / "models" / "face_landmarker.onnx",
            Path(__file__).parent / "models" / "facemesh.onnx",
        ]
        
        for path in search_paths:
            if path.exists():
                return str(path)
        
        return None

    def _resolve_model_path(self, model_path: Optional[str]) -> Optional[str]:
        if not model_path:
            return None

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

    def detect_landmarks(
        self,
        face_roi: np.ndarray,
        original_bbox: Tuple[int, int, int, int]
    ) -> Optional[np.ndarray]:
        try:
            input_size = 192
            if len(self._input_shape) >= 3 and self._input_shape[2] is not None:
                input_size = self._input_shape[2]
            
            # Optimize resize and preprocessing
            if face_roi.shape[:2] != (input_size, input_size):
                resized = cv2.resize(face_roi, (input_size, input_size), interpolation=cv2.INTER_LINEAR)
            else:
                resized = face_roi
            
            # Single operation: convert to float32, normalize, transpose
            input_tensor = np.ascontiguousarray(
                np.transpose(resized, (2, 0, 1))[np.newaxis, :, :, :].astype(np.float32) / 255.0
            )

            x, y, w, h = original_bbox
            feed_dict = {}
            for input_meta in self._session.get_inputs():
                input_name = input_meta.name
                if input_name == self._input_name:
                    feed_dict[input_name] = input_tensor
                elif input_name == "crop_x1":
                    feed_dict[input_name] = np.array([[int(x)]], dtype=np.int32)
                elif input_name == "crop_y1":
                    feed_dict[input_name] = np.array([[int(y)]], dtype=np.int32)
                elif input_name == "crop_width":
                    feed_dict[input_name] = np.array([[int(w)]], dtype=np.int32)
                elif input_name == "crop_height":
                    feed_dict[input_name] = np.array([[int(h)]], dtype=np.int32)

            missing_inputs = [i.name for i in self._session.get_inputs() if i.name not in feed_dict]
            if missing_inputs:
                raise RuntimeError(
                    f"FaceMesh ONNX model requires additional inputs not supported: {missing_inputs}"
                )

            outputs = self._session.run(self._output_names, feed_dict)
            
            landmarks_normalized = None
            for output in outputs:
                if output.shape[-1] == 3 and output.shape[-2] >= 468:
                    landmarks_normalized = output[0]
                    break
            
            if landmarks_normalized is None:
                logger.warning("Could not find landmarks in ONNX output")
                return None

            landmarks_normalized = landmarks_normalized[:478, :]

            if landmarks_normalized.shape[0] < 478:
                pad_count = 478 - int(landmarks_normalized.shape[0])
                if pad_count > 0 and landmarks_normalized.shape[0] > 0:
                    pad = np.repeat(landmarks_normalized[-1:, :], pad_count, axis=0)
                    landmarks_normalized = np.concatenate([landmarks_normalized, pad], axis=0)

            if np.issubdtype(landmarks_normalized.dtype, np.integer):
                return landmarks_normalized.astype(np.float32)

            max_abs = float(np.nanmax(np.abs(landmarks_normalized[:, :2]))) if landmarks_normalized.size else 0.0
            if max_abs > 2.0:
                return landmarks_normalized.astype(np.float32)

            landmarks_absolute = landmarks_normalized.copy()
            landmarks_absolute[:, 0] = landmarks_normalized[:, 0] * w + x
            landmarks_absolute[:, 1] = landmarks_normalized[:, 1] * h + y

            return landmarks_absolute.astype(np.float32)
        
        except Exception as e:
            logger.warning(f"Failed to detect landmarks with ONNX: {e}")
            return None
