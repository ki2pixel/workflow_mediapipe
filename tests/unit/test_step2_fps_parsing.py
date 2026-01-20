import importlib.util
from pathlib import Path
from types import SimpleNamespace


def _load_convert_videos_module():
    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "workflow_scripts" / "step2" / "convert_videos.py"
    spec = importlib.util.spec_from_file_location("step2_convert_videos", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_ffprobe_fps_prefers_counts_over_nominal_rates():
    module = _load_convert_videos_module()
    payload = {
        "streams": [
            {
                "avg_frame_rate": "25/1",
                "r_frame_rate": "25/1",
                "nb_frames": "2318",
                "duration": "182.20",
            }
        ]
    }
    fps = module._parse_ffprobe_fps(payload)
    assert fps is not None
    assert 12.6 < fps < 12.8


def test_parse_ffprobe_fps_falls_back_to_avg_rate():
    module = _load_convert_videos_module()
    payload = {"streams": [{"avg_frame_rate": "25/1", "r_frame_rate": "50/1"}]}
    fps = module._parse_ffprobe_fps(payload)
    assert fps == 25.0


def test_get_video_framerate_uses_ffprobe_json(monkeypatch, tmp_path):
    module = _load_convert_videos_module()

    fake_payload = {
        "streams": [
            {
                "avg_frame_rate": "0/0",
                "r_frame_rate": "25/1",
                "nb_frames": "2318",
                "duration": "182.20",
            }
        ]
    }

    def fake_run(*_args, **_kwargs):
        return SimpleNamespace(stdout=__import__("json").dumps(fake_payload))

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    video_path = tmp_path / "video.mp4"
    video_path.write_bytes(b"")

    fps = module.get_video_framerate(video_path)
    assert fps is not None
    assert 12.6 < fps < 12.8
