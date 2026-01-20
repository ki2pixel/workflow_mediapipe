import sys
import types

import pytest


def _install_scipy_stub_if_missing():
    if "scipy" in sys.modules:
        return
    scipy_stub = types.ModuleType("scipy")
    spatial_stub = types.ModuleType("scipy.spatial")

    class KDTree:
        def __init__(self, _data):
            raise RuntimeError("KDTree should not be instantiated in this unit test")

    spatial_stub.KDTree = KDTree
    scipy_stub.spatial = spatial_stub

    sys.modules["scipy"] = scipy_stub
    sys.modules["scipy.spatial"] = spatial_stub


_install_scipy_stub_if_missing()


from utils.tracking_optimizations import apply_tracking_and_management


def test_blendshapes_profile_mouth_filters_keys(monkeypatch):
    monkeypatch.setenv("STEP5_BLENDSHAPES_PROFILE", "mouth")
    monkeypatch.delenv("STEP5_BLENDSHAPES_INCLUDE_TONGUE", raising=False)

    det = {
        "bbox": (0, 0, 10, 10),
        "centroid": (5, 5),
        "source_detector": "face_landmarker",
        "label": "face",
        "confidence": 0.9,
        "blendshapes": {
            "jawOpen": 0.1,
            "mouthSmileLeft": 0.2,
            "browDownLeft": 0.3,
            "tongueOut": 0.4,
        },
    }

    out = apply_tracking_and_management(
        active_objects={},
        current_detections=[det],
        next_id_counter={"value": 0},
        distance_threshold=9999,
        frames_unseen_to_deregister=1,
        current_frame_num=1,
    )

    assert len(out) == 1
    blend = out[0]["blendshapes"]
    assert isinstance(blend, dict)
    assert set(blend.keys()) == {"jawOpen", "mouthSmileLeft"}


def test_blendshapes_profile_mouth_can_include_tongue(monkeypatch):
    monkeypatch.setenv("STEP5_BLENDSHAPES_PROFILE", "mouth")
    monkeypatch.setenv("STEP5_BLENDSHAPES_INCLUDE_TONGUE", "1")

    det = {
        "bbox": (0, 0, 10, 10),
        "centroid": (5, 5),
        "source_detector": "face_landmarker",
        "label": "face",
        "confidence": 0.9,
        "blendshapes": {
            "jawOpen": 0.1,
            "tongueOut": 0.4,
        },
    }

    out = apply_tracking_and_management(
        active_objects={},
        current_detections=[det],
        next_id_counter={"value": 0},
        distance_threshold=9999,
        frames_unseen_to_deregister=1,
        current_frame_num=1,
    )

    assert len(out) == 1
    blend = out[0]["blendshapes"]
    assert isinstance(blend, dict)
    assert set(blend.keys()) == {"jawOpen", "tongueOut"}


def test_blendshapes_profile_none_disables_export(monkeypatch):
    monkeypatch.setenv("STEP5_BLENDSHAPES_PROFILE", "none")

    det = {
        "bbox": (0, 0, 10, 10),
        "centroid": (5, 5),
        "source_detector": "face_landmarker",
        "label": "face",
        "confidence": 0.9,
        "blendshapes": {
            "jawOpen": 0.1,
            "mouthSmileLeft": 0.2,
        },
    }

    out = apply_tracking_and_management(
        active_objects={},
        current_detections=[det],
        next_id_counter={"value": 0},
        distance_threshold=9999,
        frames_unseen_to_deregister=1,
        current_frame_num=1,
    )

    assert len(out) == 1
    assert out[0]["blendshapes"] is None
