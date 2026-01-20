#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for ObjectDetectorRegistry

Tests model resolution, registry lookups, and fallback behavior.
"""

import os
import pytest
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "workflow_scripts" / "step5"))

from workflow_scripts.step5.object_detector_registry import ObjectDetectorRegistry, ObjectDetectorModelSpec


class TestObjectDetectorRegistry:
    """Test suite for ObjectDetectorRegistry"""
    
    def test_get_model_spec_valid(self):
        """Test retrieving valid model specifications"""
        # Test default model
        spec = ObjectDetectorRegistry.get_model_spec()
        assert spec.name == 'efficientdet_lite2'
        assert spec.backend == 'tflite'
        assert spec.filename == 'EfficientDet-Lite2-32.tflite'
        
        # Test specific models
        lite0_spec = ObjectDetectorRegistry.get_model_spec('efficientdet_lite0')
        assert lite0_spec.name == 'efficientdet_lite0'
        assert lite0_spec.map_coco == 25.69
        assert lite0_spec.recommended_hardware == 'edge_tpu'
        
        # Test case insensitivity
        spec_upper = ObjectDetectorRegistry.get_model_spec('EFFICIENTDET_LITE0')
        assert spec_upper.name == 'efficientdet_lite0'
    
    def test_get_model_spec_invalid(self):
        """Test error handling for invalid model names"""
        with pytest.raises(ValueError, match="Unknown object detector model"):
            ObjectDetectorRegistry.get_model_spec('invalid_model_name')
        
        with pytest.raises(ValueError, match="Unknown object detector model"):
            ObjectDetectorRegistry.get_model_spec('efficientdet_lite99')
    
    def test_list_available_models(self):
        """Test listing all available models"""
        models = ObjectDetectorRegistry.list_available_models()
        
        assert isinstance(models, dict)
        assert len(models) >= 6  # At least 6 models defined
        assert 'efficientdet_lite0' in models
        assert 'efficientdet_lite2' in models
        assert 'yolo11n_onnx' in models
        
        # Verify all models have required attributes
        for model_name, spec in models.items():
            assert isinstance(spec, ObjectDetectorModelSpec)
            assert spec.name == model_name
            assert spec.backend in ['tflite', 'onnx']
            assert spec.filename
            assert spec.map_coco > 0
    
    def test_get_recommended_model(self):
        """Test hardware-specific model recommendations"""
        # Test recommendations for different hardware
        assert ObjectDetectorRegistry.get_recommended_model('edge_tpu') == 'efficientdet_lite0'
        assert ObjectDetectorRegistry.get_recommended_model('cpu_arm') == 'efficientdet_lite0'
        assert ObjectDetectorRegistry.get_recommended_model('cpu_desktop') == 'efficientdet_lite0'
        assert ObjectDetectorRegistry.get_recommended_model('gpu') == 'efficientdet_lite2'
        
        # Test default for unknown hardware
        assert ObjectDetectorRegistry.get_recommended_model('unknown') == 'efficientdet_lite2'
    
    def test_validate_backend_support(self):
        """Test backend validation"""
        # TFLite should always be supported (MediaPipe requirement)
        assert ObjectDetectorRegistry.validate_backend_support('tflite') is True
        
        # ONNX depends on onnxruntime availability
        onnx_supported = ObjectDetectorRegistry.validate_backend_support('onnx')
        assert isinstance(onnx_supported, bool)
        
        # Unknown backend
        assert ObjectDetectorRegistry.validate_backend_support('unknown') is False
    
    def test_resolve_model_path_with_existing_file(self, tmp_path):
        """Test model path resolution when file exists"""
        # Create temporary models directory with a test model
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        
        model_file = models_dir / "EfficientDet-Lite2-32.tflite"
        model_file.write_text("dummy model content")
        
        # Test resolution
        resolved_path = ObjectDetectorRegistry.resolve_model_path(
            model_name='efficientdet_lite2',
            models_dir=models_dir
        )
        
        assert resolved_path == model_file
        assert resolved_path.exists()

    def test_resolve_model_path_with_backend_subfolder(self, tmp_path):
        """Test model resolution when model is stored under object_detectors/<backend>/"""
        models_dir = tmp_path / "models"
        model_dir = models_dir / "object_detectors" / "tflite"
        model_dir.mkdir(parents=True)

        model_file = model_dir / "EfficientDet-Lite2-32.tflite"
        model_file.write_text("dummy model content")

        resolved_path = ObjectDetectorRegistry.resolve_model_path(
            model_name='efficientdet_lite2',
            models_dir=models_dir,
        )

        assert resolved_path == model_file
        assert resolved_path.exists()
    
    def test_resolve_model_path_missing_file(self, tmp_path):
        """Test error when model file is missing"""
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        
        # Model file does not exist
        # Note: the registry searches in the repo default models directory as a fallback.
        # To test the missing-file behavior deterministically, inject a temporary model spec
        # with a filename that does not exist anywhere.
        with pytest.MonkeyPatch.context() as mp:
            from workflow_scripts.step5.object_detector_registry import ObjectDetectorModelSpec

            models_copy = dict(ObjectDetectorRegistry.MODELS)
            models_copy["missing_model"] = ObjectDetectorModelSpec(
                name="missing_model",
                backend="tflite",
                filename="this_model_file_should_not_exist_1234567890.tflite",
                description="Test-only missing model",
                recommended_hardware="cpu_desktop",
                map_coco=1.0,
                latency_note="n/a",
            )
            mp.setattr(ObjectDetectorRegistry, "MODELS", models_copy, raising=True)

            with pytest.raises(FileNotFoundError, match="Object detector model not found"):
                ObjectDetectorRegistry.resolve_model_path(
                    model_name='missing_model',
                    models_dir=models_dir,
                )
    
    def test_resolve_model_path_with_override(self, tmp_path):
        """Test model path resolution with explicit override"""
        # Create override file
        override_file = tmp_path / "custom_model.tflite"
        override_file.write_text("custom model")
        
        # Test that override takes priority
        resolved_path = ObjectDetectorRegistry.resolve_model_path(
            model_name='efficientdet_lite0',
            override_path=str(override_file)
        )
        
        assert resolved_path == override_file
    
    def test_resolve_model_path_with_env_variable(self, tmp_path, monkeypatch):
        """Test model path resolution with environment variable"""
        # Create model file
        env_model_file = tmp_path / "env_model.tflite"
        env_model_file.write_text("env model")
        
        # Set environment variable
        monkeypatch.setenv('STEP5_OBJECT_DETECTOR_MODEL_PATH', str(env_model_file))
        
        # Test that environment variable is used
        resolved_path = ObjectDetectorRegistry.resolve_model_path(
            model_name='efficientdet_lite0'
        )
        
        assert resolved_path == env_model_file
    
    def test_resolve_model_path_priority_order(self, tmp_path, monkeypatch):
        """Test resolution priority: override > env > models_dir > default"""
        # Create all possible paths
        override_file = tmp_path / "override.tflite"
        override_file.write_text("override")
        
        env_file = tmp_path / "env.tflite"
        env_file.write_text("env")
        
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        models_dir_file = models_dir / "EfficientDet-Lite0.tflite"
        models_dir_file.write_text("models_dir")
        
        # Test priority 1: Override wins
        resolved = ObjectDetectorRegistry.resolve_model_path(
            model_name='efficientdet_lite0',
            models_dir=models_dir,
            override_path=str(override_file)
        )
        assert resolved == override_file
        
        # Test priority 2: Env wins if no override
        monkeypatch.setenv('STEP5_OBJECT_DETECTOR_MODEL_PATH', str(env_file))
        resolved = ObjectDetectorRegistry.resolve_model_path(
            model_name='efficientdet_lite0',
            models_dir=models_dir
        )
        assert resolved == env_file
        
        # Test priority 3: models_dir wins if no override/env
        monkeypatch.delenv('STEP5_OBJECT_DETECTOR_MODEL_PATH', raising=False)
        resolved = ObjectDetectorRegistry.resolve_model_path(
            model_name='efficientdet_lite0',
            models_dir=models_dir
        )
        assert resolved == models_dir_file
    
    def test_model_specs_completeness(self):
        """Test that all model specs have complete information"""
        models = ObjectDetectorRegistry.list_available_models()
        
        required_fields = ['name', 'backend', 'filename', 'description', 
                          'recommended_hardware', 'map_coco', 'latency_note']
        
        for model_name, spec in models.items():
            for field in required_fields:
                assert hasattr(spec, field), f"Model {model_name} missing field: {field}"
                value = getattr(spec, field)
                assert value is not None, f"Model {model_name} has None value for: {field}"
                assert value != "", f"Model {model_name} has empty value for: {field}"
    
    def test_backend_consistency(self):
        """Test that model backends match their filenames"""
        models = ObjectDetectorRegistry.list_available_models()
        
        for model_name, spec in models.items():
            if spec.backend == 'tflite':
                assert spec.filename.endswith('.tflite'), \
                    f"TFLite model {model_name} has non-.tflite filename"
            elif spec.backend == 'onnx':
                assert spec.filename.endswith('.onnx'), \
                    f"ONNX model {model_name} has non-.onnx filename"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
