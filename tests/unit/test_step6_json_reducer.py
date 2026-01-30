import importlib.util
import json
from pathlib import Path

import pytest


def _load_json_reducer_module(repo_root: Path):
    module_path = repo_root / "workflow_scripts" / "step6" / "json_reducer.py"
    spec = importlib.util.spec_from_file_location("step6_json_reducer_test", module_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_reduce_video_json_raw_schema_extracts_fields_and_metadata():
    # Given: a raw STEP5-like JSON with frames and tracked_objects
    repo_root = Path(__file__).resolve().parents[2]
    mod = _load_json_reducer_module(repo_root)

    raw = {
        "fps": 25.0,
        "total_frames": 2,
        "frames": [
            {
                "frame": 1,
                "tracked_objects": [
                    {
                        "id": "face_1",
                        "centroid_x": 123.4,
                        "source": "face_landmarker",
                        "label": "face",
                        "confidence": 0.87,
                        "bbox_width": 50,
                        "bbox_height": 60,
                        "active_speakers": ["should_be_overridden"],
                        "speaking_sources": {"audio": {"active_speakers": ["spkA"]}},
                    }
                ],
            }
        ],
    }

    # When: reducing the tracking JSON
    reduced = mod.reduce_video_json(raw)

    # Then: frames_analysis contains only AE-required fields + fps/total_frames
    assert reduced is not None
    assert reduced.get("fps") == 25.0
    assert reduced.get("total_frames") == 2

    frames = reduced.get("frames_analysis")
    assert isinstance(frames, list) and len(frames) == 1
    assert frames[0].get("frame") == 1

    tracked = frames[0].get("tracked_objects")
    assert isinstance(tracked, list) and len(tracked) == 1
    obj = tracked[0]
    assert obj.get("id") == "face_1"
    assert obj.get("centroid_x") == 123.4
    assert obj.get("source") == "face_landmarker"
    assert obj.get("label") == "face"
    assert obj.get("confidence") == 0.87
    assert obj.get("bbox_width") == 50
    assert obj.get("bbox_height") == 60
    assert obj.get("active_speakers") == ["spkA"]


def test_reduce_video_json_unexpected_schema_returns_none():
    # Given: an unexpected JSON schema (no frames nor frames_analysis)
    repo_root = Path(__file__).resolve().parents[2]
    mod = _load_json_reducer_module(repo_root)

    raw = {"hello": "world"}

    # When: reducing the tracking JSON
    reduced = mod.reduce_video_json(raw)

    # Then: reducer returns None to avoid overwriting unexpected files
    assert reduced is None


def test_reduce_audio_json_keeps_minimal_fields_and_timecode():
    # Given: an audio JSON with frames_analysis + rich audio_info
    repo_root = Path(__file__).resolve().parents[2]
    mod = _load_json_reducer_module(repo_root)

    raw = {
        "fps": 25,
        "frames_analysis": [
            {
                "frame": 1,
                "audio_info": {
                    "is_speech_present": True,
                    "active_speaker_labels": ["S1"],
                    "timecode_sec": 0.04,
                    "extra": "ignored",
                },
            }
        ],
    }

    # When: reducing the audio JSON
    reduced = mod.reduce_audio_json(raw)

    # Then: output keeps only expected audio fields and preserves timecode_sec
    assert reduced is not None
    assert reduced.get("fps") == 25.0
    assert reduced.get("total_frames") == 1

    frames = reduced.get("frames_analysis")
    assert isinstance(frames, list) and len(frames) == 1
    assert frames[0].get("frame") == 1

    audio_info = frames[0].get("audio_info")
    assert audio_info == {
        "is_speech_present": True,
        "active_speaker_labels": ["S1"],
        "timecode_sec": 0.04,
    }

    speaker_stats = reduced.get("speaker_stats")
    assert speaker_stats == {
        "unique_speakers": ["S1"],
        "speaker_frame_counts": {"S1": 1},
    }


def test_compute_temporal_alignment_emits_warnings_on_mismatch():
    # Given: reduced tracking/audio metadata that mismatches
    repo_root = Path(__file__).resolve().parents[2]
    mod = _load_json_reducer_module(repo_root)

    reduced_tracking = {"fps": 25.0, "total_frames": 100, "frames_analysis": []}
    reduced_audio = {"fps": 30.0, "total_frames": 80, "frames_analysis": []}

    # When: computing temporal alignment
    alignment = mod._compute_temporal_alignment(reduced_tracking, reduced_audio)

    # Then: warnings list includes both fps and frame count mismatches
    assert alignment is not None
    warnings = alignment.get("warnings")
    assert isinstance(warnings, list)
    assert any(str(w).startswith("frame_count_mismatch") for w in warnings)
    assert any(str(w).startswith("fps_mismatch") for w in warnings)


def test_process_directory_writes_tracking_suffix_and_alignment(tmp_path: Path):
    # Given: a docs/ folder with a video + legacy tracking .json + audio json
    repo_root = Path(__file__).resolve().parents[2]
    mod = _load_json_reducer_module(repo_root)

    project_dir = tmp_path / "Camille Test"
    docs_dir = project_dir / "docs"
    docs_dir.mkdir(parents=True)

    video_path = docs_dir / "clip.mp4"
    video_path.write_bytes(b"")

    tracking_legacy = docs_dir / "clip.json"
    _write_json(
        tracking_legacy,
        {
            "fps": 25,
            "total_frames": 2,
            "frames": [
                {
                    "frame": 1,
                    "tracked_objects": [
                        {
                            "id": "face_1",
                            "centroid_x": 111,
                            "source": "face_landmarker",
                            "label": "face",
                            "confidence": 0.9,
                            "bbox_width": 10,
                            "bbox_height": 20,
                        }
                    ],
                }
            ],
        },
    )

    audio_path = docs_dir / "clip_audio.json"
    _write_json(
        audio_path,
        {
            "fps": 25,
            "frames_analysis": [
                {"frame": 1, "audio_info": {"is_speech_present": False, "active_speaker_labels": []}}
            ],
        },
    )

    # When: running directory processing
    mod.process_directory(str(tmp_path), keyword="Camille")

    # Then: reduced tracking is written to *_tracking.json with temporal_alignment
    tracking_out = docs_dir / "clip_tracking.json"
    assert tracking_out.exists()

    reduced = json.loads(tracking_out.read_text(encoding="utf-8"))
    assert isinstance(reduced.get("frames_analysis"), list)
    assert reduced.get("temporal_alignment") is not None


def test_process_directory_enriches_reduced_tracking_from_legacy_when_needed(tmp_path: Path):
    # Given: a docs/ folder with a reduced tracking JSON missing bbox/confidence and a legacy raw JSON with them
    repo_root = Path(__file__).resolve().parents[2]
    mod = _load_json_reducer_module(repo_root)

    project_dir = tmp_path / "Camille Enrich"
    docs_dir = project_dir / "docs"
    docs_dir.mkdir(parents=True)

    video_path = docs_dir / "clip.mp4"
    video_path.write_bytes(b"")

    tracking_out = docs_dir / "clip_tracking.json"
    _write_json(
        tracking_out,
        {
            "fps": 25,
            "total_frames": 1,
            "frames_analysis": [
                {
                    "frame": 1,
                    "tracked_objects": [
                        {
                            "id": "obj_1",
                            "centroid_x": 111,
                            "source": "face_landmarker",
                            "label": "face",
                            # bbox/confidence intentionally missing
                            "active_speakers": [],
                        }
                    ],
                }
            ],
        },
    )

    tracking_legacy = docs_dir / "clip.json"
    _write_json(
        tracking_legacy,
        {
            "fps": 25,
            "total_frames": 1,
            "frames": [
                {
                    "frame": 1,
                    "tracked_objects": [
                        {
                            "id": "obj_1",
                            "centroid_x": 111,
                            "source": "face_landmarker",
                            "label": "face",
                            "confidence": 0.91,
                            "bbox_width": 10,
                            "bbox_height": 20,
                            "active_speakers": ["S1"],
                        }
                    ],
                }
            ],
        },
    )

    # When: running directory processing
    mod.process_directory(str(tmp_path), keyword="Camille")

    # Then: reduced tracking is enriched from legacy without changing file name
    assert tracking_out.exists()
    reduced = json.loads(tracking_out.read_text(encoding="utf-8"))
    frames = reduced.get("frames_analysis")
    assert isinstance(frames, list) and len(frames) == 1
    tracked = frames[0].get("tracked_objects")
    assert isinstance(tracked, list) and len(tracked) == 1
    obj = tracked[0]
    assert obj.get("confidence") == 0.91
    assert obj.get("bbox_width") == 10
    assert obj.get("bbox_height") == 20
    assert obj.get("active_speakers") == ["S1"]


def test_process_directory_without_audio_does_not_crash(tmp_path: Path):
    # Given: a docs/ folder with a video + legacy tracking .json but no audio json
    repo_root = Path(__file__).resolve().parents[2]
    mod = _load_json_reducer_module(repo_root)

    project_dir = tmp_path / "Camille NoAudio"
    docs_dir = project_dir / "docs"
    docs_dir.mkdir(parents=True)

    video_path = docs_dir / "clip.mp4"
    video_path.write_bytes(b"")

    tracking_legacy = docs_dir / "clip.json"
    _write_json(
        tracking_legacy,
        {
            "fps": 25,
            "frames": [
                {
                    "frame": 1,
                    "tracked_objects": [
                        {
                            "id": "face_1",
                            "centroid_x": 111,
                            "source": "face_landmarker",
                            "label": "face",
                        }
                    ],
                }
            ],
        },
    )

    # When: running directory processing
    mod.process_directory(str(tmp_path), keyword="Camille")

    # Then: reduced tracking exists and has no temporal_alignment
    tracking_out = docs_dir / "clip_tracking.json"
    assert tracking_out.exists()

    reduced = json.loads(tracking_out.read_text(encoding="utf-8"))
    assert isinstance(reduced.get("frames_analysis"), list)
    assert "temporal_alignment" not in reduced
