import importlib.util
import sys
import types
from pathlib import Path


def test_process_frame_chunk_calls_read_before_set(monkeypatch, tmp_path):
    calls = []

    class FakeFrame:
        shape = (1080, 1920, 3)

    class FakeCapture:
        def __init__(self, _video_path: str):
            self._video_path = _video_path

        def isOpened(self):
            calls.append("isOpened")
            return True

        def read(self):
            calls.append("read")
            return True, FakeFrame()

        def set(self, prop_id, value):
            calls.append(("set", prop_id, value))
            return True

        def release(self):
            calls.append("release")

    cv2_stub = types.ModuleType("cv2")
    cv2_stub.CAP_PROP_POS_FRAMES = 1
    cv2_stub.CAP_PROP_POS_MSEC = 2
    cv2_stub.COLOR_BGR2RGB = 3

    def cvt_color(frame, _code):
        calls.append("cvtColor")
        return frame

    cv2_stub.cvtColor = cvt_color

    def video_capture_factory(video_path):
        calls.append(("VideoCapture", video_path))
        return FakeCapture(video_path)

    cv2_stub.VideoCapture = video_capture_factory

    monkeypatch.setitem(sys.modules, "cv2", cv2_stub)

    mediapipe_stub = types.ModuleType("mediapipe")

    class ImageFormat:
        SRGB = "SRGB"

    class Image:
        def __init__(self, image_format, data):
            calls.append(("mp.Image", image_format))
            self.image_format = image_format
            self.data = data

    mediapipe_stub.ImageFormat = ImageFormat
    mediapipe_stub.Image = Image
    monkeypatch.setitem(sys.modules, "mediapipe", mediapipe_stub)

    numpy_stub = types.ModuleType("numpy")

    def mean(_values):
        return 0

    numpy_stub.mean = mean
    monkeypatch.setitem(sys.modules, "numpy", numpy_stub)

    utils_pkg = types.ModuleType("utils")
    utils_pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "utils", utils_pkg)

    tracking_optimizations_stub = types.ModuleType("utils.tracking_optimizations")

    def apply_tracking_and_management(*_args, **_kwargs):
        return []

    tracking_optimizations_stub.apply_tracking_and_management = apply_tracking_and_management
    monkeypatch.setitem(sys.modules, "utils.tracking_optimizations", tracking_optimizations_stub)

    resource_manager_stub = types.ModuleType("utils.resource_manager")

    def safe_video_processing(*_args, **_kwargs):
        raise AssertionError("safe_video_processing must not be called in this unit test")

    def get_video_metadata(*_args, **_kwargs):
        raise AssertionError("get_video_metadata must not be called in this unit test")

    resource_manager_stub.safe_video_processing = safe_video_processing
    resource_manager_stub.get_video_metadata = get_video_metadata
    resource_manager_stub.resource_tracker = object()
    monkeypatch.setitem(sys.modules, "utils.resource_manager", resource_manager_stub)

    enhanced_speaking_detection_stub = types.ModuleType("utils.enhanced_speaking_detection")

    class EnhancedSpeakingDetector:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("EnhancedSpeakingDetector must not be instantiated in this unit test")

    enhanced_speaking_detection_stub.EnhancedSpeakingDetector = EnhancedSpeakingDetector
    monkeypatch.setitem(sys.modules, "utils.enhanced_speaking_detection", enhanced_speaking_detection_stub)

    object_detector_registry_stub = types.ModuleType("object_detector_registry")
    object_detector_registry_stub.ObjectDetectorRegistry = object()
    monkeypatch.setitem(sys.modules, "object_detector_registry", object_detector_registry_stub)

    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "workflow_scripts" / "step5" / "process_video_worker_multiprocessing.py"

    spec = importlib.util.spec_from_file_location("step5_worker_mp_seek_test", module_path)
    assert spec is not None
    assert spec.loader is not None

    step5_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(step5_module)

    class FakeLandmarker:
        def detect_for_video(self, *_args, **_kwargs):
            return types.SimpleNamespace(face_landmarks=[], face_blendshapes=None)

    step5_module.landmarker_global = FakeLandmarker()
    step5_module.tracking_engine_type = "mediapipe"

    video_path = tmp_path / "fake.mp4"
    out = step5_module.process_frame_chunk((10, 10, str(video_path), {"fps": 25}))
    assert isinstance(out, list)
    assert len(out) == 1
    assert out[0]["frame_idx"] == 10

    read_index = calls.index("read")
    set_index = next(
        idx for idx, call in enumerate(calls) if isinstance(call, tuple) and call[0] == "set"
    )
    assert read_index < set_index

    set_calls = [c for c in calls if isinstance(c, tuple) and c[0] == "set"]
    assert ("set", cv2_stub.CAP_PROP_POS_FRAMES, 10) in set_calls

    assert "release" in calls
