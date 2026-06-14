#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for STEP3 TransNetV2 scene detection with OpenCV 5.0 / ORT fallback.
"""

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


BASE_PATH = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = BASE_PATH / "workflow_scripts" / "step3" / "run_transnet_cv5.py"
PYTHON_PATH = config.get_venv_python("transnet_cv5_env")


class TestStep3Cv5Integration:
    """Integration tests for STEP3 CV5 scene detection."""
    
    def test_step3_cv5_no_videos_to_process(self):
        """Test run_transnet_cv5.py when no videos are to be processed."""
        if not PYTHON_PATH.exists():
            pytest.skip("transnet_cv5_env environment not found")
            
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [str(PYTHON_PATH), str(SCRIPT_PATH)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=20
            )
            
            assert result.returncode == 0
            assert "TOTAL_VIDEOS_TO_PROCESS: 0" in result.stdout
            
    def test_step3_cv5_config_loading(self):
        """Test that run_transnet_cv5.py loads and displays effective config."""
        if not PYTHON_PATH.exists():
            pytest.skip("transnet_cv5_env environment not found")
            
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [str(PYTHON_PATH), str(SCRIPT_PATH), "--threshold", "0.6", "--window", "120"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=20
            )
            
            output = result.stdout + result.stderr
            assert "CONFIG_EFFECTIVE" in output
            assert "threshold=0.6" in output
            assert "window=120" in output
            
    def test_step3_cv5_slice_validation(self):
        """Test that the ONNX model loads and the Slice operator validation passes."""
        if not PYTHON_PATH.exists():
            pytest.skip("transnet_cv5_env environment not found")
            
        model_path = BASE_PATH / "assets" / "models" / "onnx" / "transnetv2.onnx"
        if not model_path.exists():
            pytest.skip("transnetv2.onnx weights file not present")
            
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [str(PYTHON_PATH), str(SCRIPT_PATH)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout + result.stderr
            assert "VALIDATION_OK" in output
