#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests unitaires pour STEP3 (TransNetV2 alternatif via Google Coral Edge TPU).
Validation des algorithmes de calcul mathématique et flux de traitement (sans matériel requis).
"""

import sys
import pytest
from pathlib import Path
from importlib import util as _import_util
from unittest.mock import MagicMock, patch

if _import_util.find_spec("numpy") is None:
    pytestmark = pytest.mark.skip(reason="numpy non disponible dans cet environnement; tests ignorés.")
else:
    import numpy as np

# --- MOCKING PYCORAL & TFLITE ---
# Permet l'import de run_scene_detect_tpu sans RuntimeError
mock_edgetpu = MagicMock()
mock_common = MagicMock()
mock_tflite = MagicMock()

sys.modules['pycoral'] = MagicMock()
sys.modules['pycoral.utils'] = MagicMock()
sys.modules['pycoral.utils.edgetpu'] = mock_edgetpu
mock_adapters = MagicMock()
mock_adapters.common = mock_common
sys.modules['pycoral.adapters'] = mock_adapters
sys.modules['pycoral.adapters.common'] = mock_common
sys.modules['tflite_runtime'] = MagicMock()
sys.modules['tflite_runtime.interpreter'] = mock_tflite

# Ajouter le chemin du projet pour résoudre le module
BASE_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_PATH / "scripts" / "workflow_scripts" / "step3"))

try:
    from run_scene_detect_tpu import compute_cosine_distance, temporal_smoothing, format_timecode, detect_scenes_tpu
except ImportError as e:
    pytest.skip(f"Impossible d'importer run_scene_detect_tpu: {e}", allow_module_level=True)

class TestStep3TPUMath:
    """Validation des fonctions mathématiques CPU pour compenser le TPU"""

    def test_compute_cosine_distance_normal(self):
        # Given: Deux vecteurs distincts
        v1 = np.array([1.0, 0.0], dtype=np.float32)
        v2 = np.array([0.0, 1.0], dtype=np.float32)
        
        # When: Calcul de la distance cosinus
        dist = compute_cosine_distance(v1, v2)
        
        # Then: La distance doit être de 1.0 pour des vecteurs orthogonaux
        assert np.isclose(dist, 1.0)

        # Given: Deux vecteurs identiques
        v3 = np.array([0.5, 0.5], dtype=np.float32)
        
        # When: Calcul
        dist_same = compute_cosine_distance(v3, v3)
        
        # Then: La distance doit être de 0.0
        assert np.isclose(dist_same, 0.0, atol=1e-6)

    def test_compute_cosine_distance_zero_vector(self):
        # Given: Un vecteur nul (limite)
        v_zero = np.array([0.0, 0.0], dtype=np.float32)
        v_normal = np.array([1.0, 1.0], dtype=np.float32)
        
        # When: Calcul de distance avec vecteur nul
        dist = compute_cosine_distance(v_zero, v_normal)
        
        # Then: Retourne 0.0 sans division par zéro
        assert dist == 0.0

    def test_temporal_smoothing_normal(self):
        # Given: Une série de distances avec un pic de bruit isolé
        distances = np.array([0.1, 0.1, 0.9, 0.1, 0.1], dtype=np.float32)
        
        # When: Lissage avec fenêtre de 3 (médiane glissante)
        smoothed = temporal_smoothing(distances, window_size=3)
        
        # Then: Le bruit (0.9) est lissé
        # Ex: index 2: median([0.1, 0.9, 0.1]) -> 0.1
        assert np.isclose(smoothed[2], 0.1)

    def test_temporal_smoothing_short_list(self):
        # Given: Une série très courte (inférieure à la fenêtre)
        distances = np.array([0.5, 0.8], dtype=np.float32)
        
        # When: Lissage temporel
        smoothed = temporal_smoothing(distances, window_size=3)
        
        # Then: La liste est retournée inchangée
        np.testing.assert_array_equal(smoothed, distances)

class TestStep3TPUFormats:
    """Validation des formats de sortie"""

    def test_format_timecode_zero(self):
        # Given: Frame 0
        # When: Format
        tc = format_timecode(0, 25.0)
        # Then: Retourne le minimum
        assert tc == "00:00:00:00"

    def test_format_timecode_normal(self):
        # Given: Frame 3600 (2 minutes et 24 secondes à 25 fps)
        # 3600 / 25 = 144 secondes = 00:02:24:00
        # When: Format
        tc = format_timecode(3600, 25.0)
        # Then: Temps formaté correctement
        assert tc == "00:02:24:00"

class TestStep3TPUFlow:
    """Validation du flux de détection de scènes"""

    @patch("run_scene_detect_tpu.subprocess.Popen")
    @patch("run_scene_detect_tpu.common.output_tensor")
    def test_detect_scenes_tpu(self, mock_output_tensor, mock_popen):
        # Given: Un faux interpréteur et un faux flux vidéo
        interpreter = MagicMock()
        interpreter.get_input_details.return_value = [{'shape': (1, 224, 224, 3)}]
        interpreter.get_output_details.return_value = [{'shape': (1, 1000)}]
        
        mock_process = MagicMock()
        # Simuler 30 frames de vidéo 224x224 RGB
        frame_size = 224 * 224 * 3
        mock_process.stdout.read.side_effect = [b'\x00' * frame_size] * 30 + [b'']
        mock_popen.return_value = mock_process

        # Simuler des vecteurs d'embedding (Distance forte à la frame 15 pour simuler un cut)
        def tensor_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 15:
                return np.ones((1000,), dtype=np.float32)
            return np.zeros((1000,), dtype=np.float32)
        
        call_count = 0
        mock_output_tensor.side_effect = tensor_side_effect

        # When: Lancement de l'analyse (seuil très bas pour capter le mock)
        scenes = detect_scenes_tpu(Path("dummy.mp4"), interpreter, threshold=0.1, min_scene_len=5, fps=25.0)
        
        # Then: Les scènes sont détectées
        assert scenes is not None
        assert len(scenes) >= 1
        # Vérifie que la structure est bien une liste de paires [start, end]
        for scene in scenes:
            assert len(scene) == 2
            assert scene[0] <= scene[1]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
