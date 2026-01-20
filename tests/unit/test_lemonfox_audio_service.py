"""
Unit tests for Lemonfox Audio Service

Tests the conversion logic from Lemonfox API output to STEP4-compatible JSON format.
"""

import importlib.util
import sys
import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock


def _load_lemonfox_module():
    module_name = "lemonfox_audio_service_test_module"
    if module_name in sys.modules:
        return sys.modules[module_name]

    service_path = (
        Path(__file__).resolve().parents[2]
        / "services"
        / "lemonfox_audio_service.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, service_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


lemonfox_module = _load_lemonfox_module()
LemonfoxAudioService = lemonfox_module.LemonfoxAudioService
LemonfoxTranscriptionResult = lemonfox_module.LemonfoxTranscriptionResult
AudioAnalysisResult = lemonfox_module.AudioAnalysisResult
AUDIO_SUFFIX = lemonfox_module.AUDIO_SUFFIX
DEFAULT_FPS = lemonfox_module.DEFAULT_FPS


class TestLemonfoxValidation:
    """Test path validation and security checks."""
    
    def test_validate_project_rejects_absolute_paths(self):
        """Reject absolute video paths."""
        valid, path, error = LemonfoxAudioService._validate_project_and_video(
            "test_project",
            "/etc/passwd"
        )
        assert not valid
        assert "relative path" in error
        
    def test_validate_project_rejects_path_traversal(self):
        """Reject path traversal attempts."""
        valid, path, error = LemonfoxAudioService._validate_project_and_video(
            "../etc",
            "video.mp4"
        )
        assert not valid
        assert "traversal" in error.lower()
    
    def test_validate_project_rejects_windows_style_traversal(self):
        """Reject path traversal attempts even with Windows separators."""
        valid, path, error = LemonfoxAudioService._validate_project_and_video(
            "test_project",
            "..\\secret\\video.mp4"
        )
        assert not valid
        assert "traversal" in error.lower()
        
    def test_validate_project_rejects_slash_in_project_name(self):
        """Reject project names with slashes."""
        valid, path, error = LemonfoxAudioService._validate_project_and_video(
            "test/project",
            "video.mp4"
        )
        assert not valid
        assert "simple folder name" in error


class TestFrameTimelineConversion:
    """Test conversion of Lemonfox segments/words to frame timeline."""
    
    def test_build_timeline_from_segments(self):
        """Build frame timeline from Lemonfox segments."""
        transcription = LemonfoxTranscriptionResult(
            success=True,
            segments=[
                {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_A"},
                {"start": 1.0, "end": 2.0, "speaker": "SPEAKER_B"},
            ],
            words=None,
            duration=2.0
        )
        
        total_frames = 50  # 2 seconds at 25 fps
        fps = 25.0
        
        timeline, speech_frames = LemonfoxAudioService._build_frame_timeline(
            transcription, total_frames, fps
        )
        
        # Check that frames are populated
        assert len(timeline) > 0
        assert len(speech_frames) > 0
        
        # Check speaker normalization
        all_speakers = set()
        for speakers in timeline.values():
            all_speakers.update(speakers)
        
        # Should have normalized labels
        assert "SPEAKER_00" in all_speakers or "SPEAKER_01" in all_speakers
        
    def test_build_timeline_from_words(self):
        """Build frame timeline from word-level timestamps."""
        transcription = LemonfoxTranscriptionResult(
            success=True,
            segments=[],
            words=[
                {"start": 0.0, "end": 0.5, "speaker": "SPEAKER_A", "text": "hello"},
                {"start": 0.5, "end": 1.0, "speaker": "SPEAKER_A", "text": "world"},
            ],
            duration=1.0
        )
        
        total_frames = 25  # 1 second at 25 fps
        fps = 25.0
        
        timeline, speech_frames = LemonfoxAudioService._build_frame_timeline(
            transcription, total_frames, fps
        )
        
        # Words should be preferred over segments
        assert len(timeline) > 0
        assert len(speech_frames) > 0
        
    def test_build_timeline_normalizes_speaker_labels(self):
        """Speaker labels should be normalized to SPEAKER_XX format."""
        transcription = LemonfoxTranscriptionResult(
            success=True,
            segments=[
                {"start": 0.0, "end": 1.0, "speaker": "spk_alice"},
                {"start": 1.0, "end": 2.0, "speaker": "spk_bob"},
            ],
            words=None,
            duration=2.0
        )
        
        timeline, speech_frames = LemonfoxAudioService._build_frame_timeline(
            transcription, 50, 25.0
        )
        
        # Collect all speaker labels
        all_speakers = set()
        for speakers in timeline.values():
            all_speakers.update(speakers)
        
        # All labels should match SPEAKER_XX pattern
        for speaker in all_speakers:
            assert speaker.startswith("SPEAKER_")
            assert speaker[8:].isdigit()
            
    def test_build_timeline_handles_no_speaker(self):
        """Handle segments without speaker labels."""
        transcription = LemonfoxTranscriptionResult(
            success=True,
            segments=[
                {"start": 0.0, "end": 1.0},  # No speaker
            ],
            words=None,
            duration=1.0
        )
        
        timeline, speech_frames = LemonfoxAudioService._build_frame_timeline(
            transcription, 25, 25.0
        )
        
        # Timeline may be empty or have empty sets
        for speakers in timeline.values():
            assert isinstance(speakers, set)

        # But speech_frames must reflect that speech exists in the segment range
        assert len(speech_frames) > 0


class TestLemonfoxSpeechSmoothing:
    def test_apply_speech_smoothing_gap_fill_fills_short_gaps(self):
        timeline = {
            1: {"SPEAKER_00"},
            2: {"SPEAKER_00"},
            5: {"SPEAKER_00"},
            6: {"SPEAKER_00"},
        }
        speech_frames = {1, 2, 5, 6}

        timeline_out, speech_out = LemonfoxAudioService._apply_speech_smoothing(
            timeline=timeline,
            speech_frames=set(speech_frames),
            total_frames=10,
            fps=10.0,
            gap_fill_sec=0.15,
            min_on_sec=0.0,
        )

        assert speech_out == {1, 2, 3, 4, 5, 6}
        assert timeline_out[1] == {"SPEAKER_00"}
        assert 3 not in timeline_out

    def test_apply_speech_smoothing_gap_fill_does_not_fill_long_gaps(self):
        speech_frames = {1, 2, 7, 8}

        _timeline_out, speech_out = LemonfoxAudioService._apply_speech_smoothing(
            timeline={},
            speech_frames=set(speech_frames),
            total_frames=10,
            fps=10.0,
            gap_fill_sec=0.15,
            min_on_sec=0.0,
        )

        assert speech_out == {1, 2, 7, 8}

    def test_apply_speech_smoothing_min_on_removes_short_islands(self):
        timeline = {
            1: {"SPEAKER_00"},
            3: {"SPEAKER_00"},
            4: {"SPEAKER_00"},
        }
        speech_frames = {1, 3, 4}

        timeline_out, speech_out = LemonfoxAudioService._apply_speech_smoothing(
            timeline=dict(timeline),
            speech_frames=set(speech_frames),
            total_frames=10,
            fps=10.0,
            gap_fill_sec=0.0,
            min_on_sec=0.15,
        )

        assert 1 not in speech_out
        assert 1 not in timeline_out
        assert speech_out == {3, 4}

    def test_build_timeline_applies_smoothing_from_config(self, monkeypatch):
        transcription = LemonfoxTranscriptionResult(
            success=True,
            segments=[
                {"start": 0.0, "end": 0.1, "speaker": "A"},
                {"start": 0.3, "end": 0.4, "speaker": "A"},
            ],
            words=None,
            duration=0.4,
        )

        from services import lemonfox_audio_service as module
        monkeypatch.setattr(module.config, "LEMONFOX_SPEECH_GAP_FILL_SEC", 0.15, raising=False)
        monkeypatch.setattr(module.config, "LEMONFOX_SPEECH_MIN_ON_SEC", 0.0, raising=False)

        timeline, speech_frames = LemonfoxAudioService._build_frame_timeline(
            transcription=transcription,
            total_frames=10,
            fps=10.0,
        )

        assert 1 in speech_frames
        assert 2 in speech_frames


class TestLemonfoxUploadPreparation:
    def test_prepare_upload_artifact_within_limit(self, monkeypatch, tmp_path):
        video = tmp_path / "video.mp4"
        video.write_bytes(b"0" * (512 * 1024))

        monkeypatch.setattr(lemonfox_module.config, "LEMONFOX_MAX_UPLOAD_MB", 5, raising=False)
        monkeypatch.setattr(lemonfox_module.config, "LEMONFOX_ENABLE_TRANSCODE", False, raising=False)

        result = LemonfoxAudioService._prepare_upload_artifact(video)
        assert result.upload_path == video
        assert result.transcoded is False
        assert result.original_size_mb > 0

    def test_prepare_upload_artifact_over_limit_without_transcode(self, monkeypatch, tmp_path):
        video = tmp_path / "video.mp4"
        video.write_bytes(b"0" * (2 * 1024 * 1024))

        monkeypatch.setattr(lemonfox_module.config, "LEMONFOX_MAX_UPLOAD_MB", 1, raising=False)
        monkeypatch.setattr(lemonfox_module.config, "LEMONFOX_ENABLE_TRANSCODE", False, raising=False)

        with pytest.raises(ValueError) as exc:
            LemonfoxAudioService._prepare_upload_artifact(video)

        assert "dépasse la limite" in str(exc.value)

    def test_prepare_upload_artifact_over_limit_with_transcode(self, monkeypatch, tmp_path):
        video = tmp_path / "video.mp4"
        video.write_bytes(b"0" * (2 * 1024 * 1024))

        monkeypatch.setattr(lemonfox_module.config, "LEMONFOX_MAX_UPLOAD_MB", 1, raising=False)
        monkeypatch.setattr(lemonfox_module.config, "LEMONFOX_ENABLE_TRANSCODE", True, raising=False)
        monkeypatch.setattr(lemonfox_module.config, "LEMONFOX_TRANSCODE_AUDIO_CODEC", "aac", raising=False)
        monkeypatch.setattr(lemonfox_module.config, "LEMONFOX_TRANSCODE_BITRATE_KBPS", 96, raising=False)

        tmp_transcoded = tmp_path / "transcoded.mp4"
        tmp_transcoded.write_bytes(b"0" * (256 * 1024))

        def _fake_transcode(_video_path: Path):
            return tmp_transcoded, lambda: None

        monkeypatch.setattr(
            LemonfoxAudioService,
            "_transcode_video_for_upload",
            staticmethod(_fake_transcode),
        )

        result = LemonfoxAudioService._prepare_upload_artifact(video)

        assert result.upload_path == tmp_transcoded
        assert result.transcoded is True
        assert result.limit_mb == 1


class TestSTEP4JsonOutput:
    """Test STEP4-compatible JSON output format."""
    
    def test_write_json_creates_valid_structure(self):
        """Written JSON should have correct top-level structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_audio.json"
            
            timeline = {
                1: {"SPEAKER_00"},
                2: {"SPEAKER_00"},
                3: {"SPEAKER_00", "SPEAKER_01"},
            }
            
            success = LemonfoxAudioService._write_step4_json_atomically(
                output_path=output_path,
                video_filename="test.mp4",
                fps=25.0,
                total_frames=5,
                timeline=timeline,
                speech_frames={1, 2, 3}
            )
            
            assert success
            assert output_path.exists()
            
            # Parse and validate structure
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            assert "video_filename" in data
            assert "total_frames" in data
            assert "fps" in data
            assert "frames_analysis" in data
            
            assert data["video_filename"] == "test.mp4"
            assert data["total_frames"] == 5
            assert data["fps"] == 25.0
            assert isinstance(data["frames_analysis"], list)
            
    def test_write_json_frames_analysis_length(self):
        """frames_analysis should have exactly total_frames entries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_audio.json"
            
            total_frames = 100
            timeline = {}  # Empty timeline
            
            LemonfoxAudioService._write_step4_json_atomically(
                output_path=output_path,
                video_filename="test.mp4",
                fps=25.0,
                total_frames=total_frames,
                timeline=timeline,
                speech_frames=set()
            )
            
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            assert len(data["frames_analysis"]) == total_frames
            
    def test_write_json_frame_numbers_are_sequential(self):
        """Frame numbers should be 1-based and sequential without gaps."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_audio.json"
            
            LemonfoxAudioService._write_step4_json_atomically(
                output_path=output_path,
                video_filename="test.mp4",
                fps=25.0,
                total_frames=10,
                timeline={},
                speech_frames=set()
            )
            
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            frames = data["frames_analysis"]
            for i, frame_entry in enumerate(frames, start=1):
                assert frame_entry["frame"] == i
                
    def test_write_json_audio_info_structure(self):
        """Each frame's audio_info should have correct fields and types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_audio.json"
            
            timeline = {
                2: {"SPEAKER_00"},
                3: {"SPEAKER_00", "SPEAKER_01"},
            }
            
            LemonfoxAudioService._write_step4_json_atomically(
                output_path=output_path,
                video_filename="test.mp4",
                fps=25.0,
                total_frames=5,
                timeline=timeline,
                speech_frames={2, 3}
            )
            
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            for frame_entry in data["frames_analysis"]:
                audio_info = frame_entry["audio_info"]
                
                # Required fields
                assert "is_speech_present" in audio_info
                assert "num_distinct_speakers_audio" in audio_info
                assert "active_speaker_labels" in audio_info
                assert "timecode_sec" in audio_info
                
                # Type checks
                assert isinstance(audio_info["is_speech_present"], bool)
                assert isinstance(audio_info["num_distinct_speakers_audio"], int)
                assert isinstance(audio_info["active_speaker_labels"], list)
                assert isinstance(audio_info["timecode_sec"], (int, float))
                
    def test_write_json_speech_detection(self):
        """is_speech_present should be True when speakers are present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_audio.json"
            
            timeline = {
                2: {"SPEAKER_00"},
            }
            
            LemonfoxAudioService._write_step4_json_atomically(
                output_path=output_path,
                video_filename="test.mp4",
                fps=25.0,
                total_frames=5,
                timeline=timeline,
                speech_frames={2}
            )
            
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            # Frame 1: no speech
            assert data["frames_analysis"][0]["audio_info"]["is_speech_present"] is False
            assert data["frames_analysis"][0]["audio_info"]["num_distinct_speakers_audio"] == 0
            assert data["frames_analysis"][0]["audio_info"]["active_speaker_labels"] == []
            
            # Frame 2: speech present
            assert data["frames_analysis"][1]["audio_info"]["is_speech_present"] is True
            assert data["frames_analysis"][1]["audio_info"]["num_distinct_speakers_audio"] == 1
            assert data["frames_analysis"][1]["audio_info"]["active_speaker_labels"] == ["SPEAKER_00"]
            
    def test_write_json_timecode_calculation(self):
        """Timecode should be correctly calculated from frame number."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_audio.json"
            
            fps = 25.0
            LemonfoxAudioService._write_step4_json_atomically(
                output_path=output_path,
                video_filename="test.mp4",
                fps=fps,
                total_frames=5,
                timeline={},
                speech_frames=set()
            )
            
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            # Frame 1 should be at time 0.0 (frame 1 - 1) / fps
            assert data["frames_analysis"][0]["audio_info"]["timecode_sec"] == 0.0
            
            # Frame 2 should be at time 0.04 (1 / 25)
            assert abs(data["frames_analysis"][1]["audio_info"]["timecode_sec"] - 0.04) < 0.001
            
    def test_write_json_atomic_overwrite(self):
        """Writing should atomically overwrite existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_audio.json"
            
            # Write first version
            output_path.write_text('{"old": "data"}')
            assert output_path.exists()
            
            # Write new version
            success = LemonfoxAudioService._write_step4_json_atomically(
                output_path=output_path,
                video_filename="test.mp4",
                fps=25.0,
                total_frames=3,
                timeline={},
                speech_frames=set()
            )
            
            assert success
            
            # Should be overwritten with new content
            with open(output_path, 'r') as f:
                data = json.load(f)
            
            assert "old" not in data
            assert "video_filename" in data
            assert data["video_filename"] == "test.mp4"


class TestLemonfoxAPIIntegration:
    """Test Lemonfox API call logic (with mocking)."""
    
    @patch('services.lemonfox_audio_service.requests.post')
    def test_call_lemonfox_api_success(self, mock_post):
        """Successful API call should return transcription result."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "segments": [
                {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_1", "text": "hello"}
            ],
            "words": [
                {"start": 0.0, "end": 0.5, "speaker": "SPEAKER_1", "text": "hello"}
            ],
            "duration": 1.0
        }
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_video:
            tmp_path = Path(tmp_video.name)
            
            result = LemonfoxAudioService._call_lemonfox_api(
                video_path=tmp_path,
                speaker_labels=True
            )
            
            assert result.success
            assert len(result.segments) == 1
            assert result.words is not None
            assert result.duration == 1.0
            
    @patch('services.lemonfox_audio_service.requests.post')
    def test_call_lemonfox_api_error(self, mock_post):
        """Failed API call should return error result."""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"error": "Invalid file"}
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response
        
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_video:
            tmp_path = Path(tmp_video.name)
            
            result = LemonfoxAudioService._call_lemonfox_api(
                video_path=tmp_path
            )
            
            assert not result.success
            assert result.error is not None
            assert "400" in result.error

    @patch('services.lemonfox_audio_service.requests.post')
    def test_call_lemonfox_api_413_includes_limit(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 413
        mock_response.json.return_value = {"error": "too large"}
        mock_response.text = "too large"
        mock_post.return_value = mock_response

        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_video:
            tmp_path = Path(tmp_video.name)

            result = LemonfoxAudioService._call_lemonfox_api(
                video_path=tmp_path,
                original_file_size_mb=123.45,
                limit_mb=95,
            )

            assert not result.success
            assert "413" in result.error
            assert "95" in result.error
            assert "trop volumineux" in result.error.lower()
            
    @patch('services.lemonfox_audio_service.config')
    def test_call_lemonfox_api_missing_key(self, mock_config):
        """Missing API key should return error."""
        mock_config.LEMONFOX_API_KEY = None
        
        with tempfile.NamedTemporaryFile(suffix=".mp4") as tmp_video:
            tmp_path = Path(tmp_video.name)
            
            result = LemonfoxAudioService._call_lemonfox_api(
                video_path=tmp_path
            )
            
            assert not result.success
            assert "not configured" in result.error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
