#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests de non-régression des optimisations STEP4 TPU (niveau ``STEP4_TPU_FAST``).

Chaque optimisation refactorée est comparée à son implémentation d'origine sur
des données réelles : les gains ne doivent introduire aucun écart fonctionnel.
"""

import importlib
import importlib.util
import math
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

if importlib.util.find_spec("numpy") is None:
    pytestmark = pytest.mark.skip(reason="numpy non disponible dans cet environnement; tests ignorés.")
else:
    import numpy as np

    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    sys.modules.setdefault('pycoral', MagicMock())
    sys.modules.setdefault('tflite_runtime', MagicMock())
    sys.modules.setdefault('tflite_runtime.interpreter', MagicMock())

    from utils import tpu_facemesh_utils as face_utils
    from utils.one_euro_filter import OneEuroFilterND
    from utils.tracking_optimizations import apply_tracking_and_management


def _legacy_anchors():
    """Implémentation d'origine (boucle Python) conservée comme référence."""
    anchors = []
    strides = [8, 16]
    anchors_per_layer = [2, 6]
    image_size = 128.0
    for index, stride in enumerate(strides):
        grid_rows = int(image_size / stride)
        grid_cols = int(image_size / stride)
        for row in range(grid_rows):
            for col in range(grid_cols):
                y_center = (row + 0.5) / grid_rows
                x_center = (col + 0.5) / grid_cols
                for _ in range(anchors_per_layer[index]):
                    anchors.append([x_center, y_center, 1.0, 1.0])
    return np.array(anchors, dtype=np.float32)


def _legacy_one_euro_update(filter_obj, x):
    """Formule d'origine : un appel JIT par coefficient."""
    from utils.one_euro_filter import _exponential_smoothing, _smoothing_factor

    x = np.asarray(x, dtype=np.float64)
    if not filter_obj.is_initialized:
        filter_obj.x_prev = x.copy()
        filter_obj.is_initialized = True
        return x.copy()
    t_e = 1.0 / filter_obj.rate
    a_d = _smoothing_factor(t_e, filter_obj.d_cutoff)
    dx = (x - filter_obj.x_prev) / t_e
    dx_hat = _exponential_smoothing(a_d, dx, filter_obj.dx_prev)
    cutoff = filter_obj.min_cutoff + filter_obj.beta * np.abs(dx_hat)
    a = np.array([_smoothing_factor(t_e, c) for c in cutoff], dtype=np.float64)
    x_hat = _exponential_smoothing(a, x, filter_obj.x_prev)
    filter_obj.x_prev = x_hat.copy()
    filter_obj.dx_prev = dx_hat.copy()
    return x_hat


class TestBlazefaceAnchors:
    def test_cached_anchors_match_legacy_values(self):
        # Given: la version mise en cache et l'implémentation d'origine
        cached = face_utils.generate_blazeface_anchors()
        legacy = _legacy_anchors()

        # When/Then: les 896 ancres sont identiques valeur pour valeur et dans le même ordre
        assert cached.shape == (896, 4)
        assert cached.dtype == np.float32
        assert np.array_equal(cached, legacy)

    def test_anchors_are_shared_between_calls(self):
        # Given/When: deux appels successifs
        first = face_utils.generate_blazeface_anchors()
        second = face_utils.generate_blazeface_anchors()

        # Then: la même instance est retournée (plus de régénération par frame)
        assert first is second


class TestOneEuroVectorization:
    def test_vectorized_update_matches_legacy_formula(self):
        # Given: deux filtres alimentés par la même séquence
        vectorized = OneEuroFilterND(dim=52, rate=25.0)
        legacy = OneEuroFilterND(dim=52, rate=25.0)
        rng = np.random.default_rng(42)

        # When: la séquence est filtrée par les deux implémentations
        for _ in range(60):
            sample = rng.random(52)
            fast = vectorized.update(sample)
            reference = _legacy_one_euro_update(legacy, sample)

            # Then: les sorties coïncident à la précision machine
            assert np.allclose(fast, reference, atol=1e-12)

    def test_state_is_preserved_between_updates(self):
        # Given: un filtre initialisé avec un premier vecteur
        filter_obj = OneEuroFilterND(dim=8, rate=30.0)
        filter_obj.update(np.ones(8))

        # When: un second vecteur est filtré
        result = filter_obj.update(np.zeros(8))

        # Then: l'état interne a été mis à jour (sortie intermédiaire entre 0 et 1)
        assert 0.0 < float(result[0]) < 1.0
        assert np.allclose(filter_obj.x_prev, result)


class TestTrackingWithoutKdTree:
    def _run(self, active_objects, detections):
        return apply_tracking_and_management(
            active_objects=active_objects,
            current_detections=detections,
            next_id_counter={"value": len(active_objects)},
            distance_threshold=100.0,
            frames_unseen_to_deregister=10,
            current_frame_num=5,
        )

    def test_nearest_matching_is_equivalent_to_bruteforce(self):
        # Given: trois objets suivis et deux détections décalées
        active_objects = {
            "obj_1": {"centroid": (100, 100), "bbox": (90, 90, 20, 20), "frames_unseen": 0},
            "obj_2": {"centroid": (500, 500), "bbox": (490, 490, 20, 20), "frames_unseen": 0},
            "obj_3": {"centroid": (900, 100), "bbox": (890, 90, 20, 20), "frames_unseen": 0},
        }
        detections = [
            {"centroid": (110, 105), "bbox": (100, 95, 20, 20), "source_detector": "face_landmarker", "label": "face", "confidence": 0.9, "blendshapes": {}},
            {"centroid": (880, 120), "bbox": (870, 110, 20, 20), "source_detector": "face_landmarker", "label": "face", "confidence": 0.9, "blendshapes": {}},
        ]

        # When: l'appariement est calculé sans KDTree
        output = self._run(active_objects, detections)

        # Then: chaque détection rejoint l'objet suivi le plus proche
        by_id = {obj["id"]: obj for obj in output}
        assert by_id["obj_1"]["centroid_x"] == 110
        assert by_id["obj_3"]["centroid_x"] == 880
        assert "obj_2" not in by_id  # non vu cette frame
        assert len(output) == 2

    def test_detection_beyond_threshold_creates_new_track(self):
        # Given: une détection éloignée de l'objet suivi
        active_objects = {
            "obj_1": {"centroid": (10, 10), "bbox": (0, 0, 20, 20), "frames_unseen": 0},
        }
        detections = [
            {"centroid": (900, 700), "bbox": (890, 690, 20, 20), "source_detector": "face_landmarker", "label": "face", "confidence": 0.9, "blendshapes": {}},
        ]

        # When: l'appariement est calculé
        output = self._run(active_objects, detections)

        # Then: un nouvel identifiant est créé, l'ancien reste suivi mais n'est pas réémis
        assert [obj["id"] for obj in output] == ["obj_2"]
        assert set(active_objects) == {"obj_1", "obj_2"}
        assert active_objects["obj_1"]["frames_unseen"] == 1
        assert active_objects["obj_2"]["frames_unseen"] == 0

    def test_nearest_index_matches_bruteforce_distances(self):
        # Given: une grille d'objets suivis et de détections aléatoires
        from utils.tracking_optimizations import _nearest_tracked_indices

        rng = np.random.default_rng(7)
        tracked = rng.random((12, 2)) * 1000
        detections = rng.random((9, 2)) * 1000

        # When: les indices les plus proches sont calculés en NumPy
        distances, indices = _nearest_tracked_indices(tracked, detections)

        # Then: ils correspondent au calcul exhaustif
        for row, detection in enumerate(detections):
            expected = int(np.argmin([np.hypot(*(detection - tracked_point)) for tracked_point in tracked]))
            assert int(indices[row]) == expected
            assert distances[row] == pytest.approx(
                math.hypot(*(detection - tracked[expected])), abs=1e-9
            )


class TestFastLevelFlags:
    def _load_script(self, fast_value):
        """Importe run_tracking_tpu avec un niveau FAST donné (module isolé)."""
        module_name = "run_tracking_tpu"
        saved = sys.modules.pop(module_name, None)
        previous = sys.path[:]
        sys.path.insert(0, str(PROJECT_ROOT / "workflow_scripts" / "step4"))
        try:
            if fast_value is None:
                import os
                os.environ.pop("STEP4_TPU_FAST", None)
            else:
                import os
                os.environ["STEP4_TPU_FAST"] = str(fast_value)
            module = importlib.import_module(module_name)
            return module
        finally:
            sys.path[:] = previous
            sys.modules.pop(module_name, None)
            if saved is not None:
                sys.modules[module_name] = saved

    def test_object_detection_hysteresis_defaults(self):
        # Given: le niveau d'optimisation historique puis le niveau sûr
        legacy = self._load_script(0)
        optimized = self._load_script(1)

        # When: le seuil d'hystérésis est résolu
        # Then: le comportement historique invoque le détecteur dès la première frame sans visage
        assert legacy.fast_level() == 0
        assert legacy.object_detection_min_missing_frames() == 1
        assert optimized.fast_level() == 1
        assert optimized.object_detection_min_missing_frames() == 25

    def test_explicit_override_wins(self):
        # Given: une valeur explicite d'hystérésis
        import os

        optimized = self._load_script(1)
        os.environ["STEP4_TPU_OBJECT_DETECTION_MIN_MISSING"] = "40"

        # When/Then: elle prime sur le défaut du niveau
        try:
            assert optimized.object_detection_min_missing_frames() == 40
        finally:
            os.environ.pop("STEP4_TPU_OBJECT_DETECTION_MIN_MISSING", None)

    def test_object_detection_face_reset_defaults_to_legacy(self):
        # Given: les deux niveaux d'optimisation
        legacy = self._load_script(0)
        optimized = self._load_script(1)

        # When/Then: le réarmement reste historique (toute détection de visage réarme)
        assert legacy.object_detection_reset_frames() == 1
        assert optimized.object_detection_reset_frames() == 1

    def test_object_detection_face_reset_override(self):
        # Given: l'exigence d'un visage soutenu avant de réarmer le compteur
        import os

        optimized = self._load_script(1)
        os.environ["STEP4_TPU_OBJECT_DETECTION_FACE_RESET_FRAMES"] = "3"

        # When/Then: la valeur explicite est retenue
        try:
            assert optimized.object_detection_reset_frames() == 3
        finally:
            os.environ.pop("STEP4_TPU_OBJECT_DETECTION_FACE_RESET_FRAMES", None)

    def test_json_flush_frequency_follows_level(self):
        # Given/When: les deux niveaux
        legacy = self._load_script(0)
        optimized = self._load_script(1)

        # Then: le niveau sûr tamponne les écritures JSON
        assert legacy._JSON_FLUSH_EVERY == 1
        assert optimized._JSON_FLUSH_EVERY == 100

    def test_cpu_thread_defaults_to_single_thread(self):
        # Given/When: aucun réglage explicite
        module = self._load_script(1)

        # Then: le comportement historique (1 thread) est conservé
        assert module._cpu_threads() == 1


class TestInterpreterMetaCache:
    def test_metadata_is_resolved_once_per_interpreter(self):
        # Given: un faux interpréteur comptant ses appels
        module = importlib.import_module("run_tracking_tpu") if "run_tracking_tpu" in sys.modules else None
        if module is None:
            saved = sys.modules.pop("run_tracking_tpu", None)
            sys.path.insert(0, str(PROJECT_ROOT / "workflow_scripts" / "step4"))
            try:
                module = importlib.import_module("run_tracking_tpu")
            finally:
                sys.path.pop(0)
                if saved is not None:
                    sys.modules["run_tracking_tpu"] = saved

        calls = {"input": 0, "output": 0}

        class FakeInterpreter:
            def get_input_details(self):
                calls["input"] += 1
                return [{"index": 3, "shape": np.array([1, 192, 192, 3]), "dtype": np.uint8}]

            def get_output_details(self):
                calls["output"] += 1
                return [{"index": 9, "shape": np.array([1, 468, 3]), "dtype": np.float32}]

            def tensor(self, index):
                return lambda: np.zeros((1, 1, 1, 1), dtype=np.uint8)

        interpreter = FakeInterpreter()

        # When: les métadonnées sont demandées trois fois
        first = module._interpreter_meta(interpreter)
        module._interpreter_meta(interpreter)
        third = module._interpreter_meta(interpreter)

        # Then: elles ne sont résolues qu'une fois et restent stables
        assert calls == {"input": 1, "output": 1}
        assert first is third
        assert first["input_height"] == 192
        assert first["input_width"] == 192
        assert first["output_indices"] == [9]
