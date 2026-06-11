#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests unitaires pour STEP5 (Tracking avancé et Filtre de Kalman via Google Coral Edge TPU).
"""

import sys
import pytest
from pathlib import Path
from importlib import util as _import_util
from unittest.mock import MagicMock

if _import_util.find_spec("numpy") is None:
    pytestmark = pytest.mark.skip(reason="numpy non disponible dans cet environnement; tests ignorés.")
else:
    import numpy as np

# --- MOCKING PYCORAL & TFLITE ---
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

BASE_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_PATH / "workflow_scripts" / "step5"))

try:
    from run_tracking_tpu import KalmanFilterND, run_tracking_pipeline, detect_face, extract_landmarks, extract_blendshapes
except ImportError as e:
    pytest.skip(f"Impossible d'importer run_tracking_tpu: {e}", allow_module_level=True)

class TestKalmanFilterND:
    """Validation du filtre de Kalman vectorisé pour le lissage des blendshapes (CPU)"""

    def test_kalman_filter_initialization(self):
        # Given: Initialisation du filtre
        # When: L'objet est créé
        kf = KalmanFilterND(dim=52, process_variance=1e-4, measurement_variance=1e-2)
        
        # Then: L'état initial est correct
        assert kf.dim == 52
        assert not kf.is_initialized
        assert kf.x.shape == (52,)
        assert kf.p.shape == (52,)

    def test_kalman_filter_first_update(self):
        # Given: Un filtre non initialisé et une première mesure
        kf = KalmanFilterND(dim=3)
        measure = [0.1, 0.5, 0.9]
        
        # When: Première mise à jour
        result = kf.update(measure)
        
        # Then: L'état prend exactement la valeur de la mesure
        assert kf.is_initialized
        np.testing.assert_array_equal(result, np.array(measure, dtype=np.float32))
        np.testing.assert_array_equal(kf.x, np.array(measure, dtype=np.float32))

    def test_kalman_filter_smoothing(self):
        # Given: Un filtre initialisé et des mesures bruitées
        kf = KalmanFilterND(dim=1, process_variance=1e-4, measurement_variance=1e-1)
        kf.update([0.5]) # Initialisation
        
        # When: Ajout d'une mesure bruitée
        result = kf.update([1.0])
        
        # Then: Le filtre atténue le changement brut (smooths the jitter)
        # result doit être entre 0.5 et 1.0, mais plus proche de 0.5 vu que r est grand par rapport à q
        assert 0.5 < result[0] < 1.0
        assert result[0] < 0.96 # Preuve de l'atténuation

class TestStep5TPUFlow:
    """Validation du pipeline de tracking TPU"""

    def test_tracking_pipeline_mocks(self):
        # Given: Des interpréteurs simulés
        blazeface = MagicMock()
        facemesh = MagicMock()
        blendshapes = MagicMock()
        
        # When: Test unitaire des fonctions d'extraction individuelles
        bbox = detect_face(blazeface, np.zeros((256, 256, 3), dtype=np.uint8))
        assert len(bbox) == 4
        
        # FaceMesh
        facemesh.get_output_details.return_value = [{'shape': (1, 468, 3)}]
        # Mocking du retour tensoriel
        mock_common.output_tensor.return_value = [np.zeros((468, 3))]
        landmarks = extract_landmarks(facemesh, np.zeros((256, 256, 3), dtype=np.uint8))
        assert landmarks.shape == (468, 3)
        
        # Blendshapes
        blendshapes.get_input_details.return_value = [{'shape': (1, 1404), 'dtype': np.float32}]
        mock_common.output_tensor.return_value = [np.zeros(52)]
        bshapes = extract_blendshapes(blendshapes, landmarks)
        assert len(bshapes) == 52

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
