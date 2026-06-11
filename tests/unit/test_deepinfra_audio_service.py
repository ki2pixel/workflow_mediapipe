"""
Unit tests for DeepInfra Audio Service.

All API interactions are mocked: no real network calls.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from services import deepinfra_audio_service as module

DeepinfraAudioService = module.DeepinfraAudioService
DeepinfraTranscriptionResult = module.DeepinfraTranscriptionResult


class TestDeepinfraValidation:
    def test_validate_project_rejects_absolute_video_path(self):
        valid, _path, error = DeepinfraAudioService._validate_project_and_video("project", "/etc/passwd")
        assert not valid
        assert "relative path" in (error or "")

    def test_validate_project_rejects_path_traversal(self):
        valid, _path, error = DeepinfraAudioService._validate_project_and_video("project", "../secret.mp4")
        assert not valid
        assert "traversal" in (error or "").lower()


class TestDeepinfraUrlResolution:
    def test_build_deepinfra_url_uses_config_resolver(self, monkeypatch):
        monkeypatch.setattr(
            module.config,
            "resolve_deepinfra_transcriptions_url",
            lambda: "https://api.deepinfra.com/v1/openai/audio/transcriptions",
            raising=False,
        )
        url = DeepinfraAudioService._build_deepinfra_url()
        assert url == "https://api.deepinfra.com/v1/openai/audio/transcriptions"

    def test_build_deepinfra_url_falls_back_to_direct_url(self, monkeypatch):
        monkeypatch.setattr(module.config, "resolve_deepinfra_transcriptions_url", None, raising=False)
        monkeypatch.setattr(
            module.config,
            "DEEPINFRA_TRANSCRIPTIONS_URL",
            "https://api.deepinfra.com/v1/openai/audio/transcriptions",
            raising=False,
        )
        url = DeepinfraAudioService._build_deepinfra_url()
        assert url == "https://api.deepinfra.com/v1/openai/audio/transcriptions"


class TestDeepinfraApiCall:
    def test_call_deepinfra_api_missing_api_key(self, monkeypatch):
        monkeypatch.setattr(module.config, "DEEPINFRA_API_KEY", None, raising=False)

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_video:
            result = DeepinfraAudioService._call_deepinfra_api(video_path=Path(tmp_video.name))

        assert result.success is False
        assert "not configured" in (result.error or "").lower()

    @patch("services.deepinfra_audio_service.requests.post")
    def test_call_deepinfra_api_success(self, mock_post, monkeypatch):
        monkeypatch.setattr(DeepinfraAudioService, "_extract_audio_to_temp", staticmethod(lambda _path: None), raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_API_KEY", "test-key", raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_MODEL", "openai/whisper-large-v3", raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_RESPONSE_FORMAT", "verbose_json", raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_TIMEOUT_SEC", 30, raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_MAX_RETRIES", 0, raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_BACKOFF_SEC", 0.01, raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_TIMESTAMP_GRANULARITIES", ["segment"], raising=False)

        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "segments": [{"start": 0.0, "end": 1.0, "text": "bonjour"}],
            "duration": 1.0,
            "language": "fr",
            "text": "bonjour",
        }
        mock_post.return_value = response

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_video:
            result = DeepinfraAudioService._call_deepinfra_api(video_path=Path(tmp_video.name))

        assert result.success is True
        assert len(result.segments) == 1
        assert result.duration == 1.0
        assert mock_post.call_count == 1

    @patch("services.deepinfra_audio_service.requests.post")
    def test_call_deepinfra_api_retries_on_429(self, mock_post, monkeypatch):
        monkeypatch.setattr(DeepinfraAudioService, "_extract_audio_to_temp", staticmethod(lambda _path: None), raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_API_KEY", "test-key", raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_TIMEOUT_SEC", 30, raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_MAX_RETRIES", 2, raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_BACKOFF_SEC", 0.01, raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_TIMESTAMP_GRANULARITIES", ["segment"], raising=False)

        response_429 = Mock()
        response_429.status_code = 429
        response_429.json.return_value = {"error": "rate limit"}
        response_429.text = "rate limit"

        response_200 = Mock()
        response_200.status_code = 200
        response_200.json.return_value = {
            "segments": [{"start": 0.0, "end": 0.5}],
            "duration": 0.5,
            "language": "fr",
            "text": "ok",
        }

        mock_post.side_effect = [response_429, response_200]

        with patch("services.deepinfra_audio_service.time.sleep") as mock_sleep:
            with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_video:
                result = DeepinfraAudioService._call_deepinfra_api(video_path=Path(tmp_video.name))

        assert result.success is True
        assert mock_post.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("services.deepinfra_audio_service.requests.post")
    def test_call_deepinfra_api_retries_on_timeout(self, mock_post, monkeypatch):
        monkeypatch.setattr(DeepinfraAudioService, "_extract_audio_to_temp", staticmethod(lambda _path: None), raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_API_KEY", "test-key", raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_TIMEOUT_SEC", 30, raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_MAX_RETRIES", 1, raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_BACKOFF_SEC", 0.01, raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_TIMESTAMP_GRANULARITIES", ["segment"], raising=False)

        response_200 = Mock()
        response_200.status_code = 200
        response_200.json.return_value = {
            "segments": [{"start": 0.0, "end": 0.5}],
            "duration": 0.5,
            "language": "fr",
            "text": "ok",
        }

        mock_post.side_effect = [requests.Timeout(), response_200]

        with patch("services.deepinfra_audio_service.time.sleep") as mock_sleep:
            with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_video:
                result = DeepinfraAudioService._call_deepinfra_api(video_path=Path(tmp_video.name))

        assert result.success is True
        assert mock_post.call_count == 2
        assert mock_sleep.call_count == 1

    @patch("services.deepinfra_audio_service.requests.post")
    def test_call_deepinfra_api_rejects_non_json_success_payload(self, mock_post, monkeypatch):
        monkeypatch.setattr(module.config, "DEEPINFRA_API_KEY", "test-key", raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_MAX_RETRIES", 0, raising=False)

        response = Mock()
        response.status_code = 200
        response.json.side_effect = ValueError("invalid json")
        mock_post.return_value = response

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_video:
            result = DeepinfraAudioService._call_deepinfra_api(video_path=Path(tmp_video.name))

        assert result.success is False
        assert "non-json" in (result.error or "").lower()


class TestDeepinfraTimelineAndOutput:
    def test_build_frame_timeline_applies_smoothing(self, monkeypatch):
        monkeypatch.setattr(module.config, "DEEPINFRA_SPEECH_GAP_FILL_SEC", 0.15, raising=False)
        monkeypatch.setattr(module.config, "DEEPINFRA_SPEECH_MIN_ON_SEC", 0.0, raising=False)

        transcription = DeepinfraTranscriptionResult(
            success=True,
            segments=[
                {"start": 0.0, "end": 0.1},
                {"start": 0.3, "end": 0.4},
            ],
            words=None,
            duration=0.4,
            language="fr",
            text="test",
        )

        _timeline, speech_frames = DeepinfraAudioService._build_frame_timeline(
            transcription=transcription,
            total_frames=10,
            fps=10.0,
        )

        assert 1 in speech_frames
        assert 2 in speech_frames

    def test_process_video_with_deepinfra_success_writes_step4_json(self, monkeypatch, tmp_path):
        projects_dir = tmp_path / "projects"
        project_dir = projects_dir / "proj"
        project_dir.mkdir(parents=True)
        video_path = project_dir / "video.mp4"
        video_path.write_bytes(b"video")

        monkeypatch.setattr(module.config, "PROJECTS_DIR", projects_dir, raising=False)

        monkeypatch.setattr(
            DeepinfraAudioService,
            "_get_video_duration_ffprobe",
            staticmethod(lambda _path: 1.0),
        )
        monkeypatch.setattr(
            DeepinfraAudioService,
            "_call_deepinfra_api",
            staticmethod(
                lambda **_kwargs: DeepinfraTranscriptionResult(
                    success=True,
                    segments=[{"start": 0.0, "end": 1.0}],
                    words=None,
                    duration=1.0,
                    language="fr",
                    text="ok",
                )
            ),
        )

        result = DeepinfraAudioService.process_video_with_deepinfra(
            project_name="proj",
            video_name="video.mp4",
        )

        assert result.success is True
        assert result.output_path is not None
        assert result.output_path.exists()

        with open(result.output_path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)

        assert payload["video_filename"] == "video.mp4"
        assert payload["fps"] == 25.0
        assert payload["total_frames"] == 25
        assert len(payload["frames_analysis"]) == 25
