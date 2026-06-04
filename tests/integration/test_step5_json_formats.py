#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for STEP5 tracking manager JSON input formats.

Tests that run_tracking_manager.py correctly accepts both:
1. New format: raw JSON array of video paths
2. Legacy format: object with 'videos' key containing array

This ensures backward compatibility while transitioning to the simpler format.
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
MANAGER_SCRIPT = Path(__file__).resolve().parent.parent.parent / "workflow_scripts" / "step5" / "run_tracking_manager.py"
TRACKING_ENV_PYTHON = config.get_venv_python("tracking_env_slim")


class TestStep5JsonFormats:
    """Test JSON format parsing in run_tracking_manager.py."""
    
    def test_accepts_raw_list_format(self):
        """Test that manager accepts new format: raw JSON array."""
        test_videos = [
            "/fake/path/video1.mp4",
            "/fake/path/video2.mov"
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_videos, f, indent=2)
            temp_path = f.name
        
        test_env = os.environ.copy()
        test_env["STEP5_TRACKING_ENGINE"] = ""
        test_env["STEP5_ENABLE_GPU"] = "0"
        
        try:
            # Run manager with raw list format
            # Use --disable_gpu to avoid GPU requirements in tests
            result = subprocess.run(
                [str(TRACKING_ENV_PYTHON), str(MANAGER_SCRIPT), 
                 '--videos_json_path', temp_path,
                 '--disable_gpu'],
                capture_output=True,
                text=True,
                env=test_env,
                timeout=10
            )
            
            # Should not fail with "Invalid JSON format" error
            assert "Invalid JSON format" not in result.stderr
            assert "Invalid JSON format" not in result.stdout
            
            # Should log that it's processing videos (even though paths are fake, 
            # the JSON parsing should succeed)
            assert "Vidéos à traiter:" in result.stdout or "Aucune vidéo à traiter" in result.stdout
            
        finally:
            os.unlink(temp_path)
    
    def test_accepts_legacy_object_format(self):
        """Test that manager accepts legacy format: object with 'videos' key."""
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
        test_env["STEP5_TRACKING_ENGINE"] = ""
        test_env["STEP5_ENABLE_GPU"] = "0"
        
        try:
            result = subprocess.run(
                [str(TRACKING_ENV_PYTHON), str(MANAGER_SCRIPT), 
                 '--videos_json_path', temp_path,
                 '--disable_gpu'],
                capture_output=True,
                text=True,
                env=test_env,
                timeout=10
            )
            
            # Should not fail with "Invalid JSON format" error
            assert "Invalid JSON format" not in result.stderr
            assert "Invalid JSON format" not in result.stdout
            
            # Should log that legacy format was detected
            assert "Legacy videos JSON schema detected" in result.stdout
            
            # Should log that it's processing videos
            assert "Vidéos à traiter:" in result.stdout or "Aucune vidéo à traiter" in result.stdout
            
        finally:
            os.unlink(temp_path)
    
    def test_rejects_invalid_format(self):
        """Test that manager rejects invalid JSON formats."""
        invalid_data = {
            "invalid_key": ["video1.mp4"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_data, f, indent=2)
            temp_path = f.name
        
        test_env = os.environ.copy()
        test_env["STEP5_TRACKING_ENGINE"] = ""
        test_env["STEP5_ENABLE_GPU"] = "0"
        
        try:
            result = subprocess.run(
                [str(TRACKING_ENV_PYTHON), str(MANAGER_SCRIPT), 
                 '--videos_json_path', temp_path,
                 '--disable_gpu'],
                capture_output=True,
                text=True,
                env=test_env,
                timeout=10
            )
            
            # Should fail with explicit error message
            assert "Invalid JSON format" in result.stderr or "Invalid JSON format" in result.stdout
            assert result.returncode != 0
            
        finally:
            os.unlink(temp_path)
    
    def test_handles_empty_list(self):
        """Test that manager handles empty video list gracefully."""
        test_videos = []
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_videos, f, indent=2)
            temp_path = f.name
        
        test_env = os.environ.copy()
        test_env["STEP5_TRACKING_ENGINE"] = ""
        test_env["STEP5_ENABLE_GPU"] = "0"
        
        try:
            result = subprocess.run(
                [str(TRACKING_ENV_PYTHON), str(MANAGER_SCRIPT), 
                 '--videos_json_path', temp_path,
                 '--disable_gpu'],
                capture_output=True,
                text=True,
                env=test_env,
                timeout=10
            )
            
            # Should complete successfully with "no videos" message
            assert "Aucune vidéo à traiter" in result.stdout
            assert result.returncode == 0
            
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
