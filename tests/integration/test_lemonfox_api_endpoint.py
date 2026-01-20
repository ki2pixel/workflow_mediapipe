"""
Integration tests for Lemonfox Audio API endpoint

Tests the full API endpoint including request validation, service integration,
and file overwrite behavior.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock

from app_new import create_app
from services.lemonfox_audio_service import LemonfoxTranscriptionResult


@pytest.fixture
def client():
    """Create Flask test client."""
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def temp_project_dir():
    """Create temporary project directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        projects_dir = Path(tmpdir) / "projects"
        projects_dir.mkdir()
        
        # Create test project
        test_project = projects_dir / "test_project"
        test_project.mkdir()
        
        # Create test video file
        test_video = test_project / "test_video.mp4"
        test_video.write_bytes(b"fake video data")
        
        yield {
            "projects_dir": projects_dir,
            "project_name": "test_project",
            "video_name": "test_video.mp4",
            "video_path": test_video
        }


class TestLemonfoxEndpointValidation:
    """Test API endpoint input validation."""
    
    def test_endpoint_rejects_missing_body(self, client):
        """Reject requests without JSON body."""
        response = client.post('/api/step4/lemonfox_audio')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "JSON" in data["error"]
        
    def test_endpoint_rejects_missing_project_name(self, client):
        """Reject requests without project_name."""
        response = client.post(
            '/api/step4/lemonfox_audio',
            json={"video_name": "test.mp4"}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "project_name" in data["error"]
        
    def test_endpoint_rejects_missing_video_name(self, client):
        """Reject requests without video_name."""
        response = client.post(
            '/api/step4/lemonfox_audio',
            json={"project_name": "test_project"}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "video_name" in data["error"]
        
    def test_endpoint_validates_min_speakers_type(self, client):
        """Reject invalid min_speakers type."""
        response = client.post(
            '/api/step4/lemonfox_audio',
            json={
                "project_name": "test_project",
                "video_name": "test.mp4",
                "min_speakers": "two"  # Should be int
            }
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "min_speakers" in data["error"]
        
    def test_endpoint_validates_max_speakers_type(self, client):
        """Reject invalid max_speakers type."""
        response = client.post(
            '/api/step4/lemonfox_audio',
            json={
                "project_name": "test_project",
                "video_name": "test.mp4",
                "max_speakers": "five"  # Should be int
            }
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "max_speakers" in data["error"]
        
    def test_endpoint_validates_timestamp_granularities_type(self, client):
        """Reject invalid timestamp_granularities type."""
        response = client.post(
            '/api/step4/lemonfox_audio',
            json={
                "project_name": "test_project",
                "video_name": "test.mp4",
                "timestamp_granularities": "word"  # Should be array
            }
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "timestamp_granularities" in data["error"]


class TestLemonfoxEndpointIntegration:
    """Test full endpoint integration with mocked Lemonfox API."""
    
    @patch('services.lemonfox_audio_service.config')
    @patch('services.lemonfox_audio_service.LemonfoxAudioService._call_lemonfox_api')
    @patch('services.lemonfox_audio_service.LemonfoxAudioService._get_video_duration_ffprobe')
    def test_endpoint_success_creates_audio_json(
        self, mock_ffprobe, mock_lemonfox_call, mock_config, client, temp_project_dir
    ):
        """Successful request should create _audio.json file."""
        # Configure mocks
        mock_config.PROJECTS_DIR = temp_project_dir["projects_dir"]
        mock_config.LEMONFOX_API_KEY = "test_key"
        mock_config.LEMONFOX_TIMEOUT_SEC = 300
        mock_config.LEMONFOX_EU_DEFAULT = False
        
        mock_ffprobe.return_value = 2.0  # 2 seconds
        
        mock_lemonfox_call.return_value = LemonfoxTranscriptionResult(
            success=True,
            segments=[
                {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_A", "text": "hello"},
                {"start": 1.0, "end": 2.0, "speaker": "SPEAKER_B", "text": "world"},
            ],
            words=None,
            duration=2.0
        )
        
        # Make request
        response = client.post(
            '/api/step4/lemonfox_audio',
            json={
                "project_name": temp_project_dir["project_name"],
                "video_name": temp_project_dir["video_name"]
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data["status"] == "success"
        assert "output_path" in data
        assert data["fps"] == 25.0
        assert data["total_frames"] == 50  # 2 seconds * 25 fps
        
        # Verify file was created
        output_path = Path(data["output_path"])
        assert output_path.exists()
        assert output_path.name == "test_video_audio.json"
        
        # Verify file content
        with open(output_path, 'r') as f:
            audio_data = json.load(f)
        
        assert audio_data["video_filename"] == "test_video.mp4"
        assert audio_data["total_frames"] == 50
        assert audio_data["fps"] == 25.0
        assert len(audio_data["frames_analysis"]) == 50
        
    @patch('services.lemonfox_audio_service.config')
    @patch('services.lemonfox_audio_service.LemonfoxAudioService._call_lemonfox_api')
    @patch('services.lemonfox_audio_service.LemonfoxAudioService._get_video_duration_ffprobe')
    def test_endpoint_overwrites_existing_file(
        self, mock_ffprobe, mock_lemonfox_call, mock_config, client, temp_project_dir
    ):
        """Endpoint should overwrite existing _audio.json file."""
        # Configure mocks
        mock_config.PROJECTS_DIR = temp_project_dir["projects_dir"]
        mock_config.LEMONFOX_API_KEY = "test_key"
        mock_config.LEMONFOX_TIMEOUT_SEC = 300
        mock_config.LEMONFOX_EU_DEFAULT = False
        
        mock_ffprobe.return_value = 1.0
        
        mock_lemonfox_call.return_value = LemonfoxTranscriptionResult(
            success=True,
            segments=[{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_A"}],
            words=None,
            duration=1.0
        )
        
        # Create existing audio file with old content
        video_path = temp_project_dir["video_path"]
        existing_audio = video_path.with_name(f"{video_path.stem}_audio.json")
        existing_audio.write_text('{"old": "content"}')
        assert existing_audio.exists()
        
        # Make request
        response = client.post(
            '/api/step4/lemonfox_audio',
            json={
                "project_name": temp_project_dir["project_name"],
                "video_name": temp_project_dir["video_name"]
            }
        )
        
        assert response.status_code == 200
        
        # Verify file was overwritten
        with open(existing_audio, 'r') as f:
            audio_data = json.load(f)
        
        # Should have new structure, not old content
        assert "old" not in audio_data
        assert "video_filename" in audio_data
        assert "frames_analysis" in audio_data
        
    @patch('services.lemonfox_audio_service.config')
    def test_endpoint_returns_404_for_missing_project(self, mock_config, client, temp_project_dir):
        """Return 404 if project doesn't exist."""
        mock_config.PROJECTS_DIR = temp_project_dir["projects_dir"]
        
        response = client.post(
            '/api/step4/lemonfox_audio',
            json={
                "project_name": "nonexistent_project",
                "video_name": "test.mp4"
            }
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "not found" in data["error"].lower()
        
    @patch('services.lemonfox_audio_service.config')
    def test_endpoint_returns_404_for_missing_video(self, mock_config, client, temp_project_dir):
        """Return 404 if video doesn't exist."""
        mock_config.PROJECTS_DIR = temp_project_dir["projects_dir"]
        
        response = client.post(
            '/api/step4/lemonfox_audio',
            json={
                "project_name": temp_project_dir["project_name"],
                "video_name": "nonexistent.mp4"
            }
        )
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "not found" in data["error"].lower()
        
    @patch('services.lemonfox_audio_service.config')
    @patch('services.lemonfox_audio_service.LemonfoxAudioService._call_lemonfox_api')
    @patch('services.lemonfox_audio_service.LemonfoxAudioService._get_video_duration_ffprobe')
    def test_endpoint_returns_502_for_lemonfox_error(
        self, mock_ffprobe, mock_lemonfox_call, mock_config, client, temp_project_dir
    ):
        """Return 502 if Lemonfox API fails."""
        mock_config.PROJECTS_DIR = temp_project_dir["projects_dir"]
        mock_config.LEMONFOX_API_KEY = "test_key"
        
        mock_ffprobe.return_value = 1.0
        
        # Mock Lemonfox API error
        mock_lemonfox_call.return_value = LemonfoxTranscriptionResult(
            success=False,
            segments=[],
            words=None,
            duration=None,
            error="Lemonfox API error: HTTP 500"
        )
        
        response = client.post(
            '/api/step4/lemonfox_audio',
            json={
                "project_name": temp_project_dir["project_name"],
                "video_name": temp_project_dir["video_name"]
            }
        )
        
        assert response.status_code == 502
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "lemonfox" in data["error"].lower()
        
    @patch('services.lemonfox_audio_service.config')
    def test_endpoint_returns_500_for_missing_api_key(self, mock_config, client, temp_project_dir):
        """Return 400 if API key not configured."""
        mock_config.PROJECTS_DIR = temp_project_dir["projects_dir"]
        mock_config.LEMONFOX_API_KEY = None  # Not configured
        
        response = client.post(
            '/api/step4/lemonfox_audio',
            json={
                "project_name": temp_project_dir["project_name"],
                "video_name": temp_project_dir["video_name"]
            }
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"


class TestLemonfoxEndpointSecurity:
    """Test security aspects of the endpoint."""
    
    @patch('services.lemonfox_audio_service.config')
    def test_endpoint_rejects_absolute_video_path(self, mock_config, client, temp_project_dir):
        """Reject absolute paths in video_name."""
        mock_config.PROJECTS_DIR = temp_project_dir["projects_dir"]
        
        response = client.post(
            '/api/step4/lemonfox_audio',
            json={
                "project_name": temp_project_dir["project_name"],
                "video_name": "/etc/passwd"
            }
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "relative" in data["error"].lower()
        
    @patch('services.lemonfox_audio_service.config')
    def test_endpoint_rejects_path_traversal(self, mock_config, client, temp_project_dir):
        """Reject path traversal attempts."""
        mock_config.PROJECTS_DIR = temp_project_dir["projects_dir"]
        
        response = client.post(
            '/api/step4/lemonfox_audio',
            json={
                "project_name": temp_project_dir["project_name"],
                "video_name": "../../../etc/passwd"
            }
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["status"] == "error"
        assert "traversal" in data["error"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
