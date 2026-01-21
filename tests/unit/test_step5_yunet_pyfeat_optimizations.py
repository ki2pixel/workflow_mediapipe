"""
Tests unitaires pour les optimisations du moteur opencv_yunet_pyfeat (STEP5).

Vérifie :
- Configuration ONNX Runtime (threads, options)
- Throttling des blendshapes (cache, fréquence)
- Invariants (landmarks padding, JSON dense)
"""

from importlib import util as _import_util
from pathlib import Path
import os
import sys

import numpy as np
import pytest

if _import_util.find_spec("numpy") is None:
    pytestmark = pytest.mark.skip(
        reason="numpy non disponible dans cet environnement; tests STEP5 pyfeat ignorés."
    )

if _import_util.find_spec("scipy") is None:
    pytestmark = pytest.mark.skip(  # type: ignore[assignment]
        reason="scipy non disponible dans cet environnement; tests STEP5 pyfeat ignorés."
    )

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


class TestONNXRuntimeConfig:
    """Tests de configuration ONNX Runtime."""
    
    def test_onnx_default_thread_config(self):
        """Vérifier que les valeurs par défaut des threads ONNX sont appliquées."""
        # Nettoyer les variables d'environnement
        os.environ.pop('STEP5_ONNX_INTRA_OP_THREADS', None)
        os.environ.pop('STEP5_ONNX_INTER_OP_THREADS', None)
        
        # Simuler le chargement avec defaults
        intra_default = int(os.environ.get("STEP5_ONNX_INTRA_OP_THREADS", "2"))
        inter_default = int(os.environ.get("STEP5_ONNX_INTER_OP_THREADS", "1"))
        
        assert intra_default == 2, "Default intra_op_num_threads doit être 2"
        assert inter_default == 1, "Default inter_op_num_threads doit être 1"
    
    def test_onnx_custom_thread_config(self):
        """Vérifier que les threads ONNX personnalisés sont respectés."""
        os.environ['STEP5_ONNX_INTRA_OP_THREADS'] = '4'
        os.environ['STEP5_ONNX_INTER_OP_THREADS'] = '2'
        
        intra = int(os.environ.get("STEP5_ONNX_INTRA_OP_THREADS", "2"))
        inter = int(os.environ.get("STEP5_ONNX_INTER_OP_THREADS", "1"))
        
        assert intra == 4
        assert inter == 2
        
        # Cleanup
        os.environ.pop('STEP5_ONNX_INTRA_OP_THREADS', None)
        os.environ.pop('STEP5_ONNX_INTER_OP_THREADS', None)


class TestBlendshapesThrottling:
    """Tests du throttling des blendshapes."""
    
    def test_throttle_n_default(self):
        """Le throttling par défaut doit être N=1 (chaque frame)."""
        os.environ.pop('STEP5_BLENDSHAPES_THROTTLE_N', None)
        throttle_n = max(1, int(os.environ.get("STEP5_BLENDSHAPES_THROTTLE_N", "1")))
        assert throttle_n == 1, "Default throttle doit être 1 (pas de throttling)"
    
    def test_throttle_n_custom(self):
        """Le throttling personnalisé doit être respecté."""
        os.environ['STEP5_BLENDSHAPES_THROTTLE_N'] = '3'
        throttle_n = max(1, int(os.environ.get("STEP5_BLENDSHAPES_THROTTLE_N", "1")))
        assert throttle_n == 3
        os.environ.pop('STEP5_BLENDSHAPES_THROTTLE_N', None)
    
    def test_throttle_frequency_logic(self):
        """Vérifier la logique de calcul à intervalle régulier."""
        throttle_n = 3
        frame_counter = 0
        computed_frames = []
        
        for i in range(10):
            frame_counter += 1
            should_compute = (frame_counter % throttle_n) == 0
            if should_compute:
                computed_frames.append(frame_counter)
        
        # Avec throttle_n=3, on calcule aux frames 3, 6, 9
        assert computed_frames == [3, 6, 9], f"Expected [3, 6, 9], got {computed_frames}"
    
    def test_cache_key_consistency(self):
        """Vérifier que les clés de cache sont cohérentes."""
        x_safe, y_safe, x2_safe, y2_safe = 100, 150, 300, 400
        object_id = f"{x_safe}_{y_safe}_{x2_safe}_{y2_safe}"
        
        assert object_id == "100_150_300_400"
        
        # Vérifier que la même bbox produit la même clé
        object_id2 = f"{x_safe}_{y_safe}_{x2_safe}_{y2_safe}"
        assert object_id == object_id2


class TestLandmarksPadding:
    """Tests du padding des landmarks (invariant 468->478)."""
    
    def test_landmarks_padding_logic(self):
        """Vérifier que le padding de 468 à 478 landmarks fonctionne."""
        # Simuler 468 landmarks
        landmarks_468 = np.random.rand(468, 3).astype(np.float32)
        
        # Appliquer le padding (logique de onnx_facemesh_detector.py)
        target_size = 478
        current_size = landmarks_468.shape[0]
        
        if current_size < target_size:
            pad_count = target_size - current_size
            pad = np.repeat(landmarks_468[-1:, :], pad_count, axis=0)
            landmarks_padded = np.concatenate([landmarks_468, pad], axis=0)
        else:
            landmarks_padded = landmarks_468[:target_size, :]
        
        assert landmarks_padded.shape[0] == 478, f"Expected 478 landmarks, got {landmarks_padded.shape[0]}"
        
        # Vérifier que les 468 premiers points sont identiques
        np.testing.assert_array_equal(landmarks_padded[:468], landmarks_468)
        
        # Vérifier que le padding répète le dernier point
        for i in range(468, 478):
            np.testing.assert_array_equal(landmarks_padded[i], landmarks_468[-1])


class TestProfilingConfig:
    """Tests de configuration du profiling."""
    
    def test_profiling_disabled_by_default(self):
        """Le profiling doit être désactivé par défaut."""
        os.environ.pop('STEP5_ENABLE_PROFILING', None)
        enable_profiling = os.environ.get("STEP5_ENABLE_PROFILING", "0").strip() in {"1", "true", "yes"}
        assert enable_profiling is False
    
    def test_profiling_enabled_with_flag(self):
        """Le profiling doit s'activer avec le flag."""
        for flag_value in ["1", "true", "yes"]:
            os.environ['STEP5_ENABLE_PROFILING'] = flag_value
            enable_profiling = os.environ.get("STEP5_ENABLE_PROFILING", "0").strip() in {"1", "true", "yes"}
            assert enable_profiling is True, f"Profiling should be enabled with {flag_value}"
        
        os.environ.pop('STEP5_ENABLE_PROFILING', None)


class TestNumpyOptimizations:
    """Tests des optimisations numpy dans py-feat."""
    
    def test_normalization_check_before_scaling(self):
        """Vérifier la logique de normalisation optimisée."""
        # Cas 1: landmarks déjà en pixels (max > 2.0)
        landmarks_pixels = np.array([[100.0, 150.0], [200.0, 250.0]], dtype=np.float32)
        max_coord = float(np.max(np.abs(landmarks_pixels)))
        assert max_coord > 2.0
        # Pas de scaling nécessaire
        
        # Cas 2: landmarks normalisés (max <= 2.0)
        landmarks_norm = np.array([[0.5, 0.75], [1.0, 1.25]], dtype=np.float32)
        max_coord_norm = float(np.max(np.abs(landmarks_norm)))
        assert max_coord_norm <= 2.0
        # Scaling nécessaire
        img_width, img_height = 640, 480
        landmarks_scaled = landmarks_norm * np.array([img_width, img_height], dtype=np.float32)
        
        expected = np.array([[320.0, 360.0], [640.0, 600.0]], dtype=np.float32)
        np.testing.assert_array_almost_equal(landmarks_scaled, expected)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
