import importlib.util
import json
import sys
import types
from pathlib import Path


def _load_step4_script_module():
    module_name = "step4_run_audio_analysis_speaker_embeddings"
    if module_name in sys.modules:
        return sys.modules[module_name]

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
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_step4_audio_json_does_not_include_speaker_embeddings_by_default(tmp_path, monkeypatch):
    # // Given: embeddings flag disabled and a STEP4 run with fake diarization
    step4 = _load_step4_script_module()
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"fake")

    monkeypatch.delenv("AUDIO_INCLUDE_SPEAKER_EMBEDDINGS", raising=False)

    monkeypatch.setattr(step4, "_run_ffprobe_duration", lambda _p: 0.2)

    def _fake_extract(_in: Path, out_wav: Path) -> bool:
        out_wav.write_bytes(b"wav")
        return True

    monkeypatch.setattr(step4, "_extract_audio_ffmpeg", _fake_extract)
    monkeypatch.setattr(
        step4,
        "_run_diarization_and_extract_segments",
        lambda _pipeline, _wav, _dev: [(0.0, 0.08, "SPEAKER_00")],
    )

    def _should_not_be_called(**_kwargs):
        raise AssertionError("_compute_speaker_embeddings_from_wav should not be called")

    monkeypatch.setattr(step4, "_compute_speaker_embeddings_from_wav", _should_not_be_called)

    # // When: analyzing audio
    ok = step4.analyze_audio_file(video_path, diarization_pipeline=object(), hf_token="hf_dummy", device="cpu")

    # // Then: file exists, JSON valid, and speaker_embeddings is absent
    assert ok is True
    out_path = tmp_path / "clip_audio.json"
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "speaker_embeddings" not in data
    assert isinstance(data.get("frames_analysis"), list)


def test_step4_audio_json_includes_speaker_embeddings_when_enabled(tmp_path, monkeypatch):
    # // Given: embeddings flag enabled and embeddings computed
    step4 = _load_step4_script_module()
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"fake")

    monkeypatch.setenv("AUDIO_INCLUDE_SPEAKER_EMBEDDINGS", "1")
    monkeypatch.setattr(step4, "_run_ffprobe_duration", lambda _p: 0.2)

    def _fake_extract(_in: Path, out_wav: Path) -> bool:
        out_wav.write_bytes(b"wav")
        return True

    monkeypatch.setattr(step4, "_extract_audio_ffmpeg", _fake_extract)
    monkeypatch.setattr(
        step4,
        "_run_diarization_and_extract_segments",
        lambda _pipeline, _wav, _dev: [(0.0, 0.08, "SPEAKER_00")],
    )

    embeddings_payload = {
        "model_id": "pyannote/embedding",
        "embedding_dim": 3,
        "normalized": True,
        "vectors_by_label": {"SPEAKER_00": [0.1, 0.2, 0.3]},
        "num_segments_by_label": {"SPEAKER_00": 1},
    }

    def _fake_compute(**_kwargs):
        return embeddings_payload

    monkeypatch.setattr(step4, "_compute_speaker_embeddings_from_wav", _fake_compute)

    # // When: analyzing audio
    ok = step4.analyze_audio_file(video_path, diarization_pipeline=object(), hf_token="hf_dummy", device="cpu")

    # // Then: speaker_embeddings is present and equals the computed payload
    assert ok is True
    out_path = tmp_path / "clip_audio.json"
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert data.get("speaker_embeddings") == embeddings_payload


def test_step4_audio_json_ignores_embedding_errors(tmp_path, monkeypatch):
    # // Given: embeddings enabled but computation raises
    step4 = _load_step4_script_module()
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"fake")

    monkeypatch.setenv("AUDIO_INCLUDE_SPEAKER_EMBEDDINGS", "1")
    monkeypatch.setattr(step4, "_run_ffprobe_duration", lambda _p: 0.2)

    def _fake_extract(_in: Path, out_wav: Path) -> bool:
        out_wav.write_bytes(b"wav")
        return True

    monkeypatch.setattr(step4, "_extract_audio_ffmpeg", _fake_extract)
    monkeypatch.setattr(
        step4,
        "_run_diarization_and_extract_segments",
        lambda _pipeline, _wav, _dev: [(0.0, 0.08, "SPEAKER_00")],
    )

    def _raising_compute(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(step4, "_compute_speaker_embeddings_from_wav", _raising_compute)

    # // When: analyzing audio
    ok = step4.analyze_audio_file(video_path, diarization_pipeline=object(), hf_token="hf_dummy", device="cpu")

    # // Then: JSON is still written without speaker_embeddings
    assert ok is True
    out_path = tmp_path / "clip_audio.json"
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "speaker_embeddings" not in data


def test_step4_audio_json_ignores_empty_embeddings_payload(tmp_path, monkeypatch):
    # // Given: embeddings enabled but computation returns empty payload
    step4 = _load_step4_script_module()
    video_path = tmp_path / "clip.mp4"
    video_path.write_bytes(b"fake")

    monkeypatch.setenv("AUDIO_INCLUDE_SPEAKER_EMBEDDINGS", "1")
    monkeypatch.setattr(step4, "_run_ffprobe_duration", lambda _p: 0.2)

    def _fake_extract(_in: Path, out_wav: Path) -> bool:
        out_wav.write_bytes(b"wav")
        return True

    monkeypatch.setattr(step4, "_extract_audio_ffmpeg", _fake_extract)
    monkeypatch.setattr(
        step4,
        "_run_diarization_and_extract_segments",
        lambda _pipeline, _wav, _dev: [(0.0, 0.08, "SPEAKER_00")],
    )

    def _empty_compute(**_kwargs):
        return {}

    monkeypatch.setattr(step4, "_compute_speaker_embeddings_from_wav", _empty_compute)

    # // When: analyzing audio
    ok = step4.analyze_audio_file(video_path, diarization_pipeline=object(), hf_token="hf_dummy", device="cpu")

    # // Then: JSON is written without speaker_embeddings
    assert ok is True
    out_path = tmp_path / "clip_audio.json"
    data = json.loads(out_path.read_text(encoding="utf-8"))
    assert "speaker_embeddings" not in data
