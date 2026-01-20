"""
Tests unitaires pour le support GPU STEP5 (MediaPipe + OpenSeeFace).

Ces tests vérifient:
- Disponibilité des providers GPU (ONNX CUDA, TensorFlow)
- Initialisation des moteurs avec flag use_gpu
- Fallback automatique vers CPU si GPU indisponible
"""

import pytest
import os
import sys
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
            pytest.skip("PyTorch not installed in tracking_env")
    
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
            pytest.fail("ONNXRuntime not installed in tracking_env")
    
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
    
    def test_check_gpu_availability_function(self):
        """Tester la fonction Config.check_gpu_availability()."""
        from config.settings import Config
        
        result = Config.check_gpu_availability()
        
        assert 'available' in result
        assert 'reason' in result
        assert 'onnx_cuda' in result
        assert 'tensorflow_gpu' in result
        
        if result['available']:
            assert 'vram_total_gb' in result
            assert 'vram_free_gb' in result
            assert 'cuda_version' in result
            assert result['vram_total_gb'] > 0
            print(f"GPU available: {result['vram_total_gb']:.1f} GB total, {result['vram_free_gb']:.1f} GB free")
        else:
            print(f"GPU not available: {result['reason']}")
    
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
            os.environ['STEP5_GPU_ENGINES'] = 'mediapipe_landmarker,openseeface'
            engines = Config.get_step5_gpu_engines()
            
            assert 'mediapipe_landmarker' in engines
            assert 'openseeface' in engines
            assert len(engines) == 2
        finally:
            if original is not None:
                os.environ['STEP5_GPU_ENGINES'] = original
            else:
                os.environ.pop('STEP5_GPU_ENGINES', None)


@pytest.mark.gpu
class TestOpenSeeFaceGPU:
    """Tests spécifiques à OpenSeeFace avec GPU (nécessite onnxruntime-gpu)."""
    
    @pytest.fixture
    def check_onnx_cuda(self):
        """Vérifier que ONNX CUDA provider est disponible."""
        try:
            import onnxruntime as ort
            if 'CUDAExecutionProvider' not in ort.get_available_providers():
                pytest.skip("ONNX CUDA provider not available (install onnxruntime-gpu)")
        except ImportError:
            pytest.skip("ONNXRuntime not installed")
    
    def test_openseeface_engine_gpu_flag(self, check_onnx_cuda):
        """Tester l'initialisation d'OpenSeeFace avec use_gpu=True."""
        sys.path.insert(0, str(project_root / 'workflow_scripts' / 'step5'))
        
        try:
            from face_engines import OpenSeeFaceEngine
            
            engine = OpenSeeFaceEngine(use_gpu=True)
            assert engine._use_gpu is True
            
            detection_providers = engine._detection_session.get_providers()
            landmark_providers = engine._landmark_session.get_providers()
            
            assert detection_providers[0] == 'CUDAExecutionProvider', \
                f"Expected CUDA provider first, got: {detection_providers}"
            assert landmark_providers[0] == 'CUDAExecutionProvider', \
                f"Expected CUDA provider first, got: {landmark_providers}"
            
            print(f"✓ OpenSeeFace GPU mode active (providers: {detection_providers})")
        except Exception as e:
            pytest.fail(f"Failed to initialize OpenSeeFace with GPU: {e}")
    
    def test_openseeface_cpu_fallback(self):
        """Tester que OpenSeeFace fonctionne en mode CPU (fallback)."""
        sys.path.insert(0, str(project_root / 'workflow_scripts' / 'step5'))
        
        try:
            from face_engines import OpenSeeFaceEngine
            
            engine = OpenSeeFaceEngine(use_gpu=False)
            assert engine._use_gpu is False
            
            assert 'CPUExecutionProvider' in detection_providers
            
            print(f"✓ OpenSeeFace CPU mode active (providers: {detection_providers})")
        except Exception as e:
            pytest.fail(f"Failed to initialize OpenSeeFace with CPU: {e}")


@pytest.mark.gpu
class TestMediaPipeGPU:
    """Tests spécifiques à MediaPipe avec GPU delegate (nécessite TensorFlow GPU)."""
    
    @pytest.fixture
    def check_tensorflow_gpu(self):
        """Vérifier que TensorFlow GPU est disponible."""
        try:
            import tensorflow as tf
            gpus = tf.config.list_physical_devices('GPU')
            if len(gpus) == 0:
                pytest.skip("TensorFlow GPU not available (install tensorflow-gpu)")
        except ImportError:
            pytest.skip("TensorFlow not installed")
    
    def test_mediapipe_gpu_delegate_available(self, check_tensorflow_gpu):
        """Vérifier que le GPU delegate MediaPipe est accessible."""
        try:
            import mediapipe as mp
            BaseOptions = mp.tasks.BaseOptions
            
            try:
                delegate = BaseOptions.Delegate.GPU
                print(f"✓ MediaPipe GPU delegate available: {delegate}")
            except AttributeError:
                pytest.fail("MediaPipe GPU delegate not available (check MediaPipe version)")
        except ImportError:
            pytest.skip("MediaPipe not installed")


class TestFaceEngineFactory:
    """Tests de la factory create_face_engine avec flag use_gpu."""
    
    def test_create_openseeface_with_gpu_flag(self):
        """Tester create_face_engine pour OpenSeeFace avec GPU."""
        sys.path.insert(0, str(project_root / 'workflow_scripts' / 'step5'))
        
        try:
            from face_engines import create_face_engine, OpenSeeFaceEngine
            
            engine = create_face_engine('openseeface', use_gpu=True)
            assert isinstance(engine, OpenSeeFaceEngine)
            assert engine._use_gpu is True
            
            engine_cpu = create_face_engine('openseeface', use_gpu=False)
            assert isinstance(engine_cpu, OpenSeeFaceEngine)
            assert engine_cpu._use_gpu is False
            
            print("✓ create_face_engine respects use_gpu flag")
        except Exception as e:
            pytest.fail(f"Factory function failed: {e}")
    
    def test_create_mediapipe_returns_none(self):
        """Vérifier que MediaPipe retourne None (géré séparément dans workers)."""
        sys.path.insert(0, str(project_root / 'workflow_scripts' / 'step5'))
        
        from face_engines import create_face_engine
        
        assert create_face_engine('mediapipe_landmarker', use_gpu=True) is None
        assert create_face_engine('mediapipe', use_gpu=False) is None


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
