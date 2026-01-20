import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest


def _load_face_engines_module(monkeypatch, cv2_stub):
    monkeypatch.setitem(sys.modules, "cv2", cv2_stub)

    numpy_stub = types.ModuleType("numpy")
    numpy_stub.ndarray = object
    numpy_stub.float32 = float
    numpy_stub.clip = lambda v, _min, _max: v
    numpy_stub.log = lambda v: v
    numpy_stub.asarray = lambda v, dtype=None: v
    monkeypatch.setitem(sys.modules, "numpy", numpy_stub)

    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "workflow_scripts" / "step5" / "face_engines.py"
    spec = importlib.util.spec_from_file_location("step5_face_engines_test_insightface", module_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_insightface_engine_rejects_cpu_mode(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")

    class FakeCascade:
        def empty(self):
            return False

    cv2_stub.CascadeClassifier = lambda _path: FakeCascade()

    module = _load_face_engines_module(monkeypatch, cv2_stub)

    with pytest.raises(RuntimeError, match="GPU-only"):
        module.create_face_engine("insightface", use_gpu=False)


def test_insightface_engine_requires_cuda_provider(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")

    class FakeCascade:
        def empty(self):
            return False

    cv2_stub.CascadeClassifier = lambda _path: FakeCascade()

    fake_ort = types.ModuleType("onnxruntime")
    fake_ort.get_available_providers = lambda: ["CPUExecutionProvider"]

    monkeypatch.setitem(sys.modules, "onnxruntime", fake_ort)

    module = _load_face_engines_module(monkeypatch, cv2_stub)

    with pytest.raises(RuntimeError, match="CUDAExecutionProvider"):
        module.create_face_engine("insightface", use_gpu=True)


def test_insightface_engine_initializes_with_cuda_provider(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")
    cv2_stub.INTER_LINEAR = 1
    cv2_stub.resize = lambda frame, _size, interpolation=None: frame

    class FakeCascade:
        def empty(self):
            return False

    cv2_stub.CascadeClassifier = lambda _path: FakeCascade()

    fake_ort = types.ModuleType("onnxruntime")
    fake_ort.get_available_providers = lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"]

    monkeypatch.setitem(sys.modules, "onnxruntime", fake_ort)

    insightface_pkg = types.ModuleType("insightface")
    insightface_app = types.ModuleType("insightface.app")

    class _FakeFaceAnalysis:
        def __init__(self, name=None, root=None, providers=None, allowed_modules=None, **_kwargs):
            self.name = name
            self.root = root
            self.providers = providers
            self.allowed_modules = allowed_modules
            self.prepared = False

        def prepare(self, ctx_id=0, det_size=(640, 640)):
            self.prepared = True

        def get(self, _frame):
            return []

    insightface_app.FaceAnalysis = _FakeFaceAnalysis

    monkeypatch.setitem(sys.modules, "insightface", insightface_pkg)
    monkeypatch.setitem(sys.modules, "insightface.app", insightface_app)

    module = _load_face_engines_module(monkeypatch, cv2_stub)

    engine = module.create_face_engine("insightface", use_gpu=True)
    assert engine is not None
    assert getattr(engine, "_use_gpu", False) is True


def test_insightface_engine_quarantines_model_dir_on_file_exists(monkeypatch, tmp_path):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")
    cv2_stub.INTER_LINEAR = 1
    cv2_stub.resize = lambda frame, _size, interpolation=None: frame

    class FakeCascade:
        def empty(self):
            return False

    cv2_stub.CascadeClassifier = lambda _path: FakeCascade()

    fake_ort = types.ModuleType("onnxruntime")
    fake_ort.get_available_providers = lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"]
    monkeypatch.setitem(sys.modules, "onnxruntime", fake_ort)

    insightface_pkg = types.ModuleType("insightface")
    insightface_app = types.ModuleType("insightface.app")

    calls = {"count": 0}

    class _FakeFaceAnalysis:
        def __init__(self, name=None, root=None, providers=None, allowed_modules=None, **_kwargs):
            calls["count"] += 1
            if calls["count"] == 1:
                raise FileExistsError(17, "File exists", str(tmp_path / "models" / (name or "antelopev2")))
            self.name = name
            self.root = root
            self.providers = providers
            self.allowed_modules = allowed_modules
            self.prepared = False

        def prepare(self, ctx_id=0, det_size=(640, 640)):
            self.prepared = True

        def get(self, _frame):
            return []

    insightface_app.FaceAnalysis = _FakeFaceAnalysis
    monkeypatch.setitem(sys.modules, "insightface", insightface_pkg)
    monkeypatch.setitem(sys.modules, "insightface.app", insightface_app)

    model_dir = tmp_path / "models" / "antelopev2"
    model_dir.mkdir(parents=True)
    monkeypatch.setenv("INSIGHTFACE_HOME", str(tmp_path))

    module = _load_face_engines_module(monkeypatch, cv2_stub)
    monkeypatch.setattr(module.time, "time", lambda: 1234567890)

    engine = module.create_face_engine("insightface", use_gpu=True)
    assert engine is not None

    assert model_dir.exists() is False
    assert (tmp_path / "models" / "antelopev2.corrupt_1234567890").exists() is True
