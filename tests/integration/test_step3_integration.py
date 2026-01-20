#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests d'intégration pour STEP3 (TransNetV2 scene detection)
"""

import pytest
import subprocess
import tempfile
import os
from pathlib import Path


BASE_PATH = Path(__file__).parent.parent.parent


class TestStep3Integration:
    """Tests d'intégration pour STEP3"""
    
    def test_step3_no_videos_to_process(self):
        """Test STEP3 quand aucune vidéo à traiter (devrait réussir rapidement)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = BASE_PATH / "workflow_scripts" / "step3" / "run_transnet.py"
            python_path = BASE_PATH / "transnet_env" / "bin" / "python"
            
            if not python_path.exists():
                pytest.skip("transnet_env environment not found")
            
            result = subprocess.run(
                [str(python_path), str(script_path)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            assert result.returncode == 0
            assert "TOTAL_VIDEOS_TO_PROCESS: 0" in result.stdout or "0 vidéo" in result.stdout
    
    def test_step3_config_loading(self):
        """Test que STEP3 charge correctement la configuration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = BASE_PATH / "workflow_scripts" / "step3" / "run_transnet.py"
            python_path = BASE_PATH / "transnet_env" / "bin" / "python"
            
            if not python_path.exists():
                pytest.skip("transnet_env environment not found")
            
            result = subprocess.run(
                [str(python_path), str(script_path)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=10,
                env={**os.environ}
            )
            
            output = result.stdout + result.stderr
            assert "CONFIG_EFFECTIVE" in output or result.returncode == 0
    
    def test_step3_weights_file_check(self):
        """Test vérification de présence du fichier de poids"""
        weights_path = BASE_PATH / "assets" / "transnetv2-pytorch-weights.pth"
        
        if not weights_path.exists():
            pytest.skip("Weights file not present, cannot test (expected for CI)")
        
        assert weights_path.is_file()
        assert weights_path.stat().st_size > 0


class TestStep3CUDAFallback:
    """Tests spécifiques au fallback CUDA->CPU"""
    
    def test_cpu_device_forced(self):
        """Test forcer device CPU via CLI"""
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = BASE_PATH / "workflow_scripts" / "step3" / "run_transnet.py"
            python_path = BASE_PATH / "transnet_env" / "bin" / "python"
            
            if not python_path.exists():
                pytest.skip("transnet_env environment not found")
            
            result = subprocess.run(
                [str(python_path), str(script_path), "--device", "cpu"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            output = result.stdout + result.stderr
            assert "CPU" in output or result.returncode == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
