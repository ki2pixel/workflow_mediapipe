"""Unit tests for STEP4 Lemonfox wrapper fallback behavior."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

_WRAPPER_PATH = Path(__file__).resolve().parents[2] / "workflow_scripts" / "step4" / "run_audio_analysis_lemonfox.py"
_SPEC = importlib.util.spec_from_file_location("run_audio_analysis_lemonfox", _WRAPPER_PATH)
wrapper = importlib.util.module_from_spec(_SPEC)
assert _SPEC is not None and _SPEC.loader is not None
_SPEC.loader.exec_module(wrapper)


def test_wrapper_falls_back_to_pyannote_when_lemonfox_returns_error(monkeypatch, tmp_path):
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    fake_video = tmp_path / "projets_extraits" / "proj" / "video.mp4"
    fake_video.parent.mkdir(parents=True, exist_ok=True)
    fake_video.write_bytes(b"fake")

    monkeypatch.setattr(wrapper.os, "getcwd", lambda: str(tmp_path / "projets_extraits"))
    monkeypatch.setattr(wrapper, "_configure_file_logger", lambda _p: None)
    monkeypatch.setattr(wrapper, "_find_videos_for_audio_analysis", lambda _wd: [fake_video])
    monkeypatch.setattr(wrapper, "_resolve_project_and_video_name", lambda _wd, _vp: ("proj", "video.mp4"))

    class _FakeService:
        @staticmethod
        def _get_video_duration_ffprobe(_path: Path):
            return 1.0

        @staticmethod
        def process_video_with_lemonfox(**_kwargs):
            return SimpleNamespace(success=False, error="Lemonfox API error")

    monkeypatch.setattr(wrapper, "_import_lemonfox_audio_service", lambda: _FakeService)

    fallback_called = {"called": False}

    def _fake_fallback(_log_dir: Path) -> int:
        fallback_called["called"] = True
        return 0

    monkeypatch.setattr(wrapper, "_run_pyannote_fallback", _fake_fallback)

    monkeypatch.setattr(wrapper.sys, "argv", ["prog", "--log_dir", str(log_dir)])
    exit_code = wrapper.main()

    assert fallback_called["called"] is True
    assert exit_code == 0
