import importlib.util
import json
import sys
from pathlib import Path


def _load_json_reducer_module():
    module_name = "step6_json_reducer_speaker_embeddings"
    if module_name in sys.modules:
        return sys.modules[module_name]

    module_path = (
        Path(__file__).resolve().parents[2]
        / "workflow_scripts"
        / "step6"
        / "json_reducer.py"
    )
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_reduce_audio_json_preserves_speaker_embeddings():
    # // Given: audio JSON with frames_analysis and speaker_embeddings
    reducer = _load_json_reducer_module()
    raw = {
        "fps": 25,
        "frames_analysis": [
            {
                "frame": 1,
                "audio_info": {
                    "is_speech_present": True,
                    "active_speaker_labels": ["S1"],
                    "timecode_sec": 0.04,
                },
            }
        ],
        "speaker_embeddings": {
            "model_id": "pyannote/embedding",
            "embedding_dim": 3,
            "normalized": True,
            "vectors_by_label": {"SPEAKER_00": [0.1, 0.2, 0.3]},
            "num_segments_by_label": {"SPEAKER_00": 1},
        },
    }

    # // When: reducing the audio JSON
    reduced = reducer.reduce_audio_json(raw)

    # // Then: speaker_embeddings is preserved in the reduced output
    assert reduced is not None
    assert reduced.get("fps") == 25.0
    assert reduced.get("total_frames") == 1
    assert "speaker_embeddings" in reduced
    assert reduced["speaker_embeddings"] == raw["speaker_embeddings"]


def test_reduce_audio_json_ignores_missing_or_empty_speaker_embeddings():
    # // Given: audio JSON without speaker_embeddings or with empty dict
    reducer = _load_json_reducer_module()
    raw_without = {
        "fps": 25,
        "frames_analysis": [
            {"frame": 1, "audio_info": {"is_speech_present": False, "active_speaker_labels": []}}
        ],
    }
    raw_empty = {
        "fps": 25,
        "frames_analysis": [
            {"frame": 1, "audio_info": {"is_speech_present": False, "active_speaker_labels": []}}
        ],
        "speaker_embeddings": {},
    }

    # // When: reducing both JSONs
    reduced_without = reducer.reduce_audio_json(raw_without)
    reduced_empty = reducer.reduce_audio_json(raw_empty)

    # // Then: speaker_embeddings is absent in both reduced outputs
    assert reduced_without is not None
    assert "speaker_embeddings" not in reduced_without

    assert reduced_empty is not None
    assert "speaker_embeddings" not in reduced_empty
