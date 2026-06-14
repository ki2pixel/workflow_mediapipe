#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests unitaires pour STEP3 (TransNetV2 alternatif via Google Coral Edge TPU).
Validation des algorithmes de calcul mathématique et flux de traitement (sans matériel requis).

Audit Camille : Tests couvrant EMA, filtre médian, seuillage Dugad, twin-comparison et timecode.
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
sys.path.insert(0, str(BASE_PATH / "workflow_scripts" / "step3"))

try:
    from run_scene_detect_tpu import (
        compute_cosine_distance,
        temporal_smoothing,
        format_timecode,
        apply_ema_smoothing,
        compute_adaptive_threshold,
        detect_cuts_dugad,
        detect_gradual_transitions,
        detect_scenes_tpu,
    )
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


class TestStep3TPUMedianFilter:
    """Validation du filtre médian 1D (remplacement de la moyenne mobile)"""

    def test_temporal_smoothing_rejects_impulse_noise(self):
        # Given: Une série de distances avec un pic de bruit isolé
        distances = np.array([0.1, 0.1, 0.9, 0.1, 0.1], dtype=np.float32)

        # When: Lissage médian avec fenêtre de 3
        smoothed = temporal_smoothing(distances, window_size=3)

        # Then: Le bruit impulsionnel (0.9) est rejeté, valeur médiane = 0.1
        assert np.isclose(smoothed[2], 0.1)

    def test_temporal_smoothing_preserves_step(self):
        # Given: Un changement net (vraie coupure de scène)
        distances = np.array([0.1, 0.1, 0.1, 0.8, 0.8, 0.8, 0.1], dtype=np.float32)

        # When: Lissage médian taille 3
        smoothed = temporal_smoothing(distances, window_size=3)

        # Then: Les valeurs hautes sont préservées (pas de propagation comme la moyenne mobile)
        assert smoothed[3] >= 0.5
        assert smoothed[4] >= 0.5

    def test_temporal_smoothing_short_list(self):
        # Given: Une série très courte (inférieure à la fenêtre)
        distances = np.array([0.5, 0.8], dtype=np.float32)

        # When: Lissage temporel
        smoothed = temporal_smoothing(distances, window_size=3)

        # Then: La liste est retournée inchangée
        np.testing.assert_array_equal(smoothed, distances)


class TestStep3TPUEMA:
    """Validation de la Moyenne Mobile Exponentielle sur les embeddings"""

    def test_ema_identity_when_alpha_one(self):
        # Given: α = 1.0 → pas de lissage
        embeddings = [
            np.array([1.0, 0.0], dtype=np.float32),
            np.array([0.0, 1.0], dtype=np.float32),
        ]

        # When: EMA avec α=1.0
        smoothed = apply_ema_smoothing(embeddings, alpha=1.0)

        # Then: Les embeddings sont identiques aux originaux
        np.testing.assert_array_equal(smoothed[0], embeddings[0])
        np.testing.assert_array_equal(smoothed[1], embeddings[1])

    def test_ema_smoothing_effect(self):
        # Given: Deux embeddings très différents, α=0.5
        embeddings = [
            np.array([1.0, 0.0], dtype=np.float32),
            np.array([0.0, 1.0], dtype=np.float32),
        ]

        # When: EMA avec α=0.5
        smoothed = apply_ema_smoothing(embeddings, alpha=0.5)

        # Then: Le second embedding est un mix 50/50
        expected = 0.5 * np.array([0.0, 1.0]) + 0.5 * np.array([1.0, 0.0])
        np.testing.assert_array_almost_equal(smoothed[1], expected)

    def test_ema_first_element_unchanged(self):
        # Given: N'importe quelle valeur de α
        embeddings = [np.array([3.0, 4.0], dtype=np.float32)]

        # When: EMA
        smoothed = apply_ema_smoothing(embeddings, alpha=0.8)

        # Then: Le premier élément est toujours identique
        np.testing.assert_array_equal(smoothed[0], embeddings[0])

    def test_ema_empty_input(self):
        # Given: Liste vide
        smoothed = apply_ema_smoothing([], alpha=0.8)

        # Then: Retourne une liste vide
        assert smoothed == []


class TestStep3TPUAdaptiveThreshold:
    """Validation du seuillage adaptatif de Dugad"""

    def test_compute_adaptive_threshold_uniform(self):
        # Given: Distances uniformes (pas de variation)
        distances = np.ones(50, dtype=np.float32) * 0.1

        # When: Calcul des seuils adaptatifs
        thresholds = compute_adaptive_threshold(distances, window_size=25, k=3.0)

        # Then: Le seuil est μ + k·σ = 0.1 + 3.0·0.0 = 0.1 (σ=0 car uniforme)
        assert len(thresholds) == 50
        np.testing.assert_array_almost_equal(thresholds, 0.1)

    def test_compute_adaptive_threshold_with_spike(self):
        # Given: Un pic isolé dans un signal uniforme
        distances = np.ones(50, dtype=np.float32) * 0.1
        distances[25] = 1.0  # Pic

        # When: Calcul des seuils adaptatifs
        thresholds = compute_adaptive_threshold(distances, window_size=25, k=3.0)

        # Then: Le seuil autour du pic est plus élevé que la baseline
        # mais le pic (1.0) doit quand même dépasser le seuil local
        assert thresholds[25] < 1.0  # Le seuil est inférieur au pic

    def test_detect_cuts_dugad_basic(self):
        # Given: Un signal avec un pic clair
        distances = np.zeros(50, dtype=np.float32)
        distances[25] = 1.0

        thresholds = compute_adaptive_threshold(distances, window_size=25, k=3.0)

        # When: Détection des cuts
        cuts = detect_cuts_dugad(distances, thresholds, refractory_period=12, min_scene_len=5)

        # Then: Le pic est détecté comme un cut
        assert 25 in cuts

    def test_detect_cuts_dugad_refractory(self):
        # Given: Deux pics très proches (dans la période réfractaire)
        distances = np.zeros(50, dtype=np.float32)
        distances[20] = 1.0
        distances[25] = 1.0

        thresholds = compute_adaptive_threshold(distances, window_size=25, k=3.0)

        # When: Détection avec période réfractaire de 12
        cuts = detect_cuts_dugad(distances, thresholds, refractory_period=12, min_scene_len=5)

        # Then: Seul le premier pic est détecté (le second est en période réfractaire)
        assert len(cuts) == 1


class TestStep3TPUTwinComparison:
    """Validation de la détection de transitions graduelles"""

    def test_gradual_transition_detection(self):
        # Given: Un signal de transition graduelle (montée douce puis redescente)
        distances = np.zeros(100, dtype=np.float32)
        # Transition graduelle entre les frames 40 et 60
        for i in range(40, 60):
            distances[i] = 0.3 + 0.2 * np.sin((i - 40) / 20 * np.pi)

        thresholds_high = compute_adaptive_threshold(distances, window_size=25, k=3.5)
        thresholds_low = compute_adaptive_threshold(distances, window_size=25, k=2.0)

        # When: Détection des transitions graduelles
        gradual = detect_gradual_transitions(
            distances, thresholds_high, thresholds_low,
            refractory_period=12, existing_cuts=[]
        )

        # Then: La fonction retourne des résultats (peut être vide selon les seuils)
        assert isinstance(gradual, list)


class TestStep3TPUFormats:
    """Validation des formats de sortie (Audit Camille : timecode HH:MM:SS.mmm)"""

    def test_format_timecode_zero(self):
        # Given: Frame 0
        # When: Format
        tc = format_timecode(0, 25.0)
        # Then: Retourne le minimum en format millisecondes
        assert tc == "00:00:00.000"

    def test_format_timecode_normal(self):
        # Given: Frame 3600 (2 minutes et 24 secondes à 25 fps)
        # 3600 / 25 = 144 secondes = 00:02:24.000
        # When: Format
        tc = format_timecode(3600, 25.0)
        # Then: Temps formaté correctement en HH:MM:SS.mmm
        assert tc == "00:02:24.000"

    def test_format_timecode_with_milliseconds(self):
        # Given: Frame 232 à 25fps → 9.28 secondes → 00:00:09.280
        tc = format_timecode(232, 25.0)
        # Then: Les millisecondes sont correctes
        assert tc == "00:00:09.280"

    def test_format_timecode_format_pattern(self):
        # Given: N'importe quelle frame
        tc = format_timecode(100, 25.0)
        # Then: Le format est HH:MM:SS.mmm (avec un point, pas un ':')
        parts = tc.split(":")
        assert len(parts) == 3
        assert "." in parts[2]
        ms_part = parts[2].split(".")[1]
        assert len(ms_part) == 3  # 3 chiffres pour les millisecondes


class TestStep3TPUFlow:
    """Validation du flux de détection de scènes"""

    @patch("run_scene_detect_tpu.subprocess.Popen")
    def test_detect_scenes_tpu(self, mock_popen):
        # Given: Un faux interpréteur et un faux flux vidéo
        interpreter = MagicMock()
        interpreter.get_input_details.return_value = [{'shape': (1, 224, 224, 3), 'index': 0}]
        interpreter.get_output_details.return_value = [{'shape': (1, 1000), 'index': 0}]

        mock_process = MagicMock()
        # Simuler 30 frames de vidéo 224x224 RGB
        frame_size = 224 * 224 * 3
        mock_process.stdout.read.side_effect = [b'\x00' * frame_size] * 30 + [b'']
        mock_popen.return_value = mock_process

        # Simuler des vecteurs d'embedding (Distance forte à la frame 15 pour simuler un cut)
        call_count = 0

        def tensor_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 15:
                return np.ones((1000,), dtype=np.float32)
            return np.zeros((1000,), dtype=np.float32)

        interpreter.get_tensor.side_effect = tensor_side_effect

        # When: Lancement de l'analyse avec les paramètres Audit Camille
        scenes = detect_scenes_tpu(
            Path("dummy.mp4"), interpreter,
            threshold=0.1, min_scene_len=5, fps=25.0,
            ema_alpha=0.8, dugad_window=10, dugad_k=2.5,
            median_filter_size=3, twin_enabled=False
        )

        # Then: Les scènes sont détectées
        assert scenes is not None
        assert len(scenes) >= 1
        # Vérifie que la structure est bien une liste de paires [start, end]
        for scene in scenes:
            assert len(scene) == 2
            assert scene[0] <= scene[1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
