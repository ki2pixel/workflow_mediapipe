"""
Integration tests for DeepInfra Audio API endpoint.

All upstream DeepInfra interactions are mocked (no real network).
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from app_new import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as flask_client:
        yield flask_client


@pytest.fixture
def temp_project_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        projects_dir = Path(tmpdir) / "projects"
        projects_dir.mkdir()

        test_project = projects_dir / "test_project"
        test_project.mkdir()

        test_video = test_project / "test_video.mp4"
        test_video.write_bytes(b"fake video")

        yield {
            "projects_dir": projects_dir,
            "project_name": "test_project",
            "video_name": "test_video.mp4",
            "video_path": test_video,
        }


class TestDeepinfraEndpointValidation:
    def test_endpoint_rejects_missing_body(self, client):
        response = client.post("/api/step4/deepinfra_audio")
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "JSON" in data["error"]

    def test_endpoint_rejects_missing_project_name(self, client):
        response = client.post(
            "/api/step4/deepinfra_audio",
            json={"video_name": "test.mp4"},
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "project_name" in data["error"]

    def test_endpoint_rejects_missing_video_name(self, client):
        response = client.post(
            "/api/step4/deepinfra_audio",
            json={"project_name": "test_project"},
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "video_name" in data["error"]

    def test_endpoint_validates_timestamp_granularities_type(self, client):
        response = client.post(
            "/api/step4/deepinfra_audio",
            json={
                "project_name": "test_project",
                "video_name": "test.mp4",
                "timestamp_granularities": "segment",
            },
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "timestamp_granularities" in data["error"]

    def test_endpoint_validates_response_format_type(self, client):
        response = client.post(
            "/api/step4/deepinfra_audio",
            json={
                "project_name": "test_project",
                "video_name": "test.mp4",
                "response_format": ["verbose_json"],
            },
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "response_format" in data["error"]

    def test_endpoint_validates_temperature_type(self, client):
        response = client.post(
            "/api/step4/deepinfra_audio",
            json={
                "project_name": "test_project",
                "video_name": "test.mp4",
                "temperature": "hot",
            },
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "temperature" in data["error"]


class TestDeepinfraEndpointIntegration:
    @patch("services.deepinfra_audio_service.config")
    @patch("services.deepinfra_audio_service.DeepinfraAudioService._call_deepinfra_api")
    @patch("services.deepinfra_audio_service.DeepinfraAudioService._get_video_duration_ffprobe")
    def test_endpoint_success_creates_audio_json(
        self,
        mock_ffprobe,
        mock_deepinfra_call,
        mock_config,
        client,
        temp_project_dir,
    ):
        mock_config.PROJECTS_DIR = temp_project_dir["projects_dir"]
        mock_config.DEEPINFRA_API_KEY = "test_key"
        mock_config.DEEPINFRA_SPEECH_GAP_FILL_SEC = 0.15
        mock_config.DEEPINFRA_SPEECH_MIN_ON_SEC = 0.0

        mock_ffprobe.return_value = 2.0
        mock_deepinfra_call.return_value = type(
            "_DeepinfraResult",
            (),
            {
                "success": True,
                "segments": [{"start": 0.0, "end": 2.0, "text": "bonjour"}],
                "words": None,
                "duration": 2.0,
                "language": "fr",
                "text": "bonjour",
                "error": None,
            },
        )()

        response = client.post(
            "/api/step4/deepinfra_audio",
            json={
                "project_name": temp_project_dir["project_name"],
                "video_name": temp_project_dir["video_name"],
            },
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["status"] == "success"
        assert data["fps"] == 25.0
        assert data["total_frames"] == 50

        output_path = Path(data["output_path"])
        assert output_path.exists()
        assert output_path.name == "test_video_audio.json"

    @patch("services.deepinfra_audio_service.config")
    def test_endpoint_returns_404_for_missing_project(self, mock_config, client, temp_project_dir):
        mock_config.PROJECTS_DIR = temp_project_dir["projects_dir"]

        response = client.post(
            "/api/step4/deepinfra_audio",
            json={
                "project_name": "missing_project",
                "video_name": "test.mp4",
            },
        )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["status"] == "error"

    @patch("services.deepinfra_audio_service.DeepinfraAudioService.process_video_with_deepinfra")
    def test_endpoint_returns_502_for_deepinfra_upstream_error(self, mock_process, client):
        mock_process.return_value = type(
            "_AudioResult",
            (),
            {
                "success": False,
                "output_path": None,
                "fps": 25.0,
                "total_frames": 0,
                "error": "DeepInfra API error: HTTP 503",
            },
        )()

        response = client.post(
            "/api/step4/deepinfra_audio",
            json={"project_name": "p", "video_name": "v.mp4"},
        )

        assert response.status_code == 502
        data = json.loads(response.data)
        assert data["status"] == "error"

    @patch("services.deepinfra_audio_service.DeepinfraAudioService.process_video_with_deepinfra")
    def test_endpoint_returns_500_for_missing_api_key(self, mock_process, client):
        mock_process.return_value = type(
            "_AudioResult",
            (),
            {
                "success": False,
                "output_path": None,
                "fps": 25.0,
                "total_frames": 0,
                "error": "DEEPINFRA_API_KEY not configured",
            },
        )()

        response = client.post(
            "/api/step4/deepinfra_audio",
            json={"project_name": "p", "video_name": "v.mp4"},
        )

        assert response.status_code == 500
        data = json.loads(response.data)
        assert data["status"] == "error"
