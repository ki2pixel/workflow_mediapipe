"""
DeepInfra Audio Service
Provides integration with DeepInfra OpenAI-compatible Speech-to-Text API for STEP4.

This service:
- Calls DeepInfra API with media files
- Converts transcription output to STEP4-compatible JSON format
- Writes {video_stem}_audio.json files with frame-by-frame audio analysis
- Preserves compatibility with STEP5/STEP6 consumers
"""

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests

from config.settings import config

logger = logging.getLogger(__name__)

AUDIO_SUFFIX = "_audio.json"
DEFAULT_FPS = 25.0


@dataclass
class DeepinfraTranscriptionResult:
    success: bool
    segments: List[Dict[str, Any]]
    words: Optional[List[Dict[str, Any]]]
    duration: Optional[float]
    language: Optional[str]
    text: Optional[str]
    error: Optional[str] = None


@dataclass
class AudioAnalysisResult:
    success: bool
    output_path: Optional[Path]
    fps: float
    total_frames: int
    error: Optional[str] = None


class DeepinfraAudioService:
    """Service for DeepInfra-based audio analysis."""

    @staticmethod
    def _apply_speech_smoothing(
        speech_frames: Set[int],
        total_frames: int,
        fps: float,
        gap_fill_sec: float,
        min_on_sec: float,
    ) -> Set[int]:
        if total_frames <= 0 or fps <= 0 or not speech_frames:
            return speech_frames

        try:
            gap_fill_frames = int(round(max(0.0, float(gap_fill_sec)) * fps))
        except Exception:
            gap_fill_frames = 0
        try:
            min_on_frames = int(round(max(0.0, float(min_on_sec)) * fps))
        except Exception:
            min_on_frames = 0

        frames_sorted = sorted(speech_frames)

        def _build_runs(sorted_frames: List[int]) -> List[Tuple[int, int]]:
            runs: List[Tuple[int, int]] = []
            start = sorted_frames[0]
            end = sorted_frames[0]
            for frame in sorted_frames[1:]:
                if frame == end + 1:
                    end = frame
                else:
                    runs.append((start, end))
                    start = frame
                    end = frame
            runs.append((start, end))
            return runs

        if gap_fill_frames > 0:
            runs = _build_runs(frames_sorted)
            for (_, prev_end), (next_start, _) in zip(runs, runs[1:]):
                gap_start = prev_end + 1
                gap_end = next_start - 1
                if gap_end >= gap_start and (gap_end - gap_start + 1) <= gap_fill_frames:
                    for frame in range(gap_start, gap_end + 1):
                        speech_frames.add(frame)
            frames_sorted = sorted(speech_frames)

        if min_on_frames > 0 and speech_frames:
            runs = _build_runs(frames_sorted)
            for run_start, run_end in runs:
                if (run_end - run_start + 1) < min_on_frames:
                    for frame in range(run_start, run_end + 1):
                        speech_frames.discard(frame)

        return speech_frames

    @staticmethod
    def _validate_project_and_video(project_name: str, video_name: str) -> Tuple[bool, Optional[Path], Optional[str]]:
        if os.path.isabs(video_name):
            return False, None, "video_name must be a relative path"

        sanitized_video_name = (video_name or "").replace("\\", "/").strip()
        if ".." in project_name:
            return False, None, "Path traversal not allowed"

        video_rel_path = Path(sanitized_video_name)
        if any(part == ".." for part in video_rel_path.parts):
            return False, None, "Path traversal not allowed"

        if "/" in project_name or "\\" in project_name:
            return False, None, "project_name must be a simple folder name"

        project_path = config.PROJECTS_DIR / project_name
        if not project_path.exists():
            return False, None, f"Project not found: {project_name}"

        video_path = project_path / video_name
        try:
            video_path_resolved = video_path.resolve()
            project_path_resolved = project_path.resolve()
            if not str(video_path_resolved).startswith(str(project_path_resolved)):
                return False, None, "Invalid video path (outside project directory)"
        except Exception:
            return False, None, "Invalid path"

        if not video_path.exists():
            return False, None, f"Video not found: {video_name}"
        if not video_path.is_file():
            return False, None, f"Video path is not a file: {video_name}"

        return True, video_path, None

    @staticmethod
    def _get_video_duration_ffprobe(video_path: Path) -> Optional[float]:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=nw=1:nk=1",
                    str(video_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True,
                timeout=30,
            )
            return float(result.stdout.strip())
        except Exception as e:
            logger.warning("ffprobe failed for %s: %s", video_path.name, e)
            return None

    @staticmethod
    def _build_deepinfra_url() -> str:
        resolver = getattr(config, "resolve_deepinfra_transcriptions_url", None)
        if callable(resolver):
            return resolver()
        return getattr(config, "DEEPINFRA_TRANSCRIPTIONS_URL", "") or "https://api.deepinfra.com/v1/openai/audio/transcriptions"

    @staticmethod
    def _is_retriable_status(status_code: int) -> bool:
        return status_code in {429, 500, 502, 503, 504}

    @staticmethod
    def _call_deepinfra_api(
        video_path: Path,
        *,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        timestamp_granularities: Optional[List[str]] = None,
        response_format: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> DeepinfraTranscriptionResult:
        api_key = config.DEEPINFRA_API_KEY
        if not api_key:
            return DeepinfraTranscriptionResult(
                success=False,
                segments=[],
                words=None,
                duration=None,
                language=None,
                text=None,
                error="DEEPINFRA_API_KEY not configured",
            )

        endpoint = DeepinfraAudioService._build_deepinfra_url()
        headers = {"Authorization": f"Bearer {api_key}"}

        model = getattr(config, "DEEPINFRA_MODEL", "openai/whisper-large-v3")
        fmt = (response_format or getattr(config, "DEEPINFRA_RESPONSE_FORMAT", "verbose_json") or "verbose_json").strip()
        effective_temperature = temperature if temperature is not None else getattr(config, "DEEPINFRA_TEMPERATURE", None)

        data: List[Tuple[str, str]] = [("model", model), ("response_format", fmt)]
        if language:
            data.append(("language", language))
        if prompt:
            data.append(("prompt", prompt))
        if effective_temperature is not None:
            data.append(("temperature", str(effective_temperature)))

        granularities = timestamp_granularities
        if granularities is None:
            granularities = list(getattr(config, "DEEPINFRA_TIMESTAMP_GRANULARITIES", []) or [])
        if granularities and fmt == "verbose_json":
            for granularity in granularities:
                data.append(("timestamp_granularities[]", str(granularity)))

        timeout_sec = max(1, int(getattr(config, "DEEPINFRA_TIMEOUT_SEC", 300) or 300))
        max_retries = max(0, int(getattr(config, "DEEPINFRA_MAX_RETRIES", 2) or 0))
        backoff = float(getattr(config, "DEEPINFRA_BACKOFF_SEC", 1.5) or 1.5)

        for attempt in range(max_retries + 1):
            try:
                with open(video_path, "rb") as media_file:
                    files = {"file": (video_path.name, media_file, "application/octet-stream")}
                    response = requests.post(
                        endpoint,
                        headers=headers,
                        data=data,
                        files=files,
                        timeout=timeout_sec,
                    )

                if response.status_code == 200:
                    try:
                        payload = response.json()
                    except Exception:
                        return DeepinfraTranscriptionResult(
                            success=False,
                            segments=[],
                            words=None,
                            duration=None,
                            language=None,
                            text=None,
                            error="DeepInfra API returned non-JSON payload",
                        )

                    return DeepinfraTranscriptionResult(
                        success=True,
                        segments=payload.get("segments") or [],
                        words=payload.get("words"),
                        duration=payload.get("duration"),
                        language=payload.get("language"),
                        text=payload.get("text"),
                        error=None,
                    )

                error_message = f"DeepInfra API error: HTTP {response.status_code}"
                try:
                    error_message += f" - {response.json()}"
                except Exception:
                    error_message += f" - {response.text[:200]}"

                retriable = DeepinfraAudioService._is_retriable_status(response.status_code)
                if retriable and attempt < max_retries:
                    sleep_sec = backoff * (2 ** attempt)
                    logger.warning("DeepInfra retryable error (attempt %s/%s): %s", attempt + 1, max_retries + 1, error_message)
                    time.sleep(sleep_sec)
                    continue

                return DeepinfraTranscriptionResult(
                    success=False,
                    segments=[],
                    words=None,
                    duration=None,
                    language=None,
                    text=None,
                    error=error_message,
                )

            except requests.Timeout:
                if attempt < max_retries:
                    sleep_sec = backoff * (2 ** attempt)
                    logger.warning("DeepInfra timeout, retry in %.2fs (attempt %s/%s)", sleep_sec, attempt + 1, max_retries + 1)
                    time.sleep(sleep_sec)
                    continue
                return DeepinfraTranscriptionResult(
                    success=False,
                    segments=[],
                    words=None,
                    duration=None,
                    language=None,
                    text=None,
                    error=f"DeepInfra API timeout after {timeout_sec}s",
                )
            except requests.RequestException as e:
                if attempt < max_retries:
                    sleep_sec = backoff * (2 ** attempt)
                    logger.warning("DeepInfra request error, retry in %.2fs (attempt %s/%s): %s", sleep_sec, attempt + 1, max_retries + 1, e)
                    time.sleep(sleep_sec)
                    continue
                return DeepinfraTranscriptionResult(
                    success=False,
                    segments=[],
                    words=None,
                    duration=None,
                    language=None,
                    text=None,
                    error=f"DeepInfra API call failed: {e}",
                )

        return DeepinfraTranscriptionResult(
            success=False,
            segments=[],
            words=None,
            duration=None,
            language=None,
            text=None,
            error="DeepInfra API unknown failure",
        )

    @staticmethod
    def _build_frame_timeline(
        transcription: DeepinfraTranscriptionResult,
        total_frames: int,
        fps: float,
    ) -> Tuple[Dict[int, Set[str]], Set[int]]:
        timeline: Dict[int, Set[str]] = {}
        speech_frames: Set[int] = set()

        source = transcription.words if transcription.words else transcription.segments
        if not source:
            return timeline, speech_frames

        for item in source:
            start = item.get("start")
            end = item.get("end")
            if start is None or end is None:
                continue

            start_frame = max(1, int(float(start) * fps))
            end_frame = min(total_frames, int(float(end) * fps))
            if end_frame < start_frame:
                continue

            for frame_num in range(start_frame, end_frame + 1):
                speech_frames.add(frame_num)

        speech_frames = DeepinfraAudioService._apply_speech_smoothing(
            speech_frames=speech_frames,
            total_frames=total_frames,
            fps=fps,
            gap_fill_sec=float(getattr(config, "DEEPINFRA_SPEECH_GAP_FILL_SEC", 0.15) or 0.15),
            min_on_sec=float(getattr(config, "DEEPINFRA_SPEECH_MIN_ON_SEC", 0.0) or 0.0),
        )
        return timeline, speech_frames

    @staticmethod
    def _write_step4_json_atomically(
        output_path: Path,
        video_filename: str,
        fps: float,
        total_frames: int,
        timeline: Dict[int, Set[str]],
        speech_frames: Set[int],
    ) -> bool:
        tmp_path = output_path.with_suffix(".tmp")
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write("{\n")
                f.write(f'  "video_filename": "{video_filename}",\n')
                f.write(f'  "total_frames": {total_frames},\n')
                f.write(f'  "fps": {round(fps, 2)},\n')
                f.write('  "frames_analysis": [\n')

                for frame_num in range(1, total_frames + 1):
                    speakers = sorted(timeline.get(frame_num, set()))
                    is_speech = (frame_num in speech_frames) or (len(speakers) > 0)
                    frame_obj = {
                        "frame": frame_num,
                        "audio_info": {
                            "is_speech_present": is_speech,
                            "num_distinct_speakers_audio": len(speakers),
                            "active_speaker_labels": speakers,
                            "timecode_sec": round((frame_num - 1) / fps, 3),
                        },
                    }
                    if frame_num > 1:
                        f.write(",\n")
                    f.write("    " + json.dumps(frame_obj))

                f.write("\n  ]\n")
                f.write("}\n")

            os.replace(tmp_path, output_path)
            return True
        except Exception as e:
            logger.error("Failed to write DeepInfra STEP4 JSON: %s", e, exc_info=True)
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
            return False

    @staticmethod
    def process_video_with_deepinfra(
        project_name: str,
        video_name: str,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
        timestamp_granularities: Optional[List[str]] = None,
        response_format: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> AudioAnalysisResult:
        valid, video_path, error = DeepinfraAudioService._validate_project_and_video(project_name, video_name)
        if not valid or video_path is None:
            return AudioAnalysisResult(
                success=False,
                output_path=None,
                fps=DEFAULT_FPS,
                total_frames=0,
                error=error,
            )

        duration_sec = DeepinfraAudioService._get_video_duration_ffprobe(video_path)
        if duration_sec is None or duration_sec <= 0:
            return AudioAnalysisResult(
                success=False,
                output_path=None,
                fps=DEFAULT_FPS,
                total_frames=0,
                error="Could not determine video duration",
            )

        fps = DEFAULT_FPS
        total_frames = int(round(duration_sec * fps))

        effective_language = language if language is not None else getattr(config, "DEEPINFRA_DEFAULT_LANGUAGE", None)
        effective_prompt = prompt if prompt is not None else getattr(config, "DEEPINFRA_DEFAULT_PROMPT", None)

        transcription = DeepinfraAudioService._call_deepinfra_api(
            video_path=video_path,
            language=effective_language,
            prompt=effective_prompt,
            timestamp_granularities=timestamp_granularities,
            response_format=response_format,
            temperature=temperature,
        )
        if not transcription.success:
            return AudioAnalysisResult(
                success=False,
                output_path=None,
                fps=fps,
                total_frames=total_frames,
                error=transcription.error,
            )

        timeline, speech_frames = DeepinfraAudioService._build_frame_timeline(transcription, total_frames, fps)

        output_path = video_path.with_name(f"{video_path.stem}{AUDIO_SUFFIX}")
        if not DeepinfraAudioService._write_step4_json_atomically(
            output_path=output_path,
            video_filename=video_path.name,
            fps=fps,
            total_frames=total_frames,
            timeline=timeline,
            speech_frames=speech_frames,
        ):
            return AudioAnalysisResult(
                success=False,
                output_path=None,
                fps=fps,
                total_frames=total_frames,
                error="Failed to write output JSON",
            )

        return AudioAnalysisResult(
            success=True,
            output_path=output_path,
            fps=fps,
            total_frames=total_frames,
            error=None,
        )
