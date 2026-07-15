from pathlib import Path

import numpy as np

from workflow_scripts.step5 import run_tracking_cv5 as tracking_cv5


class _CapturingOutput:
    def __init__(self):
        self.frames = []

    def add_frame(self, frame):
        self.frames.append(frame)


class _PassThroughFilter:
    def update(self, values):
        return np.asarray(values, dtype=np.float32)


def test_adaptive_worker_count_uses_cpu_budget_for_one_long_video():
    worker_count = tracking_cv5.calculate_adaptive_worker_count(
        [1600],
        cpu_budget=15,
        max_workers_by_memory=15,
        min_frames_per_worker=80,
    )

    assert worker_count == 15


def test_adaptive_worker_count_respects_memory_and_available_work():
    worker_count = tracking_cv5.calculate_adaptive_worker_count(
        [40, 100, None],
        cpu_budget=15,
        max_workers_by_memory=4,
        min_frames_per_worker=80,
    )

    assert worker_count == 4


def test_cv5_cpu_worker_pool_ignores_insightface_gpu_flag(monkeypatch):
    monkeypatch.setenv("STEP5_ENABLE_GPU", "1")

    worker_count = tracking_cv5.calculate_cv5_inference_worker_count(
        [1600],
        cpu_budget=15,
        max_workers_by_memory=15,
        min_frames_per_worker=80,
        inference_device="cpu",
    )

    assert worker_count == 15


def test_cv5_cuda_worker_pool_is_limited_to_one_worker():
    worker_count = tracking_cv5.calculate_cv5_inference_worker_count(
        [1600],
        cpu_budget=15,
        max_workers_by_memory=15,
        min_frames_per_worker=80,
        inference_device="cuda",
    )

    assert worker_count == 1


def test_cv5_inference_device_defaults_to_cpu_for_invalid_values():
    assert tracking_cv5.normalize_cv5_inference_device("unsupported") == "cpu"


def test_cv5_cpu_onnx_runtime_provider_ignores_insightface_gpu_flag(monkeypatch):
    monkeypatch.setenv("STEP5_ENABLE_GPU", "1")

    providers = tracking_cv5.get_cv5_onnx_runtime_providers(
        "cpu",
        ["CUDAExecutionProvider", "CPUExecutionProvider"],
    )

    assert providers == ["CPUExecutionProvider"]


def test_cv5_cuda_onnx_runtime_provider_uses_cuda_when_available():
    providers = tracking_cv5.get_cv5_onnx_runtime_providers(
        "cuda",
        ["CUDAExecutionProvider", "CPUExecutionProvider"],
    )

    assert providers == ["CUDAExecutionProvider", "CPUExecutionProvider"]


def test_ready_chunks_are_reduced_in_frame_order(monkeypatch):
    output = _CapturingOutput()
    state = tracking_cv5.AdaptiveVideoState(
        index=0,
        video_path=Path("video.mp4"),
        width=1280,
        height=720,
        fps=25.0,
        total_frames=4,
        output_path=Path("video.json"),
        temporary_output_path=Path("video.json.partial"),
        stream_out=output,
        speaking_detector=object(),
        temporal_filter=_PassThroughFilter(),
        decoder=None,
    )
    processed_frames = []

    def fake_tracking(**kwargs):
        processed_frames.append(kwargs["current_frame_num"])
        return [{"tracked_frame": kwargs["current_frame_num"]}]

    monkeypatch.setattr(tracking_cv5, "apply_tracking_and_management", fake_tracking)
    state.ready_chunks[2] = [
        {"face": None, "objects": []},
        {"face": None, "objects": []},
    ]
    state.ready_chunks[0] = [
        {"face": None, "objects": []},
        {"face": None, "objects": []},
    ]

    flushed = tracking_cv5._flush_cv5_ready_chunks(state)

    assert flushed == 4
    assert processed_frames == [1, 2, 3, 4]
    assert [frame["frame"] for frame in output.frames] == [1, 2, 3, 4]
    assert state.next_output_frame == 4
