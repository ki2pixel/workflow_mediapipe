import importlib.util
import sys
import types
from pathlib import Path

import builtins


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


def test_opencv_haar_engine_detects_faces(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")
    cv2_stub.COLOR_BGR2GRAY = 1

    def cvtColor(frame, _code):
        return frame

    cv2_stub.cvtColor = cvtColor

    class FakeCascade:
        def empty(self):
            return False

        def detectMultiScale(self, _gray, **_kwargs):
            return [(10, 20, 30, 40)]

    cv2_stub.CascadeClassifier = lambda _path: FakeCascade()

    module = _load_face_engines_module(monkeypatch, cv2_stub)

    engine = module.create_face_engine("opencv_haar")
    out = engine.detect(object())

    assert isinstance(out, list)
    assert len(out) == 1
    assert out[0]["bbox"] == (10, 20, 30, 40)
    assert out[0]["centroid"] == (25, 40)
    assert out[0]["source_detector"] == "face_landmarker"
    assert out[0]["label"] == "face"
    assert out[0]["blendshapes"] is None


def test_opencv_haar_engine_respects_opencv_max_faces(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")
    cv2_stub.COLOR_BGR2GRAY = 1

    def cvtColor(frame, _code):
        return frame

    cv2_stub.cvtColor = cvtColor

    class FakeCascade:
        def empty(self):
            return False

        def detectMultiScale(self, _gray, **_kwargs):
            return [(10, 20, 30, 40), (11, 21, 31, 41), (12, 22, 32, 42)]

    cv2_stub.CascadeClassifier = lambda _path: FakeCascade()

    module = _load_face_engines_module(monkeypatch, cv2_stub)
    monkeypatch.setenv("STEP5_OPENCV_MAX_FACES", "2")

    engine = module.create_face_engine("opencv_haar")
    out = engine.detect(object())

    assert isinstance(out, list)
    assert len(out) == 2


def test_opencv_yunet_engine_respects_opencv_max_faces(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")
    cv2_stub.INTER_LINEAR = 1
    cv2_stub.setNumThreads = lambda _n: None
    cv2_stub.resize = lambda frame, _size, interpolation=None: frame

    class FakeCascade:
        def empty(self):
            return False

    cv2_stub.CascadeClassifier = lambda _path: FakeCascade()

    class FakeYuNetDetector:
        def __init__(self):
            self._input_size = None

        def setInputSize(self, size):
            self._input_size = size

        def detect(self, _frame_bgr):
            faces = [
                [10.0, 20.0, 30.0, 40.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.85],
                [50.0, 60.0, 30.0, 40.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.80],
                [90.0, 15.0, 30.0, 40.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.75],
            ]
            return True, faces

    class FaceDetectorYN:
        @staticmethod
        def create(_model_path, _cfg, _input_size, _score_threshold, _nms_threshold, _top_k):
            return FakeYuNetDetector()

    cv2_stub.FaceDetectorYN = FaceDetectorYN

    module = _load_face_engines_module(monkeypatch, cv2_stub)
    dummy_model = Path("/tmp") / "yunet_test_dummy_max_faces.onnx"
    dummy_model.write_bytes(b"dummy")
    monkeypatch.setenv("STEP5_YUNET_MODEL_PATH", str(dummy_model))
    monkeypatch.setenv("STEP5_OPENCV_MAX_FACES", "2")

    engine = module.create_face_engine("opencv_yunet")

    class FakeFrame:
        shape = (100, 200, 3)

    out = engine.detect(FakeFrame())
    assert isinstance(out, list)
    assert len(out) == 2


def test_opencv_yunet_engine_detects_faces(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")
    cv2_stub.INTER_LINEAR = 1
    cv2_stub.setNumThreads = lambda _n: None
    cv2_stub.resize = lambda frame, _size, interpolation=None: frame

    class FakeCascade:
        def empty(self):
            return False

    cv2_stub.CascadeClassifier = lambda _path: FakeCascade()

    class FakeYuNetDetector:
        def __init__(self):
            self._input_size = None

        def setInputSize(self, size):
            self._input_size = size

        def detect(self, _frame_bgr):
            faces = [
                [10.0, 20.0, 30.0, 40.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.85]
            ]
            return True, faces

    class FaceDetectorYN:
        @staticmethod
        def create(_model_path, _cfg, _input_size, _score_threshold, _nms_threshold, _top_k):
            return FakeYuNetDetector()

    cv2_stub.FaceDetectorYN = FaceDetectorYN

    module = _load_face_engines_module(monkeypatch, cv2_stub)
    # Create a dummy model file so the engine init does not fail on path existence.
    dummy_model = Path("/tmp") / "yunet_test_dummy.onnx"
    dummy_model.write_bytes(b"dummy")
    monkeypatch.setenv("STEP5_YUNET_MODEL_PATH", str(dummy_model))

    engine = module.create_face_engine("opencv_yunet")

    class FakeFrame:
        shape = (100, 200, 3)

    out = engine.detect(FakeFrame())

    assert isinstance(out, list)
    assert len(out) == 1
    assert out[0]["bbox"] == (10, 20, 30, 40)
    assert out[0]["centroid"] == (25, 40)
    assert out[0]["confidence"] == 0.85


def test_create_face_engine_rejects_unknown(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")

    class FakeCascade:
        def empty(self):
            return False

    cv2_stub.CascadeClassifier = lambda _path: FakeCascade()

    module = _load_face_engines_module(monkeypatch, cv2_stub)

    try:
        module.create_face_engine("unknown_engine")
        assert False, "Expected ValueError"
    except ValueError:
        assert True


def test_opencv_yunet_pyfeat_engine_requires_dependencies(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")
    cv2_stub.setNumThreads = lambda _n: None

    class FakeCascade:
        def empty(self):
            return False

    cv2_stub.CascadeClassifier = lambda _path: FakeCascade()

    class FakeYuNetDetector:
        def __init__(self):
            self._input_size = None

        def setInputSize(self, size):
            self._input_size = size

        def detect(self, _frame_bgr):
            return True, []

    class FaceDetectorYN:
        @staticmethod
        def create(_model_path, _cfg, _input_size, _score_threshold, _nms_threshold, _top_k):
            return FakeYuNetDetector()

    cv2_stub.FaceDetectorYN = FaceDetectorYN

    module = _load_face_engines_module(monkeypatch, cv2_stub)
    dummy_model = Path("/tmp") / "yunet_test_dummy_pyfeat.onnx"
    dummy_model.write_bytes(b"dummy")
    monkeypatch.setenv("STEP5_YUNET_MODEL_PATH", str(dummy_model))

    try:
        module.create_face_engine("opencv_yunet_pyfeat")
        assert False, "Expected RuntimeError due to missing dependencies"
    except RuntimeError as e:
        assert "py-feat" in str(e) or "pyfeat" in str(e).lower()


def test_eos_engine_requires_eos_py(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")

    class FakeCascade:
        def empty(self):
            return False

    cv2_stub.CascadeClassifier = lambda _path: FakeCascade()

    module = _load_face_engines_module(monkeypatch, cv2_stub)

    original_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "eos":
            raise ModuleNotFoundError("No module named 'eos'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    try:
        module.create_face_engine("eos")
        assert False, "Expected RuntimeError due to missing eos-py"
    except RuntimeError as e:
        assert "eos" in str(e).lower()


def test_openseeface_engine_reports_missing_models(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")
    cv2_stub.INTER_LINEAR = 1
    cv2_stub.setNumThreads = lambda _n: None
    cv2_stub.resize = lambda frame, _size, interpolation=None: frame

    module = _load_face_engines_module(monkeypatch, cv2_stub)

    # Stub onnxruntime so we don't depend on it being installed in the pytest venv.
    monkeypatch.setitem(sys.modules, "onnxruntime", types.ModuleType("onnxruntime"))

    # Ensure we hit the "model not found" error path deterministically.
    monkeypatch.delenv("STEP5_OPENSEEFACE_DETECTION_MODEL_PATH", raising=False)
    monkeypatch.delenv("STEP5_OPENSEEFACE_LANDMARK_MODEL_PATH", raising=False)
    monkeypatch.setenv("STEP5_OPENSEEFACE_MODELS_DIR", "/tmp/does-not-exist-openseeface-models")

    try:
        module.create_face_engine("openseeface")
        assert False, "Expected RuntimeError due to missing OpenSeeFace models"
    except RuntimeError as e:
        assert "OpenSeeFace detection model not found" in str(e)


def test_openseeface_engine_rescales_output_when_downscaled(monkeypatch):
    resize_calls = []

    class FakeResizedFrame:
        def __init__(self, shape):
            self.shape = shape

    def resize(frame, size, interpolation=None):
        resize_calls.append(size)
        width, height = size
        return FakeResizedFrame((height, width, 3))

    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")
    cv2_stub.INTER_LINEAR = 1
    cv2_stub.setNumThreads = lambda _n: None
    cv2_stub.resize = resize

    module = _load_face_engines_module(monkeypatch, cv2_stub)

    class GraphOptimizationLevel:
        ORT_ENABLE_ALL = 99

    class ExecutionMode:
        ORT_SEQUENTIAL = 0

    class SessionOptions:
        def __init__(self):
            self.graph_optimization_level = None
            self.intra_op_num_threads = None
            self.inter_op_num_threads = None
            self.execution_mode = None

    class FakeInput:
        def __init__(self, name):
            self.name = name

    class InferenceSession:
        def __init__(self, _path, sess_options=None, providers=None):
            self._sess_options = sess_options
            self._providers = providers

        def get_inputs(self):
            return [FakeInput("input")]

        def run(self, _output_names, _feeds):
            return [None]

    ort_stub = types.ModuleType("onnxruntime")
    ort_stub.SessionOptions = SessionOptions
    ort_stub.GraphOptimizationLevel = GraphOptimizationLevel
    ort_stub.ExecutionMode = ExecutionMode
    ort_stub.InferenceSession = InferenceSession
    monkeypatch.setitem(sys.modules, "onnxruntime", ort_stub)

    detection_model = Path("/tmp") / "openseeface_test_detection.onnx"
    landmark_model = Path("/tmp") / "openseeface_test_landmark.onnx"
    detection_model.write_bytes(b"dummy")
    landmark_model.write_bytes(b"dummy")

    monkeypatch.setenv("STEP5_OPENSEEFACE_DETECTION_MODEL_PATH", str(detection_model))
    monkeypatch.setenv("STEP5_OPENSEEFACE_LANDMARK_MODEL_PATH", str(landmark_model))
    monkeypatch.setenv("STEP5_OPENSEEFACE_MAX_WIDTH", "640")

    engine = module.create_face_engine("openseeface")

    engine._detect_faces = lambda _frame: [(100.0, 50.0, 100.0, 100.0, 0.9)]
    engine._preprocess_landmarks = lambda _frame, crop: (None, crop)
    engine._landmark_session.run = lambda _out, _feeds: [types.SimpleNamespace(ndim=1)]

    lms_yx_conf = module.np.array(
        [
            [50.0, 100.0, 1.0],
            [150.0, 200.0, 1.0],
        ],
        dtype=module.np.float32,
    )
    engine._decode_landmarks = lambda _tensor, _crop_info: (0.9, lms_yx_conf)

    class FakeFrame:
        shape = (720, 1280, 3)

    out = engine.detect(FakeFrame())
    assert resize_calls == [(640, 360)]

    assert len(out) == 1
    assert out[0]["bbox"] == (200, 100, 200, 200)
    assert out[0]["centroid"] == (300, 200)


def test_openseeface_engine_max_width_falls_back_to_yunet_max_width(monkeypatch):
    resize_calls = []

    class FakeResizedFrame:
        def __init__(self, shape):
            self.shape = shape

    def resize(frame, size, interpolation=None):
        resize_calls.append(size)
        width, height = size
        return FakeResizedFrame((height, width, 3))

    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")
    cv2_stub.INTER_LINEAR = 1
    cv2_stub.setNumThreads = lambda _n: None
    cv2_stub.resize = resize

    module = _load_face_engines_module(monkeypatch, cv2_stub)

    class GraphOptimizationLevel:
        ORT_ENABLE_ALL = 99

    class ExecutionMode:
        ORT_SEQUENTIAL = 0

    class SessionOptions:
        def __init__(self):
            self.graph_optimization_level = None
            self.intra_op_num_threads = None
            self.inter_op_num_threads = None
            self.execution_mode = None

    class FakeInput:
        def __init__(self, name):
            self.name = name

    class InferenceSession:
        def __init__(self, _path, sess_options=None, providers=None):
            self._sess_options = sess_options
            self._providers = providers

        def get_inputs(self):
            return [FakeInput("input")]

        def run(self, _output_names, _feeds):
            return [None]

    ort_stub = types.ModuleType("onnxruntime")
    ort_stub.SessionOptions = SessionOptions
    ort_stub.GraphOptimizationLevel = GraphOptimizationLevel
    ort_stub.ExecutionMode = ExecutionMode
    ort_stub.InferenceSession = InferenceSession
    monkeypatch.setitem(sys.modules, "onnxruntime", ort_stub)

    detection_model = Path("/tmp") / "openseeface_test_detection_fallback.onnx"
    landmark_model = Path("/tmp") / "openseeface_test_landmark_fallback.onnx"
    detection_model.write_bytes(b"dummy")
    landmark_model.write_bytes(b"dummy")

    monkeypatch.setenv("STEP5_OPENSEEFACE_DETECTION_MODEL_PATH", str(detection_model))
    monkeypatch.setenv("STEP5_OPENSEEFACE_LANDMARK_MODEL_PATH", str(landmark_model))
    monkeypatch.delenv("STEP5_OPENSEEFACE_MAX_WIDTH", raising=False)
    monkeypatch.setenv("STEP5_YUNET_MAX_WIDTH", "640")

    engine = module.create_face_engine("openseeface")

    engine._detect_faces = lambda _frame: [(100.0, 50.0, 100.0, 100.0, 0.9)]
    engine._preprocess_landmarks = lambda _frame, crop: (None, crop)
    engine._landmark_session.run = lambda _out, _feeds: [types.SimpleNamespace(ndim=1)]

    lms_yx_conf = module.np.array(
        [
            [50.0, 100.0, 1.0],
            [150.0, 200.0, 1.0],
        ],
        dtype=module.np.float32,
    )
    engine._decode_landmarks = lambda _tensor, _crop_info: (0.9, lms_yx_conf)

    class FakeFrame:
        shape = (720, 1280, 3)

    out = engine.detect(FakeFrame())
    assert resize_calls == [(640, 360)]
    assert len(out) == 1


def test_openseeface_engine_uses_blendshapes_throttle_as_default_detect_every(monkeypatch):
    cv2_stub = types.ModuleType("cv2")
    cv2_stub.data = types.SimpleNamespace(haarcascades="/tmp/")
    cv2_stub.INTER_LINEAR = 1
    cv2_stub.setNumThreads = lambda _n: None
    cv2_stub.resize = lambda frame, _size, interpolation=None: frame

    module = _load_face_engines_module(monkeypatch, cv2_stub)

    class GraphOptimizationLevel:
        ORT_ENABLE_ALL = 99

    class ExecutionMode:
        ORT_SEQUENTIAL = 0

    class SessionOptions:
        def __init__(self):
            self.graph_optimization_level = None
            self.intra_op_num_threads = None
            self.inter_op_num_threads = None
            self.execution_mode = None

    class FakeInput:
        def __init__(self, name):
            self.name = name

    class InferenceSession:
        def __init__(self, _path, sess_options=None, providers=None):
            self._sess_options = sess_options
            self._providers = providers

        def get_inputs(self):
            return [FakeInput("input")]

        def run(self, _output_names, _feeds):
            return [None]

    ort_stub = types.ModuleType("onnxruntime")
    ort_stub.SessionOptions = SessionOptions
    ort_stub.GraphOptimizationLevel = GraphOptimizationLevel
    ort_stub.ExecutionMode = ExecutionMode
    ort_stub.InferenceSession = InferenceSession
    monkeypatch.setitem(sys.modules, "onnxruntime", ort_stub)

    detection_model = Path("/tmp") / "openseeface_test_detection_throttle.onnx"
    landmark_model = Path("/tmp") / "openseeface_test_landmark_throttle.onnx"
    detection_model.write_bytes(b"dummy")
    landmark_model.write_bytes(b"dummy")

    monkeypatch.setenv("STEP5_OPENSEEFACE_DETECTION_MODEL_PATH", str(detection_model))
    monkeypatch.setenv("STEP5_OPENSEEFACE_LANDMARK_MODEL_PATH", str(landmark_model))

    monkeypatch.delenv("STEP5_OPENSEEFACE_DETECT_EVERY_N", raising=False)
    monkeypatch.setenv("STEP5_BLENDSHAPES_THROTTLE_N", "2")

    engine = module.create_face_engine("openseeface")

    detect_calls = {"count": 0}

    def fake_detect_faces(_frame):
        detect_calls["count"] += 1
        return [(0.0, 0.0, 10.0, 10.0, 0.9)]

    engine._detect_faces = fake_detect_faces
    engine._preprocess_landmarks = lambda _frame, crop: (None, crop)
    engine._landmark_session.run = lambda _out, _feeds: [types.SimpleNamespace(ndim=1)]
    engine._decode_landmarks = lambda _tensor, _crop_info: (0.9, module.np.array([[0.0, 0.0, 1.0]], dtype=module.np.float32))

    class FakeFrame:
        shape = (100, 100, 3)

    out1 = engine.detect(FakeFrame())
    out2 = engine.detect(FakeFrame())

    assert out1 == []
    assert len(out2) == 1
    assert detect_calls["count"] == 1
