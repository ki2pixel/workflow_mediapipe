"""Unit tests for the Pyannote loader helpers introduced in STEP4."""

import importlib.util
import sys
import types
from pathlib import Path
import pytest


def _load_step4_module():
    module_name = "step4_run_audio_analysis_test_module"
    if module_name in sys.modules:
        return sys.modules[module_name]

    # Provide a minimal torch stub if torch is not available in the test env.
    if "torch" not in sys.modules:
        class _DummyInferenceMode:
            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc, tb):
                return False

        fake_torch = types.SimpleNamespace(
            cuda=types.SimpleNamespace(
                is_available=lambda: False,
                amp=types.SimpleNamespace(autocast=lambda **_kwargs: _DummyInferenceMode()),
            ),
            inference_mode=lambda: _DummyInferenceMode(),
            device=lambda *_args, **_kwargs: None,
            set_num_threads=lambda *_args, **_kwargs: None,
        )
        sys.modules["torch"] = fake_torch

    module_path = (
        Path(__file__).resolve().parents[2]
        / "workflow_scripts"
        / "step4"
        / "run_audio_analysis.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


step4_script = _load_step4_module()


def test_load_pyannote_pipeline_prefers_token(monkeypatch):
    recorded_calls = []

    class _DummyPipeline:
        @staticmethod
        def from_pretrained(model_id, *, token=None, use_auth_token=None):
            recorded_calls.append(
                {
                    "model_id": model_id,
                    "token": token,
                    "use_auth_token": use_auth_token,
                }
            )
            return f"pipeline:{model_id}"

    result = step4_script._load_pyannote_pipeline(
        model_id="pyannote/speaker-diarization-3.1",
        hf_token="hf_dummy",
        pipeline_cls=_DummyPipeline,
    )

    assert result == "pipeline:pyannote/speaker-diarization-3.1"
    assert recorded_calls == [
        {
            "model_id": "pyannote/speaker-diarization-3.1",
            "token": "hf_dummy",
            "use_auth_token": None,
        }
    ]


def test_load_pyannote_pipeline_falls_back_to_use_auth_token(monkeypatch):
    recorded_calls = []

    class _FallbackPipeline:
        call_count = 0

        @staticmethod
        def from_pretrained(model_id, *, token=None, use_auth_token=None):
            _FallbackPipeline.call_count += 1
            recorded_calls.append(
                {
                    "model_id": model_id,
                    "token": token,
                    "use_auth_token": use_auth_token,
                    "call": _FallbackPipeline.call_count,
                }
            )
            if _FallbackPipeline.call_count == 1:
                raise TypeError("unexpected keyword argument 'token'")
            return "pipeline-fallback"

    result = step4_script._load_pyannote_pipeline(
        model_id="pyannote/speaker-diarization-3.1",
        hf_token="hf_dummy",
        pipeline_cls=_FallbackPipeline,
    )

    assert result == "pipeline-fallback"
    assert recorded_calls == [
        {
            "model_id": "pyannote/speaker-diarization-3.1",
            "token": "hf_dummy",
            "use_auth_token": None,
            "call": 1,
        },
        {
            "model_id": "pyannote/speaker-diarization-3.1",
            "token": None,
            "use_auth_token": "hf_dummy",
            "call": 2,
        },
    ]


def test_load_pyannote_pipeline_propagates_non_token_type_error():
    class _RaisingPipeline:
        @staticmethod
        def from_pretrained(model_id, *, token=None, use_auth_token=None):
            raise TypeError("boom")

    with pytest.raises(TypeError, match="boom"):
        step4_script._load_pyannote_pipeline(
            model_id="pyannote/speaker-diarization-3.1",
            hf_token="hf_dummy",
            pipeline_cls=_RaisingPipeline,
        )
