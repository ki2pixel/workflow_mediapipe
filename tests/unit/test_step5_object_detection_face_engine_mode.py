import importlib.util
import sys
import types
from pathlib import Path


def test_mp_object_detector_runs_in_face_engine_mode(monkeypatch, tmp_path):
    calls = []

    class FakeFrame:
        shape = (100, 200, 3)

    class FakeCapture:
        def __init__(self, _video_path: str):
            self._video_path = _video_path
            self._read_count = 0

        def isOpened(self):
            calls.append("isOpened")
            return True

        def read(self):
            calls.append("read")
            self._read_count += 1
            if self._read_count <= 2:
                return True, FakeFrame()
            return False, None

        def set(self, prop_id, value):
            calls.append(("set", prop_id, value))
            return True

        def release(self):
            calls.append("release")
            return None

    cv2_stub = types.ModuleType("cv2")
    cv2_stub.CAP_PROP_POS_FRAMES = 1
    cv2_stub.COLOR_BGR2RGB = 2
    cv2_stub.VideoCapture = lambda video_path: FakeCapture(video_path)
    cv2_stub.cvtColor = lambda frame, _code: frame
    monkeypatch.setitem(sys.modules, "cv2", cv2_stub)

    mediapipe_stub = types.ModuleType("mediapipe")

    class ImageFormat:
        SRGB = "SRGB"

    class Image:
        def __init__(self, image_format, data):
            self.image_format = image_format
            self.data = data

    mediapipe_stub.ImageFormat = ImageFormat
    mediapipe_stub.Image = Image
    monkeypatch.setitem(sys.modules, "mediapipe", mediapipe_stub)

    numpy_stub = types.ModuleType("numpy")
    numpy_stub.mean = lambda _values: 0
    monkeypatch.setitem(sys.modules, "numpy", numpy_stub)

    utils_pkg = types.ModuleType("utils")
    utils_pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "utils", utils_pkg)

    tracking_optimizations_stub = types.ModuleType("utils.tracking_optimizations")
    tracking_optimizations_stub.apply_tracking_and_management = lambda *_args, **_kwargs: []
    monkeypatch.setitem(sys.modules, "utils.tracking_optimizations", tracking_optimizations_stub)

    resource_manager_stub = types.ModuleType("utils.resource_manager")
    resource_manager_stub.safe_video_processing = lambda *_args, **_kwargs: None
    resource_manager_stub.get_video_metadata = lambda *_args, **_kwargs: None
    resource_manager_stub.resource_tracker = object()
    monkeypatch.setitem(sys.modules, "utils.resource_manager", resource_manager_stub)

    enhanced_speaking_detection_stub = types.ModuleType("utils.enhanced_speaking_detection")
    enhanced_speaking_detection_stub.EnhancedSpeakingDetector = object()
    monkeypatch.setitem(
        sys.modules,
        "utils.enhanced_speaking_detection",
        enhanced_speaking_detection_stub,
    )

    face_engines_stub = types.ModuleType("face_engines")
    face_engines_stub.create_face_engine = lambda *_args, **_kwargs: None
    monkeypatch.setitem(sys.modules, "face_engines", face_engines_stub)

    object_detector_registry_stub = types.ModuleType("object_detector_registry")
    object_detector_registry_stub.ObjectDetectorRegistry = object()
    monkeypatch.setitem(sys.modules, "object_detector_registry", object_detector_registry_stub)

    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "workflow_scripts" / "step5" / "process_video_worker_multiprocessing.py"
    spec = importlib.util.spec_from_file_location("step5_object_fallback_face_engine_test", module_path)
    assert spec is not None
    assert spec.loader is not None

    step5_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(step5_module)

    class FakeCategory:
        category_name = "person"
        score = 0.9

    class FakeBoundingBox:
        origin_x = 10
        origin_y = 20
        width = 30
        height = 40

    class FakeDetection:
        bounding_box = FakeBoundingBox()
        categories = [FakeCategory()]

    class FakeObjectResult:
        detections = [FakeDetection()]

    class FakeObjectDetector:
        def detect_for_video(self, _mp_image, _timestamp_ms):
            return FakeObjectResult()

    class FakeFaceEngine:
        def detect(self, _frame):
            return []

    step5_module.tracking_engine_type = "face_engine"
    step5_module.face_engine_global = FakeFaceEngine()
    step5_module.object_detector_global = FakeObjectDetector()

    video_path = tmp_path / "fake.mp4"
    out = step5_module.process_frame_chunk((0, 0, str(video_path), {"enable_object_detection": True, "fps": 25.0}))

    assert isinstance(out, list)
    assert len(out) == 1
    assert out[0]["frame_idx"] == 0
    assert out[0]["face_detected"] is False

    detections = out[0]["detections"]
    assert len(detections) == 1
    assert detections[0]["source_detector"] == "object_detector"
    assert detections[0]["label"] == "person"
    assert detections[0]["bbox"] == (10, 20, 30, 40)
