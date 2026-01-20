"""
Lemonfox Audio Service
Provides integration with Lemonfox Speech-to-Text API for STEP4 (Audio Analysis).

This service:
- Calls Lemonfox API with video files
- Converts Lemonfox transcription output to STEP4-compatible JSON format
- Writes {video_stem}_audio.json files with frame-by-frame audio analysis
- Ensures compatibility with STEP5 (enhanced_speaking_detection.py) and STEP6 (json_reducer.py)

Architecture:
- Service layer only (business logic)
- Consumed by API routes (thin controllers)
- All secrets via config.settings
- Security: anti path traversal, input validation
"""

import os
import json
import logging
import math
import subprocess
import tempfile
import requests
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from config.settings import config

logger = logging.getLogger(__name__)

# Constants matching STEP4 current implementation
AUDIO_SUFFIX = "_audio.json"
DEFAULT_FPS = 25.0


@dataclass
class LemonfoxTranscriptionResult:
    """Result from Lemonfox API transcription."""
    success: bool
    segments: List[Dict[str, Any]]
    words: Optional[List[Dict[str, Any]]]
    duration: Optional[float]
    error: Optional[str] = None


@dataclass
class AudioAnalysisResult:
    """Result of audio analysis processing."""
    success: bool
    output_path: Optional[Path]
    fps: float
    total_frames: int
    error: Optional[str] = None


@dataclass
class UploadPreparationResult:
    """Upload artifact used for Lemonfox API requests."""
    upload_path: Path
    cleanup: Optional[Callable[[], None]]
    original_size_mb: float
    limit_mb: Optional[float]
    transcoded: bool = False


class LemonfoxAudioService:
    """Service for Lemonfox-based audio analysis."""

    @staticmethod
    def _apply_speech_smoothing(
        timeline: Dict[int, set],
        speech_frames: set[int],
        total_frames: int,
        fps: float,
        gap_fill_sec: float,
        min_on_sec: float,
    ) -> Tuple[Dict[int, set], set[int]]:
        if total_frames <= 0 or fps <= 0:
            return timeline, speech_frames

        if not speech_frames:
            return timeline, speech_frames

        try:
            gap_fill_sec = float(gap_fill_sec or 0.0)
        except Exception:
            gap_fill_sec = 0.0
        try:
            min_on_sec = float(min_on_sec or 0.0)
        except Exception:
            min_on_sec = 0.0

        gap_fill_frames = 0
        if gap_fill_sec > 0:
            gap_fill_frames = int(math.ceil(gap_fill_sec * fps))

        min_on_frames = 0
        if min_on_sec > 0:
            min_on_frames = int(math.ceil(min_on_sec * fps))

        def _build_runs(frames_sorted: List[int]) -> List[Tuple[int, int]]:
            runs: List[Tuple[int, int]] = []
            run_start = frames_sorted[0]
            run_end = frames_sorted[0]
            for frame in frames_sorted[1:]:
                if frame == run_end + 1:
                    run_end = frame
                else:
                    runs.append((run_start, run_end))
                    run_start = frame
                    run_end = frame
            runs.append((run_start, run_end))
            return runs

        frames_sorted = sorted(speech_frames)

        if gap_fill_frames > 0:
            runs = _build_runs(frames_sorted)
            for (prev_start, prev_end), (next_start, next_end) in zip(runs, runs[1:]):
                gap_start = prev_end + 1
                gap_end = next_start - 1
                if gap_end < gap_start:
                    continue
                gap_len = gap_end - gap_start + 1
                if gap_len <= gap_fill_frames:
                    for f in range(gap_start, gap_end + 1):
                        speech_frames.add(f)

            frames_sorted = sorted(speech_frames)

        if min_on_frames > 0 and speech_frames:
            runs = _build_runs(frames_sorted)
            for run_start, run_end in runs:
                run_len = run_end - run_start + 1
                if run_len >= min_on_frames:
                    continue
                for f in range(run_start, run_end + 1):
                    speech_frames.discard(f)
                    timeline.pop(f, None)

        return timeline, speech_frames

    @staticmethod
    def _validate_project_and_video(project_name: str, video_name: str) -> Tuple[bool, Optional[Path], Optional[str]]:
        """
        Validate and resolve project + video paths securely.
        
        Args:
            project_name: Name of the project (must be a valid folder name)
            video_name: Relative path to video within project
            
        Returns:
            Tuple of (success, video_path, error_message)
        """
        # Security: Reject absolute paths
        if os.path.isabs(video_name):
            return False, None, "video_name must be a relative path"
        
        # Security: Reject path traversal attempts (sanitize separators)
        sanitized_video_name = (video_name or "").replace("\\", "/").strip()
        if ".." in project_name:
            return False, None, "Path traversal not allowed"
        video_rel_path = Path(sanitized_video_name)
        if any(part == ".." for part in video_rel_path.parts):
            return False, None, "Path traversal not allowed"
        
        # Normalize project name (should be a simple folder name)
        if "/" in project_name or "\\" in project_name:
            return False, None, "project_name must be a simple folder name"
        
        # Construct and validate project path
        projects_dir = config.PROJECTS_DIR
        project_path = projects_dir / project_name
        
        if not project_path.exists():
            return False, None, f"Project not found: {project_name}"
        
        # Resolve video path
        video_path = project_path / video_name
        
        # Security: Ensure final path is within project directory
        try:
            video_path_resolved = video_path.resolve()
            project_path_resolved = project_path.resolve()
            
            if not str(video_path_resolved).startswith(str(project_path_resolved)):
                return False, None, "Invalid video path (outside project directory)"
        except Exception as e:
            logger.error(f"Path resolution error: {e}")
            return False, None, "Invalid path"
        
        if not video_path.exists():
            return False, None, f"Video not found: {video_name}"
        
        if not video_path.is_file():
            return False, None, f"Video path is not a file: {video_name}"
        
        return True, video_path, None

    @staticmethod
    def _get_video_duration_ffprobe(video_path: Path) -> Optional[float]:
        """
        Get video duration in seconds using ffprobe.
        
        Args:
            video_path: Path to video file
            
        Returns:
            Duration in seconds or None if failed
        """
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=nw=1:nk=1", str(video_path)
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
                timeout=30
            )
            return float(result.stdout.strip())
        except Exception as e:
            logger.warning(f"ffprobe failed for {video_path.name}: {e}")
            return None

    @staticmethod
    def _call_lemonfox_api(
        video_path: Path,
        *,
        upload_filename: Optional[str] = None,
        original_file_size_mb: Optional[float] = None,
        limit_mb: Optional[float] = None,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        speaker_labels: bool = True,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
        timestamp_granularities: Optional[List[str]] = None,
        eu_processing: Optional[bool] = None
    ) -> LemonfoxTranscriptionResult:
        """
        Call Lemonfox API to transcribe audio.
        
        Args:
            video_path: Path to the (possibly transcodé) file to upload
            upload_filename: Filename to expose to the API (defaults to video_path.name)
            original_file_size_mb: Size of the original video (for logging/errors)
            limit_mb: Configured upload limit (for logging/errors)
            language: Optional language hint
            prompt: Optional prompt to guide transcription
            speaker_labels: Enable speaker diarization (default: True)
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers
            timestamp_granularities: List of granularities (e.g., ["word"])
            eu_processing: Force EU processing (overrides default from config)
            
        Returns:
            LemonfoxTranscriptionResult
        """
        api_key = config.LEMONFOX_API_KEY
        if not api_key:
            return LemonfoxTranscriptionResult(
                success=False,
                segments=[],
                words=None,
                duration=None,
                error="LEMONFOX_API_KEY not configured"
            )
        
        # Determine endpoint (EU or standard)
        use_eu = eu_processing if eu_processing is not None else config.LEMONFOX_EU_DEFAULT
        base_url = "https://eu-api.lemonfox.ai" if use_eu else "https://api.lemonfox.ai"
        endpoint = f"{base_url}/v1/audio/transcriptions"
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {api_key}"
        }

        # Build form data as list of tuples to support repeated keys like timestamp_granularities[]
        data: List[Tuple[str, str]] = [
            ("response_format", "verbose_json"),
        ]

        if language:
            data.append(("language", language))
        if prompt:
            data.append(("prompt", prompt))
        if speaker_labels:
            data.append(("speaker_labels", "true"))
        if min_speakers is not None:
            data.append(("min_speakers", str(min_speakers)))
        if max_speakers is not None:
            data.append(("max_speakers", str(max_speakers)))
        if timestamp_granularities:
            for gran in timestamp_granularities:
                data.append(("timestamp_granularities[]", str(gran)))
        
        filename_for_api = upload_filename or video_path.name

        try:
            with open(video_path, 'rb') as video_file:
                files = {
                    "file": (filename_for_api, video_file, "video/mp4")
                }
                
                logger.info(f"Calling Lemonfox API for {video_path.name}...")
                response = requests.post(
                    endpoint,
                    headers=headers,
                    data=data,
                    files=files,
                    timeout=config.LEMONFOX_TIMEOUT_SEC
                )
                
                if response.status_code != 200:
                    if response.status_code == 413:
                        size_clause = ""
                        if original_file_size_mb is not None:
                            size_clause = f" (taille locale ≈ {original_file_size_mb:.2f} MB)"
                        limit_clause = ""
                        if limit_mb is not None:
                            limit_clause = f" (limite configurée: {limit_mb} MB)"
                        error_msg = (
                            "Lemonfox API error: HTTP 413 - fichier trop volumineux"
                            f"{size_clause}{limit_clause}. "
                            "Activez LEMONFOX_ENABLE_TRANSCODE ou réduisez la vidéo."
                        )
                    else:
                        error_msg = f"Lemonfox API error: HTTP {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail}"
                    except Exception:
                        error_msg += f" - {response.text[:200]}"
                    
                    logger.error(error_msg)
                    return LemonfoxTranscriptionResult(
                        success=False,
                        segments=[],
                        words=None,
                        duration=None,
                        error=error_msg
                    )
                
                result = response.json()
                
                # Extract segments and words
                segments = result.get("segments", [])
                words = result.get("words", None)
                duration = result.get("duration", None)
                
                logger.info(f"Lemonfox API success: {len(segments)} segments, duration={duration}s")
                
                return LemonfoxTranscriptionResult(
                    success=True,
                    segments=segments,
                    words=words,
                    duration=duration,
                    error=None
                )
                
        except requests.Timeout:
            error_msg = f"Lemonfox API timeout after {config.LEMONFOX_TIMEOUT_SEC}s"
            logger.error(error_msg)
            return LemonfoxTranscriptionResult(
                success=False,
                segments=[],
                words=None,
                duration=None,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Lemonfox API call failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return LemonfoxTranscriptionResult(
                success=False,
                segments=[],
                words=None,
                duration=None,
                error=error_msg
            )

    @staticmethod
    def _build_frame_timeline(
        transcription: LemonfoxTranscriptionResult,
        total_frames: int,
        fps: float
    ) -> Tuple[Dict[int, set], set]:
        """
        Build frame-by-frame timeline from Lemonfox segments/words.
        
        Args:
            transcription: Lemonfox transcription result
            total_frames: Total number of frames in video
            fps: Frames per second
            
        Returns:
            Tuple of:
            - timeline: Dictionary mapping frame_num -> set of speaker labels
            - speech_frames: Set of frame numbers where speech is present even if no speaker label is available
        """
        timeline: Dict[int, set] = {}  # frame_num -> set(speaker_labels)
        speech_frames: set[int] = set()
        
        # Use words if available (more granular), otherwise use segments
        source = transcription.words if transcription.words else transcription.segments
        
        if not source:
            logger.warning("No segments or words in transcription, returning empty timeline")
            return timeline, speech_frames
        
        # Build speaker label mapping (normalize to SPEAKER_XX format)
        speaker_map = {}
        speaker_counter = 0

        for item in source:
            raw_speaker = item.get("speaker")
            if raw_speaker and raw_speaker not in speaker_map:
                speaker_map[raw_speaker] = f"SPEAKER_{speaker_counter:02d}"
                speaker_counter += 1

        logger.info(f"Speaker mapping: {speaker_map}")

        # Build timeline
        for item in source:
            start = item.get("start")
            end = item.get("end")
            raw_speaker = item.get("speaker")

            if start is None or end is None:
                continue

            # Convert times to frame numbers (1-based)
            start_frame = max(1, int(start * fps))
            end_frame = min(total_frames, int(end * fps))
            if end_frame < start_frame:
                continue

            # Get normalized speaker label
            speaker_label = speaker_map.get(raw_speaker) if raw_speaker else None

            # Track speech presence for each frame in range
            for frame_num in range(start_frame, end_frame + 1):
                speech_frames.add(frame_num)
                if frame_num not in timeline:
                    timeline[frame_num] = set()
                if speaker_label:
                    timeline[frame_num].add(speaker_label)
        
        logger.info(f"Built timeline with {len(speech_frames)} frames containing speech")
        gap_fill_sec = float(getattr(config, "LEMONFOX_SPEECH_GAP_FILL_SEC", 0.0) or 0.0)
        min_on_sec = float(getattr(config, "LEMONFOX_SPEECH_MIN_ON_SEC", 0.0) or 0.0)
        timeline, speech_frames = LemonfoxAudioService._apply_speech_smoothing(
            timeline=timeline,
            speech_frames=speech_frames,
            total_frames=total_frames,
            fps=fps,
            gap_fill_sec=gap_fill_sec,
            min_on_sec=min_on_sec,
        )
        return timeline, speech_frames

    @staticmethod
    def _calculate_file_size_mb(path: Path) -> float:
        size_bytes = path.stat().st_size
        return size_bytes / (1024 * 1024)

    @staticmethod
    def _transcode_video_for_upload(video_path: Path) -> Tuple[Path, Callable[[], None]]:
        """
        Create an audio-only MP4 optimized for Lemonfox uploads.

        Returns:
            Tuple[path_to_upload, cleanup_callback]
        """
        tmp_file = tempfile.NamedTemporaryFile(prefix="lemonfox_audio_upload_", suffix=".mp4", delete=False)
        tmp_path = Path(tmp_file.name)
        tmp_file.close()

        audio_codec = getattr(config, "LEMONFOX_TRANSCODE_AUDIO_CODEC", "aac")
        bitrate_kbps = int(getattr(config, "LEMONFOX_TRANSCODE_BITRATE_KBPS", 96))

        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(video_path),
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-c:a", audio_codec,
            "-b:a", f"{bitrate_kbps}k",
            "-movflags", "+faststart",
            str(tmp_path),
        ]

        logger.info(
            "Transcodage Lemonfox audio-only pour %s via codec=%s bitrate=%skbps",
            video_path.name,
            audio_codec,
            bitrate_kbps,
        )

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(f"Transcodage Lemonfox échoué pour {video_path.name}: {exc}") from exc

        def _cleanup() -> None:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

        return tmp_path, _cleanup

    @staticmethod
    def _prepare_upload_artifact(video_path: Path) -> UploadPreparationResult:
        """
        Ensure the file to upload respects Lemonfox size policy.

        Returns:
            UploadPreparationResult describing the artifact to upload.

        Raises:
            ValueError if the file exceeds the limit and transcode is disabled.
            RuntimeError if transcode fails.
        """
        original_size_mb = LemonfoxAudioService._calculate_file_size_mb(video_path)
        limit_mb = getattr(config, "LEMONFOX_MAX_UPLOAD_MB", None)

        if not limit_mb or original_size_mb <= float(limit_mb):
            return UploadPreparationResult(
                upload_path=video_path,
                cleanup=None,
                original_size_mb=original_size_mb,
                limit_mb=limit_mb,
                transcoded=False,
            )

        if not getattr(config, "LEMONFOX_ENABLE_TRANSCODE", False):
            raise ValueError(
                f"La vidéo ({original_size_mb:.2f} MB) dépasse la limite Lemonfox "
                f"configurée ({limit_mb} MB) et LEMONFOX_ENABLE_TRANSCODE=0."
            )

        tmp_path, cleanup = LemonfoxAudioService._transcode_video_for_upload(video_path)
        transcoded_size_mb = LemonfoxAudioService._calculate_file_size_mb(tmp_path)
        if limit_mb and transcoded_size_mb > float(limit_mb):
            cleanup()
            raise ValueError(
                f"Le fichier transcodé ({transcoded_size_mb:.2f} MB) dépasse toujours "
                f"la limite Lemonfox ({limit_mb} MB)."
            )

        logger.info(
            "Lemonfox upload: %s compressé de %.2f MB à %.2f MB (limite=%s MB)",
            video_path.name,
            original_size_mb,
            transcoded_size_mb,
            limit_mb,
        )

        return UploadPreparationResult(
            upload_path=tmp_path,
            cleanup=cleanup,
            original_size_mb=original_size_mb,
            limit_mb=limit_mb,
            transcoded=True,
        )

    @staticmethod
    def _write_step4_json_atomically(
        output_path: Path,
        video_filename: str,
        fps: float,
        total_frames: int,
        timeline: Dict[int, set],
        speech_frames: set
    ) -> bool:
        """
        Write STEP4-compatible JSON atomically.
        
        Args:
            output_path: Target output path
            video_filename: Video filename for metadata
            fps: Frames per second
            total_frames: Total number of frames
            timeline: Frame timeline (frame_num -> set of speakers)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Write to temporary file first (atomic write pattern)
            tmp_path = output_path.with_suffix('.tmp')
            
            with open(tmp_path, 'w', encoding='utf-8') as f:
                # Write JSON header
                f.write('{\n')
                f.write(f'  "video_filename": "{video_filename}",\n')
                f.write(f'  "total_frames": {total_frames},\n')
                f.write(f'  "fps": {round(fps, 2)},\n')
                f.write('  "frames_analysis": [\n')
                
                # Write frame-by-frame analysis
                for frame_num in range(1, total_frames + 1):
                    speakers = sorted(timeline.get(frame_num, set()))
                    is_speech = (frame_num in speech_frames) or (len(speakers) > 0)
                    timecode_sec = round((frame_num - 1) / fps, 3)
                    
                    frame_obj = {
                        "frame": frame_num,
                        "audio_info": {
                            "is_speech_present": is_speech,
                            "num_distinct_speakers_audio": len(speakers),
                            "active_speaker_labels": speakers,
                            "timecode_sec": timecode_sec
                        }
                    }
                    
                    if frame_num > 1:
                        f.write(',\n')
                    f.write('    ' + json.dumps(frame_obj))
                
                f.write('\n  ]\n')
                f.write('}\n')
            
            # Atomic replace (overwrites existing file)
            os.replace(tmp_path, output_path)
            logger.info(f"Successfully wrote {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write JSON: {e}", exc_info=True)
            # Clean up temp file if it exists
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass
            return False

    @staticmethod
    def process_video_with_lemonfox(
        project_name: str,
        video_name: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        speaker_labels: Optional[bool] = None,
        min_speakers: Optional[int] = None,
        max_speakers: Optional[int] = None,
        timestamp_granularities: Optional[List[str]] = None,
        eu_processing: Optional[bool] = None
    ) -> AudioAnalysisResult:
        """
        Process a video with Lemonfox API and generate STEP4-compatible JSON.
        
        This is the main service method called by API routes.
        
        Args:
            project_name: Name of the project
            video_name: Relative path to video within project
            language: Optional language hint
            prompt: Optional prompt to guide transcription
            speaker_labels: Enable speaker diarization
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers
            timestamp_granularities: List of granularities (e.g., ["word"])
            eu_processing: Force EU processing
            
        Returns:
            AudioAnalysisResult with success status and output details
        """
        # Step 1: Validate and resolve paths
        valid, video_path, error = LemonfoxAudioService._validate_project_and_video(
            project_name, video_name
        )
        if not valid:
            return AudioAnalysisResult(
                success=False,
                output_path=None,
                fps=DEFAULT_FPS,
                total_frames=0,
                error=error
            )
        
        # Step 2: Get video duration and calculate frames
        duration_sec = LemonfoxAudioService._get_video_duration_ffprobe(video_path)
        if duration_sec is None or duration_sec <= 0:
            return AudioAnalysisResult(
                success=False,
                output_path=None,
                fps=DEFAULT_FPS,
                total_frames=0,
                error="Could not determine video duration"
            )
        
        fps = DEFAULT_FPS
        total_frames = int(round(duration_sec * fps))
        
        logger.info(f"Video: {video_path.name}, duration={duration_sec:.2f}s, fps={fps}, frames={total_frames}")
        
        # Step 3: Prepare file for upload (size policy + optional transcode)
        try:
            upload_prep = LemonfoxAudioService._prepare_upload_artifact(video_path)
        except ValueError as size_error:
            return AudioAnalysisResult(
                success=False,
                output_path=None,
                fps=fps,
                total_frames=total_frames,
                error=str(size_error),
            )

        # Step 4: Call Lemonfox API
        effective_language = language
        if effective_language is None:
            effective_language = getattr(config, "LEMONFOX_DEFAULT_LANGUAGE", None)

        effective_prompt = prompt
        if effective_prompt is None:
            effective_prompt = getattr(config, "LEMONFOX_DEFAULT_PROMPT", None)

        if speaker_labels is None:
            effective_speaker_labels = bool(getattr(config, "LEMONFOX_SPEAKER_LABELS_DEFAULT", True))
        else:
            effective_speaker_labels = bool(speaker_labels)

        effective_min_speakers = min_speakers
        if effective_min_speakers is None:
            effective_min_speakers = getattr(config, "LEMONFOX_DEFAULT_MIN_SPEAKERS", None)

        effective_max_speakers = max_speakers
        if effective_max_speakers is None:
            effective_max_speakers = getattr(config, "LEMONFOX_DEFAULT_MAX_SPEAKERS", None)

        effective_timestamp_granularities = timestamp_granularities
        if effective_timestamp_granularities is None:
            effective_timestamp_granularities = list(getattr(config, "LEMONFOX_TIMESTAMP_GRANULARITIES", []) or [])
        if not effective_timestamp_granularities:
            effective_timestamp_granularities = None

        try:
            transcription = LemonfoxAudioService._call_lemonfox_api(
                video_path=upload_prep.upload_path,
                upload_filename=video_path.name,
                original_file_size_mb=upload_prep.original_size_mb,
                limit_mb=upload_prep.limit_mb,
                language=effective_language,
                prompt=effective_prompt,
                speaker_labels=effective_speaker_labels,
                min_speakers=effective_min_speakers,
                max_speakers=effective_max_speakers,
                timestamp_granularities=effective_timestamp_granularities,
                eu_processing=eu_processing
            )
        finally:
            if upload_prep.cleanup:
                upload_prep.cleanup()
        
        if not transcription.success:
            return AudioAnalysisResult(
                success=False,
                output_path=None,
                fps=fps,
                total_frames=total_frames,
                error=transcription.error
            )
        
        # Step 4: Build frame timeline
        timeline, speech_frames = LemonfoxAudioService._build_frame_timeline(
            transcription, total_frames, fps
        )
        
        # Step 5: Write output JSON atomically
        output_path = video_path.with_name(f"{video_path.stem}{AUDIO_SUFFIX}")
        success = LemonfoxAudioService._write_step4_json_atomically(
            output_path=output_path,
            video_filename=video_path.name,
            fps=fps,
            total_frames=total_frames,
            timeline=timeline,
            speech_frames=speech_frames
        )
        
        if not success:
            return AudioAnalysisResult(
                success=False,
                output_path=None,
                fps=fps,
                total_frames=total_frames,
                error="Failed to write output JSON"
            )
        
        return AudioAnalysisResult(
            success=True,
            output_path=output_path,
            fps=fps,
            total_frames=total_frames,
            error=None
        )
