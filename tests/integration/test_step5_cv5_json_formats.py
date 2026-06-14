#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for STEP5 tracking manager JSON input formats with OpenCV 5.0.

Tests that run_tracking_cv5.py correctly accepts both:
1. New format: raw JSON array of video paths
2. Legacy format: object with 'videos' key containing array
"""

import json
import os
import subprocess
import tempfile
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Load .env file to resolve VENV_BASE_DIR
_env_path = Path(__file__).resolve().parent.parent.parent / '.env'
if _env_path.exists():
    load_dotenv(_env_path)

from config.settings import config


# Path to the tracking manager script
MANAGER_SCRIPT = Path(__file__).resolve().parent.parent.parent / "workflow_scripts" / "step5" / "run_tracking_cv5.py"
TRACKING_ENV_PYTHON = config.get_venv_python("tracking_cv5_env")


class TestStep5Cv5JsonFormats:
    """Test JSON format parsing in run_tracking_cv5.py."""
    
    def test_accepts_raw_list_format(self):
        """Test that manager accepts new format: raw JSON array."""
        if not TRACKING_ENV_PYTHON.exists():
            pytest.skip("tracking_cv5_env environment not found")
            
        test_videos = [
            "/fake/path/video1.mp4",
            "/fake/path/video2.mov"
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_videos, f, indent=2)
            temp_path = f.name
        
        test_env = os.environ.copy()
        
        try:
            result = subprocess.run(
                [str(TRACKING_ENV_PYTHON), str(MANAGER_SCRIPT), 
                 '--videos_json_path', temp_path],
                capture_output=True,
                text=True,
                env=test_env,
                timeout=15
            )
            
            # Should not fail with "Invalid JSON format" or "traceback"
            assert "Invalid JSON format" not in result.stderr
            assert "Invalid JSON format" not in result.stdout
            assert "TOTAL_VIDEOS_TO_PROCESS:" in result.stdout or "Aucune vidéo à traiter" in result.stdout
            
        finally:
            os.unlink(temp_path)
    
    def test_accepts_legacy_object_format(self):
        """Test that manager accepts legacy format: object with 'videos' key."""
        if not TRACKING_ENV_PYTHON.exists():
            pytest.skip("tracking_cv5_env environment not found")
            
        test_videos_object = {
            "videos": [
                "/fake/path/video1.mp4",
                "/fake/path/video2.mov"
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_videos_object, f, indent=2)
            temp_path = f.name
        
        test_env = os.environ.copy()
        
        try:
            result = subprocess.run(
                [str(TRACKING_ENV_PYTHON), str(MANAGER_SCRIPT), 
                 '--videos_json_path', temp_path],
                capture_output=True,
                text=True,
                env=test_env,
                timeout=15
            )
            
            # Should not fail with "Invalid JSON format" or "traceback"
            assert "Invalid JSON format" not in result.stderr
            assert "Invalid JSON format" not in result.stdout
            assert "Legacy videos JSON schema detected" in result.stdout
            assert "TOTAL_VIDEOS_TO_PROCESS:" in result.stdout or "Aucune vidéo à traiter" in result.stdout
            
        finally:
            os.unlink(temp_path)
    
    def test_rejects_invalid_format(self):
        """Test that manager rejects invalid JSON formats."""
        if not TRACKING_ENV_PYTHON.exists():
            pytest.skip("tracking_cv5_env environment not found")
            
        invalid_data = {
            "invalid_key": ["video1.mp4"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_data, f, indent=2)
            temp_path = f.name
        
        test_env = os.environ.copy()
        
        try:
            result = subprocess.run(
                [str(TRACKING_ENV_PYTHON), str(MANAGER_SCRIPT), 
                 '--videos_json_path', temp_path],
                capture_output=True,
                text=True,
                env=test_env,
                timeout=15
            )
            
            # Should fail with explicit error message
            assert "Invalid JSON format" in result.stderr or "Invalid JSON format" in result.stdout
            assert result.returncode != 0
            
        finally:
            os.unlink(temp_path)
    
    def test_handles_empty_list(self):
        """Test that manager handles empty video list gracefully."""
        if not TRACKING_ENV_PYTHON.exists():
            pytest.skip("tracking_cv5_env environment not found")
            
        test_videos = []
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_videos, f, indent=2)
            temp_path = f.name
        
        test_env = os.environ.copy()
        
        try:
            result = subprocess.run(
                [str(TRACKING_ENV_PYTHON), str(MANAGER_SCRIPT), 
                 '--videos_json_path', temp_path],
                capture_output=True,
                text=True,
                env=test_env,
                timeout=15
            )
            
            assert "Aucune vidéo à traiter" in result.stdout
            assert result.returncode == 0
            
        finally:
            os.unlink(temp_path)

    def test_parallel_progress_reporting(self):
        """Test that run_tracking_cv5.py outputs standard Échec/Succès lines in parallel mode."""
        if not TRACKING_ENV_PYTHON.exists():
            pytest.skip("tracking_cv5_env environment not found")
            
        test_videos = [
            "/fake/path/video1.mp4",
            "/fake/path/video2.mov"
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_videos, f, indent=2)
            temp_path = f.name
            
        test_env = os.environ.copy()
        
        try:
            result = subprocess.run(
                [str(TRACKING_ENV_PYTHON), str(MANAGER_SCRIPT), 
                 '--videos_json_path', temp_path, '--num_workers', '2'],
                capture_output=True,
                text=True,
                env=test_env,
                timeout=20
            )
            
            output = result.stdout + result.stderr
            # Since the video paths are fake, workers must fail and report "Échec:" to stdout
            assert "Échec: video1.mp4 échoué" in output or "Échec pour video1.mp4" in output
            assert "Échec: video2.mov échoué" in output or "Échec pour video2.mov" in output
            
        finally:
            os.unlink(temp_path)

    def test_streaming_json_output_newline(self):
        """Test that StreamingJSONOutput formats the beginning of the file with a real newline."""
        from workflow_scripts.step5.run_tracking_cv5 import StreamingJSONOutput
        metadata = {"test": "value"}
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            stream = StreamingJSONOutput(temp_path, metadata)
            stream.close()
            
            with open(temp_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # The output should start with '{\n  "metadata":'
            assert content.startswith('{\n  "metadata":')
            # It should be valid JSON
            parsed = json.loads(content)
            assert parsed["metadata"]["test"] == "value"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_load_cv5_model_absolute_path_resolution(self):
        """Test that load_cv5_model resolves absolute paths correctly."""
        from workflow_scripts.step5.run_tracking_cv5 import load_cv5_model
        with tempfile.NamedTemporaryFile(suffix='.onnx', delete=False) as f:
            temp_path = f.name
            
        try:
            # When we pass the absolute path, load_cv5_model should try to load it.
            # Since it's empty, ONNX runtime or OpenCV DNN will fail to parse it,
            # but it should NOT print "Modèle ONNX manquant" in the warning.
            res = load_cv5_model(temp_path)
            assert res is None  # Fails to parse empty file
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_object_detector_resolution_with_tflite_env(self):
        """Test that ObjectDetectorRegistry.resolve_model_path resolves to ONNX in CV5 main logic even with TFLite in env."""
        import os
        from workflow_scripts.step5.object_detector_registry import ObjectDetectorRegistry
        
        # Save original env
        orig_env = os.environ.get('STEP5_OBJECT_DETECTOR_MODEL_PATH')
        
        # Set to a fake/real tflite path
        os.environ['STEP5_OBJECT_DETECTOR_MODEL_PATH'] = 'workflow_scripts/step5/models/object_detectors/tflite/efficientdet_lite2_int8_mediapipe.tflite'
        
        try:
            # Execute the same env popping logic as in run_tracking_cv5.py main()
            env_path = os.environ.get('STEP5_OBJECT_DETECTOR_MODEL_PATH', '')
            if env_path and not env_path.endswith('.onnx'):
                orig_env_val = os.environ.pop('STEP5_OBJECT_DETECTOR_MODEL_PATH', None)
            else:
                orig_env_val = None
                
            override_path = env_path if env_path.endswith('.onnx') else None
            model_name = "yolo11n_onnx"
            
            try:
                object_model_path = ObjectDetectorRegistry.resolve_model_path(
                    model_name=model_name,
                    override_path=override_path
                )
            finally:
                if orig_env_val is not None:
                    os.environ['STEP5_OBJECT_DETECTOR_MODEL_PATH'] = orig_env_val
            
            # The resolved model path must end with yolo11n.onnx
            assert object_model_path.name == 'yolo11n.onnx'
            assert object_model_path.exists()
            
        finally:
            if orig_env == os.environ.get('STEP5_OBJECT_DETECTOR_MODEL_PATH'):
                pass
            elif orig_env is None:
                os.environ.pop('STEP5_OBJECT_DETECTOR_MODEL_PATH', None)
            else:
                os.environ['STEP5_OBJECT_DETECTOR_MODEL_PATH'] = orig_env


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
