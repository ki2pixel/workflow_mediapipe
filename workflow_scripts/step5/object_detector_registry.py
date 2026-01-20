#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Object Detector Model Registry for STEP5

Centralized configuration and resolution for object detection models
used as fallback when face detection fails in MediaPipe tracking engine.

Supports multiple model backends (TFLite, ONNX) with hardware-aware recommendations.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ObjectDetectorModelSpec:
    """Specification for an object detection model."""
    
    name: str
    backend: str  # 'tflite' or 'onnx'
    filename: str
    description: str
    recommended_hardware: str  # 'edge_tpu', 'cpu_arm', 'cpu_desktop', 'gpu'
    map_coco: float  # mAP on COCO dataset
    latency_note: str


class ObjectDetectorRegistry:
    """
    Registry for object detection models used in STEP5 fallback detection.
    
    Provides centralized configuration, model resolution, and hardware-aware
    recommendations for object detection models.
    """
    
    # Model catalog with specifications from technical analysis
    MODELS = {
        'efficientdet_lite0': ObjectDetectorModelSpec(
            name='efficientdet_lite0',
            backend='tflite',
            filename='EfficientDet-Lite0.tflite',
            description='EfficientDet-Lite0 (320x320) - Fastest, Edge TPU compatible',
            recommended_hardware='edge_tpu',
            map_coco=25.69,
            latency_note='~37ms on Pixel 4 CPU, ~50% faster than Lite2'
        ),
        'efficientdet_lite1': ObjectDetectorModelSpec(
            name='efficientdet_lite1',
            backend='tflite',
            filename='EfficientDet-Lite1.tflite',
            description='EfficientDet-Lite1 (384x384) - Balanced, Edge TPU compatible',
            recommended_hardware='edge_tpu',
            map_coco=30.55,
            latency_note='~49ms on Pixel 4 CPU'
        ),
        'efficientdet_lite2': ObjectDetectorModelSpec(
            name='efficientdet_lite2',
            backend='tflite',
            filename='EfficientDet-Lite2-32.tflite',
            description='EfficientDet-Lite2 (448x448) - Current baseline',
            recommended_hardware='cpu_desktop',
            map_coco=33.97,
            latency_note='~69ms on Pixel 4 CPU'
        ),
        'ssd_mobilenet_v3': ObjectDetectorModelSpec(
            name='ssd_mobilenet_v3',
            backend='tflite',
            filename='ssd_mobilenet_v3.tflite',
            description='SSD-MobileNetV3 - Stable ecosystem, CPU optimized',
            recommended_hardware='cpu_arm',
            map_coco=28.0,
            latency_note='~40% faster than Lite2, high confidence stability'
        ),
        'yolo11n_onnx': ObjectDetectorModelSpec(
            name='yolo11n_onnx',
            backend='onnx',
            filename='yolo11n.onnx',
            description='YOLO11 Nano (ONNX) - Best CPU performance (experimental)',
            recommended_hardware='cpu_desktop',
            map_coco=39.5,
            latency_note='~56ms CPU ONNX, 20-30% faster with better precision'
        ),
        'nanodet_plus': ObjectDetectorModelSpec(
            name='nanodet_plus',
            backend='onnx',
            filename='nanodet-plus-m_416.onnx',
            description='NanoDet-Plus (416x416) - Ultra-lightweight (experimental)',
            recommended_hardware='cpu_arm',
            map_coco=34.1,
            latency_note='~25ms on ARM, 60-70% faster than Lite2'
        ),
    }
    
    # Default model (backward compatible with existing setup)
    DEFAULT_MODEL = 'efficientdet_lite2'

    @classmethod
    def _try_resolve_path(cls, raw_path: str, models_dir: Optional[Path]) -> Optional[Path]:
        if not raw_path:
            return None

        candidate = Path(raw_path)
        if candidate.exists():
            return candidate if candidate.is_absolute() else candidate.resolve()

        step5_dir = Path(__file__).resolve().parent
        project_root = step5_dir.parent.parent

        for base in [models_dir, project_root, step5_dir]:
            if base is None:
                continue
            if candidate.is_absolute():
                continue
            resolved = base / candidate
            if resolved.exists():
                return resolved.resolve()

        return None
    
    @classmethod
    def get_model_spec(cls, model_name: Optional[str] = None) -> ObjectDetectorModelSpec:
        """
        Get model specification by name.
        
        Args:
            model_name: Model identifier (e.g., 'efficientdet_lite0').
                       If None, returns default model.
        
        Returns:
            ObjectDetectorModelSpec for the requested model.
        
        Raises:
            ValueError: If model_name is not found in registry.
        """
        if not model_name:
            model_name = cls.DEFAULT_MODEL
        
        model_name_normalized = model_name.strip().lower()
        
        if model_name_normalized not in cls.MODELS:
            available = ', '.join(cls.MODELS.keys())
            raise ValueError(
                f"Unknown object detector model: '{model_name}'. "
                f"Available models: {available}"
            )
        
        return cls.MODELS[model_name_normalized]
    
    @classmethod
    def resolve_model_path(
        cls,
        model_name: Optional[str] = None,
        models_dir: Optional[Path] = None,
        override_path: Optional[str] = None
    ) -> Path:
        """
        Resolve the full path to an object detection model file.
        
        Priority order:
        1. override_path (if provided and exists)
        2. Environment variable STEP5_OBJECT_DETECTOR_MODEL_PATH
        3. models_dir / model_spec.filename
        4. Default models directory / model_spec.filename
        
        Args:
            model_name: Model identifier from registry.
            models_dir: Directory containing model files.
            override_path: Explicit path override.
        
        Returns:
            Resolved Path to model file.
        
        Raises:
            FileNotFoundError: If model file cannot be found.
            ValueError: If model_name is invalid.
        """
        # Priority 1: Explicit override path
        if override_path:
            override_path_obj = cls._try_resolve_path(override_path, models_dir=models_dir)
            if override_path_obj is not None:
                logger.info(f"Using override model path: {override_path_obj}")
                return override_path_obj
            logger.warning(f"Override path does not exist: {override_path}")

        # Priority 2: Environment variable
        env_path = os.environ.get('STEP5_OBJECT_DETECTOR_MODEL_PATH')
        if env_path:
            env_path_obj = cls._try_resolve_path(env_path, models_dir=models_dir)
            if env_path_obj is not None:
                logger.info(f"Using model path from STEP5_OBJECT_DETECTOR_MODEL_PATH: {env_path_obj}")
                return env_path_obj
            logger.warning(f"STEP5_OBJECT_DETECTOR_MODEL_PATH does not exist: {env_path}")
        
        # Get model spec
        spec = cls.get_model_spec(model_name)
        
        # Priority 3/4: Provided models_dir and default models directory
        search_base_dirs = []
        if models_dir is not None:
            search_base_dirs.append(models_dir)

        default_models_dir = Path(__file__).resolve().parent / "models"
        search_base_dirs.append(default_models_dir)

        backend_dir = "tflite" if spec.backend == "tflite" else "onnx"
        relative_candidates = [
            Path(spec.filename),
            Path("object_detectors") / backend_dir / spec.filename,
            Path("object_detectors") / spec.backend / spec.filename,
        ]

        for base_dir in search_base_dirs:
            for rel in relative_candidates:
                model_path = base_dir / rel
                if model_path.exists():
                    logger.info(f"Using object detector model: {model_path}")
                    return model_path

        searched_in = ", ".join(str(d) for d in search_base_dirs)
        raise FileNotFoundError(
            f"Object detector model not found: {spec.filename}\n"
            f"Model: {spec.name} ({spec.description})\n"
            f"Expected filename: {spec.filename}\n"
            f"Searched in: {searched_in}\n"
            f"To use this model, download it under workflow_scripts/step5/models/object_detectors/ "
            f"or set STEP5_OBJECT_DETECTOR_MODEL_PATH environment variable."
        )
    
    @classmethod
    def get_recommended_model(cls, hardware_target: str = 'cpu_desktop') -> str:
        """
        Get recommended model name for a specific hardware target.
        
        Args:
            hardware_target: One of 'edge_tpu', 'cpu_arm', 'cpu_desktop', 'gpu'
        
        Returns:
            Recommended model name for the hardware target.
        """
        recommendations = {
            'edge_tpu': 'efficientdet_lite0',
            'cpu_arm': 'efficientdet_lite0',  # or nanodet_plus if ONNX available
            'cpu_desktop': 'efficientdet_lite0',  # balance of speed and accuracy
            'gpu': 'efficientdet_lite2',  # can handle higher resolution
        }
        
        return recommendations.get(hardware_target, cls.DEFAULT_MODEL)
    
    @classmethod
    def list_available_models(cls) -> Dict[str, ObjectDetectorModelSpec]:
        """
        Get all registered models with their specifications.
        
        Returns:
            Dictionary of model_name -> ObjectDetectorModelSpec
        """
        return cls.MODELS.copy()
    
    @classmethod
    def validate_backend_support(cls, backend: str) -> bool:
        """
        Check if a model backend is supported in the current environment.
        
        Args:
            backend: 'tflite' or 'onnx'
        
        Returns:
            True if backend is supported, False otherwise.
        """
        if backend == 'tflite':
            # MediaPipe always supports TFLite
            return True
        elif backend == 'onnx':
            # ONNX support is experimental/future work
            try:
                import onnxruntime
                return True
            except ImportError:
                logger.warning("ONNX Runtime not available. ONNX models require: pip install onnxruntime")
                return False
        else:
            return False
