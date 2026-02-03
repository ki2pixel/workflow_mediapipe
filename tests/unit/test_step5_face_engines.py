import importlib.util
import sys
import types
from pathlib import Path

import pytest


def _load_face_engines_module(monkeypatch, cv2_stub):
    monkeypatch.setitem(sys.modules, "cv2", cv2_stub)

    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "workflow_scripts" / "step5" / "face_engines.py"
    spec = importlib.util.spec_from_file_location("step5_face_engines_test", module_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_create_face_engine_none_for_mediapipe(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")

    class FakeCascade:
        def empty(self):
            return False

    cv2_stub.CascadeClassifier = lambda _path: FakeCascade()

    module = _load_face_engines_module(monkeypatch, cv2_stub)

    assert module.create_face_engine(None) is None
    assert module.create_face_engine("") is None
    assert module.create_face_engine("mediapipe") is None
    assert module.create_face_engine("mediapipe_landmarker") is None


def test_create_face_engine_rejects_unknown(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")

    module = _load_face_engines_module(monkeypatch, cv2_stub)

    with pytest.raises(ValueError, match="Unsupported tracking engine"):
        module.create_face_engine("unknown_engine")


def test_create_face_engine_insightface_requires_gpu_flag(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")

    module = _load_face_engines_module(monkeypatch, cv2_stub)

    with pytest.raises(RuntimeError, match="GPU-only"):
        module.create_face_engine("insightface", use_gpu=False)


def test_create_face_engine_insightface_creates_engine_with_stubs(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")

    module = _load_face_engines_module(monkeypatch, cv2_stub)

    ort_stub = types.ModuleType("onnxruntime")
    ort_stub.get_available_providers = lambda: ["CUDAExecutionProvider"]
    monkeypatch.setitem(sys.modules, "onnxruntime", ort_stub)

    insightface_app_stub = types.ModuleType("insightface.app")

    class FaceAnalysis:
        def __init__(self, name=None, root=None, providers=None, allowed_modules=None):
            self._init_args = {
                "name": name,
                "root": root,
                "providers": providers,
                "allowed_modules": allowed_modules,
            }

        def prepare(self, ctx_id=0, det_size=(640, 640)):
            self._prepared = True

        def get(self, _frame):
            return []

    insightface_app_stub.FaceAnalysis = FaceAnalysis
    monkeypatch.setitem(sys.modules, "insightface.app", insightface_app_stub)

    engine = module.create_face_engine("insightface", use_gpu=True)
    assert engine is not None
    assert hasattr(engine, "detect")
