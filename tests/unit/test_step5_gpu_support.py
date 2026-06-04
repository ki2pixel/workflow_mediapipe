"""
Tests unitaires pour le support GPU STEP5 (InsightFace).

Ces tests vérifient:
- Disponibilité des providers GPU (ONNX CUDA, TensorFlow)
- Initialisation des moteurs avec flag use_gpu
- Fallback automatique vers CPU si GPU indisponible
"""

import pytest
import os
import sys
import types
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestGPUAvailability:
    """Tests de disponibilité GPU au niveau système."""
    
    def test_pytorch_cuda_available(self):
        """Vérifier que PyTorch détecte le GPU."""
        try:
            import torch
            if torch.cuda.is_available():
                assert torch.cuda.device_count() > 0, "CUDA available but no devices found"
                print(f"GPU detected: {torch.cuda.get_device_name(0)}")
            else:
                pytest.skip("CUDA not available (expected in CI)")
        except ImportError:
            pytest.skip("PyTorch not installed in transnet_env / tracking_env_slim")
    
    def test_onnxruntime_providers(self):
        """Vérifier les providers ONNXRuntime disponibles."""
        try:
            import onnxruntime as ort
            providers = ort.get_available_providers()
            
            assert 'CPUExecutionProvider' in providers, "CPU provider should always be available"
            
            has_cuda = 'CUDAExecutionProvider' in providers
            print(f"ONNX providers: {providers}")
            print(f"CUDA provider: {'✓' if has_cuda else '✗ (install onnxruntime-gpu)'}")
        except ImportError:
            pytest.skip("ONNXRuntime not installed")
    
    def test_tensorflow_gpu_detection(self):
        """Vérifier que TensorFlow détecte le GPU (optionnel)."""
        try:
            import tensorflow as tf
            gpus = tf.config.list_physical_devices('GPU')
            print(f"TensorFlow GPU devices: {len(gpus)}")
            
            if len(gpus) > 0:
                print(f"TensorFlow GPU available: {[gpu.name for gpu in gpus]}")
            else:
                pytest.skip("TensorFlow GPU not available (install tensorflow-gpu)")
        except ImportError:
            pytest.skip("TensorFlow not installed")


class TestConfigGPUValidation:
    """Tests de validation GPU dans config.settings."""
    
    def test_check_gpu_availability_function(self, monkeypatch):
        """Tester la fonction Config.check_gpu_availability()."""
        from config.settings import Config

        class _CudaStub:
            @staticmethod
            def is_available():
                return True

            @staticmethod
            def get_device_properties(_idx):
                return types.SimpleNamespace(total_memory=int(8 * 1024**3))

            @staticmethod
            def mem_get_info():
                free = int(4 * 1024**3)
                total = int(8 * 1024**3)
                return (free, total)

        torch_stub = types.ModuleType("torch")
        torch_stub.cuda = _CudaStub()
        torch_stub.version = types.SimpleNamespace(cuda="12.0")
        monkeypatch.setitem(sys.modules, "torch", torch_stub)

        ort_stub = types.ModuleType("onnxruntime")
        ort_stub.get_available_providers = lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"]
        monkeypatch.setitem(sys.modules, "onnxruntime", ort_stub)

        result = Config.check_gpu_availability()

        assert result["available"] is True
        assert result["onnx_cuda"] is True
        assert result["vram_total_gb"] > 0
        assert result["vram_free_gb"] > 0
        assert result["cuda_version"]
    
    def test_is_step5_gpu_enabled(self):
        """Tester la lecture de STEP5_ENABLE_GPU."""
        from config.settings import Config
        
        original = os.environ.get('STEP5_ENABLE_GPU')
        try:
            os.environ['STEP5_ENABLE_GPU'] = '0'
            assert Config.is_step5_gpu_enabled() is False
            
            os.environ['STEP5_ENABLE_GPU'] = '1'
            assert Config.is_step5_gpu_enabled() is True
        finally:
            if original is not None:
                os.environ['STEP5_ENABLE_GPU'] = original
            else:
                os.environ.pop('STEP5_ENABLE_GPU', None)
    
    def test_get_step5_gpu_engines(self):
        """Tester la lecture de STEP5_GPU_ENGINES."""
        from config.settings import Config
        
        original = os.environ.get('STEP5_GPU_ENGINES')
        try:
            os.environ['STEP5_GPU_ENGINES'] = 'mediapipe_landmarker,openseeface,insightface'
            engines = Config.get_step5_gpu_engines()

            assert engines == ['insightface']
        finally:
            if original is not None:
                os.environ['STEP5_GPU_ENGINES'] = original
            else:
                os.environ.pop('STEP5_GPU_ENGINES', None)


class TestFaceEngineFactory:
    """Tests de la factory create_face_engine avec flag use_gpu."""
    
    def test_create_unknown_engine_is_rejected(self):
        """Tester create_face_engine rejette un moteur non supporté."""
        sys.path.insert(0, str(project_root / 'workflow_scripts' / 'step5'))

        from face_engines import create_face_engine

        with pytest.raises(ValueError):
            create_face_engine('unknown_engine', use_gpu=True)
    
    def test_create_mediapipe_returns_none(self):
        """Vérifier que MediaPipe retourne None (géré séparément dans workers)."""
        sys.path.insert(0, str(project_root / 'workflow_scripts' / 'step5'))
        
        from face_engines import create_face_engine
        
        assert create_face_engine('mediapipe_landmarker', use_gpu=True) is None
        assert create_face_engine('mediapipe', use_gpu=False) is None

    def test_create_insightface_requires_gpu_flag(self):
        """InsightFace est GPU-only: use_gpu=False doit échouer."""
        sys.path.insert(0, str(project_root / 'workflow_scripts' / 'step5'))

        from face_engines import create_face_engine

        with pytest.raises(RuntimeError):
            create_face_engine('insightface', use_gpu=False)


@pytest.mark.integration
class TestGPUWorkflowIntegration:
    """Tests d'intégration du workflow GPU complet."""
    
    def test_run_tracking_manager_gpu_validation(self):
        """Tester que run_tracking_manager valide correctement le GPU."""
        # Pour l'instant, on vérifie juste que le module charge sans erreur
        sys.path.insert(0, str(project_root / 'workflow_scripts' / 'step5'))
        
        try:
            import run_tracking_manager
            print("✓ run_tracking_manager module loads successfully")
        except Exception as e:
            pytest.fail(f"Failed to load run_tracking_manager: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
