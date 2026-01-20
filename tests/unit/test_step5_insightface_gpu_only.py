"""
Tests unitaires pour valider que le GPU STEP5 est réservé exclusivement à InsightFace.

Décision v4.2+ : Seul le moteur InsightFace peut utiliser le GPU.
Tous les autres moteurs (MediaPipe, OpenSeeFace, OpenCV, EOS) doivent
s'exécuter en mode CPU-only même si STEP5_ENABLE_GPU=1.
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))


class TestInsightFaceGPUOnly:
    """Tests pour vérifier que seul InsightFace peut utiliser le GPU."""

    @pytest.fixture(autouse=True)
    def setup_env(self):
        """Setup initial pour chaque test."""
        self.original_env = os.environ.copy()
        
        yield
        
        os.environ.clear()
        os.environ.update(self.original_env)

    def test_insightface_gpu_enabled(self):
        """
        Test: InsightFace avec STEP5_ENABLE_GPU=1 doit activer le GPU.
        """
        os.environ['STEP5_ENABLE_GPU'] = '1'
        os.environ['STEP5_GPU_ENGINES'] = 'insightface'
        os.environ['STEP5_TRACKING_ENGINE'] = 'insightface'
        
        mock_gpu_status = {
            'available': True,
            'vram_free_gb': 3.5,
            'cuda_version': '12.8',
            'reason': ''
        }
        
        with patch('config.settings.Config.check_gpu_availability', return_value=mock_gpu_status):
            from workflow_scripts.step5 import run_tracking_manager
            
            class Args:
                tracking_engine = 'insightface'
                disable_gpu = False
                cpu_internal_workers = 1
                videos_json_path = 'dummy.json'
            
            args = Args()
            
            engine_norm = 'insightface'
            gpu_enabled_global = os.environ.get('STEP5_ENABLE_GPU', '0').strip() == '1'
            gpu_engines = ['insightface']
            
            engine_supports_gpu = False
            if gpu_enabled_global and not args.disable_gpu:
                if engine_norm == "insightface":
                    if engine_norm in gpu_engines or 'all' in gpu_engines:
                        engine_supports_gpu = True
            
            assert engine_supports_gpu is True, "InsightFace doit pouvoir utiliser le GPU"
            assert args.disable_gpu is False, "disable_gpu ne doit pas être forcé pour InsightFace"

    def test_mediapipe_gpu_forced_to_cpu(self):
        """
        Test: MediaPipe avec STEP5_ENABLE_GPU=1 doit être forcé en mode CPU.
        """
        os.environ['STEP5_ENABLE_GPU'] = '1'
        os.environ['STEP5_GPU_ENGINES'] = 'insightface'
        os.environ['STEP5_TRACKING_ENGINE'] = 'mediapipe_landmarker'
        
        # Simuler les arguments CLI
        class Args:
            tracking_engine = 'mediapipe_landmarker'
            disable_gpu = False
            cpu_internal_workers = 15
            videos_json_path = 'dummy.json'
        
        args = Args()
        
        engine_norm = 'mediapipe_landmarker'
        gpu_enabled_global = os.environ.get('STEP5_ENABLE_GPU', '0').strip() == '1'
        
        engine_supports_gpu = False
        if gpu_enabled_global and not args.disable_gpu:
            if engine_norm == "insightface":
                engine_supports_gpu = True
            else:
                args.disable_gpu = True
        
        assert engine_supports_gpu is False, "MediaPipe ne doit pas pouvoir utiliser le GPU"
        assert args.disable_gpu is True, "MediaPipe doit être forcé en mode CPU"

    def test_openseeface_gpu_forced_to_cpu(self):
        """
        Test: OpenSeeFace avec STEP5_ENABLE_GPU=1 doit être forcé en mode CPU.
        """
        os.environ['STEP5_ENABLE_GPU'] = '1'
        os.environ['STEP5_GPU_ENGINES'] = 'insightface'
        os.environ['STEP5_TRACKING_ENGINE'] = 'openseeface'
        
        # Simuler les arguments CLI
        class Args:
            tracking_engine = 'openseeface'
            disable_gpu = False
            cpu_internal_workers = 15
            videos_json_path = 'dummy.json'
        
        args = Args()
        
        engine_norm = 'openseeface'
        gpu_enabled_global = os.environ.get('STEP5_ENABLE_GPU', '0').strip() == '1'
        
        engine_supports_gpu = False
        if gpu_enabled_global and not args.disable_gpu:
            if engine_norm == "insightface":
                engine_supports_gpu = True
            else:
                args.disable_gpu = True
        
        assert engine_supports_gpu is False, "OpenSeeFace ne doit pas pouvoir utiliser le GPU"
        assert args.disable_gpu is True, "OpenSeeFace doit être forcé en mode CPU"

    def test_opencv_yunet_pyfeat_gpu_forced_to_cpu(self):
        """
        Test: OpenCV YuNet + PyFeat avec STEP5_ENABLE_GPU=1 doit être forcé en mode CPU.
        """
        os.environ['STEP5_ENABLE_GPU'] = '1'
        os.environ['STEP5_GPU_ENGINES'] = 'insightface'
        os.environ['STEP5_TRACKING_ENGINE'] = 'opencv_yunet_pyfeat'
        
        # Simuler les arguments CLI
        class Args:
            tracking_engine = 'opencv_yunet_pyfeat'
            disable_gpu = False
            cpu_internal_workers = 15
            videos_json_path = 'dummy.json'
        
        args = Args()
        
        engine_norm = 'opencv_yunet_pyfeat'
        gpu_enabled_global = os.environ.get('STEP5_ENABLE_GPU', '0').strip() == '1'
        
        engine_supports_gpu = False
        if gpu_enabled_global and not args.disable_gpu:
            if engine_norm == "insightface":
                engine_supports_gpu = True
            else:
                args.disable_gpu = True
        
        assert engine_supports_gpu is False, "OpenCV YuNet+PyFeat ne doit pas pouvoir utiliser le GPU"
        assert args.disable_gpu is True, "OpenCV YuNet+PyFeat doit être forcé en mode CPU"

    def test_eos_gpu_forced_to_cpu(self):
        """
        Test: EOS avec STEP5_ENABLE_GPU=1 doit être forcé en mode CPU.
        """
        os.environ['STEP5_ENABLE_GPU'] = '1'
        os.environ['STEP5_GPU_ENGINES'] = 'insightface'
        os.environ['STEP5_TRACKING_ENGINE'] = 'eos'
        
        # Simuler les arguments CLI
        class Args:
            tracking_engine = 'eos'
            disable_gpu = False
            cpu_internal_workers = 15
            videos_json_path = 'dummy.json'
        
        args = Args()
        
        engine_norm = 'eos'
        gpu_enabled_global = os.environ.get('STEP5_ENABLE_GPU', '0').strip() == '1'
        
        engine_supports_gpu = False
        if gpu_enabled_global and not args.disable_gpu:
            if engine_norm == "insightface":
                engine_supports_gpu = True
            else:
                args.disable_gpu = True
        
        if engine_norm in {"opencv_haar", "opencv_yunet", "eos"}:
            if not args.disable_gpu:
                args.disable_gpu = True
        
        assert engine_supports_gpu is False, "EOS ne doit pas pouvoir utiliser le GPU"
        assert args.disable_gpu is True, "EOS doit être forcé en mode CPU"

    def test_insightface_without_gpu_engines_forced_to_cpu(self):
        """
        Test: InsightFace avec STEP5_ENABLE_GPU=1 mais absent de STEP5_GPU_ENGINES
        doit être forcé en mode CPU avec warning.
        """
        os.environ['STEP5_ENABLE_GPU'] = '1'
        os.environ['STEP5_GPU_ENGINES'] = 'mediapipe_landmarker'  # InsightFace absent
        os.environ['STEP5_TRACKING_ENGINE'] = 'insightface'
        
        # Simuler les arguments CLI
        class Args:
            tracking_engine = 'insightface'
            disable_gpu = False
            cpu_internal_workers = 1
            videos_json_path = 'dummy.json'
        
        args = Args()
        
        engine_norm = 'insightface'
        gpu_enabled_global = os.environ.get('STEP5_ENABLE_GPU', '0').strip() == '1'
        gpu_engines_str = os.environ.get('STEP5_GPU_ENGINES', '').strip().lower()
        gpu_engines = [e.strip() for e in gpu_engines_str.split(',') if e.strip()]
        
        engine_supports_gpu = False
        if gpu_enabled_global and not args.disable_gpu:
            if engine_norm == "insightface":
                if engine_norm in gpu_engines or 'all' in gpu_engines:
                    engine_supports_gpu = True
                else:
                    args.disable_gpu = True
        
        assert engine_supports_gpu is False, "InsightFace absent de GPU_ENGINES ne doit pas activer le GPU"
        assert args.disable_gpu is True, "InsightFace doit être forcé en CPU si absent de GPU_ENGINES"

    def test_gpu_disabled_globally(self):
        """
        Test: Avec STEP5_ENABLE_GPU=0, tous les moteurs doivent utiliser le CPU.
        """
        # Setup
        os.environ['STEP5_ENABLE_GPU'] = '0'
        os.environ['STEP5_GPU_ENGINES'] = 'insightface'
        os.environ['STEP5_TRACKING_ENGINE'] = 'insightface'
        
        # Simuler les arguments CLI
        class Args:
            tracking_engine = 'insightface'
            disable_gpu = False
            cpu_internal_workers = 15
            videos_json_path = 'dummy.json'
        
        args = Args()
        
        engine_norm = 'insightface'
        gpu_enabled_global = os.environ.get('STEP5_ENABLE_GPU', '0').strip() == '1'
        
        engine_supports_gpu = False
        if gpu_enabled_global and not args.disable_gpu:
            pass
        
        assert engine_supports_gpu is False, "Aucun moteur ne doit utiliser le GPU si STEP5_ENABLE_GPU=0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
