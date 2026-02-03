#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
import json
from pathlib import Path

import pytest


def _load_step7_module():
    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "workflow_scripts" / "step7" / "preprocess_ae_json.py"
    spec = importlib.util.spec_from_file_location("workflow_scripts.step7.preprocess_ae_json", module_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _write_json(path: Path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_analyze_manifest_selects_audio_confirmed_face(tmp_path):
    mod = _load_step7_module()

    # Given: Preconditions
    ae_path = tmp_path / "video_ae.json"
    _write_json(
        ae_path,
        {
            "dataByFrame": {
                "1": [
                    {
                        "id": "face1",
                        "centroid_x": 100.0,
                        "source": "face_landmarker",
                        "label": "face",
                        "video_speakers": ["SPEAKER_01"],
                        "bbox_surface": 1000.0,
                        "confidence": 0.9,
                    },
                    {
                        "id": "person1",
                        "centroid_x": 50.0,
                        "source": "object_detector",
                        "label": "person",
                        "video_speakers": ["SPEAKER_01"],
                        "bbox_surface": 1200.0,
                        "confidence": 0.5,
                    },
                ]
            },
            "maxFrame": 1,
            "audioByFrame": {
                "1": {"is_speech_present": True, "active_speaker_labels": ["SPEAKER_01"]}
            },
            "audioMaxFrame": 1,
        },
    )

    manifest = {
        "comp_name": "Comp",
        "comp_max_frame": 1,
        "layers": {
            "1": {
                "name": "Layer1",
                "json_path": str(ae_path),
                "in_frame": 1,
                "out_frame": 1,
                "video_scale": 1.0,
            }
        },
    }

    # When:  Operation to execute
    results = mod.analyze_manifest(manifest)

    # Then:  Expected result/verification
    assert "1" in results
    assert results["1"]["selected_id"] == "face1"
    assert results["1"]["reason"] == "audio_confirm_face"


def test_analyze_manifest_selects_audio_confirmed_person_when_no_face_audio(tmp_path):
    mod = _load_step7_module()

    # Given: Preconditions
    ae_path = tmp_path / "video_ae.json"
    _write_json(
        ae_path,
        {
            "dataByFrame": {
                "1": [
                    {
                        "id": "face1",
                        "centroid_x": 100.0,
                        "source": "face_landmarker",
                        "label": "face",
                        "video_speakers": [],
                        "bbox_surface": 1000.0,
                        "confidence": 0.9,
                    },
                    {
                        "id": "person1",
                        "centroid_x": 50.0,
                        "source": "object_detector",
                        "label": "person",
                        "video_speakers": ["SPEAKER_01"],
                        "bbox_surface": 1200.0,
                        "confidence": 0.5,
                    },
                ]
            },
            "maxFrame": 1,
            "audioByFrame": {
                "1": {"is_speech_present": True, "active_speaker_labels": ["SPEAKER_01"]}
            },
            "audioMaxFrame": 1,
        },
    )

    manifest = {
        "comp_name": "Comp",
        "comp_max_frame": 1,
        "layers": {
            "1": {
                "name": "Layer1",
                "json_path": str(ae_path),
                "in_frame": 1,
                "out_frame": 1,
                "video_scale": 1.0,
            }
        },
    }

    # When:  Operation to execute
    results = mod.analyze_manifest(manifest)

    # Then:  Expected result/verification
    assert "1" in results
    assert results["1"]["selected_id"] == "person1"
    assert results["1"]["reason"] == "audio_confirm_person"


def test_analyze_manifest_applies_high_spread_label_for_face(tmp_path):
    mod = _load_step7_module()

    # Given: Preconditions
    ae_path = tmp_path / "video_ae.json"
    _write_json(
        ae_path,
        {
            "dataByFrame": {
                "1": [
                    {
                        "id": "face1",
                        "centroid_x": 0.0,
                        "source": "face_landmarker",
                        "label": "face",
                        "video_speakers": [],
                        "bbox_surface": 1000.0,
                        "confidence": 0.9,
                    }
                ],
                "2": [
                    {
                        "id": "face1",
                        "centroid_x": 500.0,
                        "source": "face_landmarker",
                        "label": "face",
                        "video_speakers": [],
                        "bbox_surface": 1000.0,
                        "confidence": 0.9,
                    }
                ],
            },
            "maxFrame": 2,
            "audioByFrame": {},
            "audioMaxFrame": None,
        },
    )

    manifest = {
        "comp_name": "Comp",
        "comp_max_frame": 2,
        "config": {
            "SPREAD_THRESHOLD": 200,
            "LABEL_HIGH_SPREAD": 12,
            "LABEL_STABLE": 3,
        },
        "layers": {
            "1": {
                "name": "Layer1",
                "json_path": str(ae_path),
                "in_frame": 1,
                "out_frame": 2,
                "video_scale": 1.0,
            }
        },
    }

    # When:  Operation to execute
    results = mod.analyze_manifest(manifest)

    # Then:  Expected result/verification
    assert results["1"]["label_color"] == 12


def test_analyze_manifest_maps_frame_scale_when_video_and_comp_lengths_differ(tmp_path):
    mod = _load_step7_module()

    # Given: Preconditions
    ae_path = tmp_path / "video_ae.json"
    _write_json(
        ae_path,
        {
            "dataByFrame": {
                "100": [
                    {
                        "id": "face1",
                        "centroid_x": 123.0,
                        "source": "face_landmarker",
                        "label": "face",
                        "video_speakers": [],
                        "bbox_surface": 1000.0,
                        "confidence": 0.9,
                    }
                ]
            },
            "maxFrame": 200,
            "audioByFrame": {},
            "audioMaxFrame": None,
        },
    )

    manifest = {
        "comp_name": "Comp",
        "comp_max_frame": 100,
        "layers": {
            "1": {
                "name": "Layer1",
                "json_path": str(ae_path),
                "in_frame": 50,
                "out_frame": 50,
                "video_scale": 1.0,
            }
        },
    }

    # When:  Operation to execute
    results = mod.analyze_manifest(manifest)

    # Then:  Expected result/verification
    assert "1" in results
    assert results["1"]["selected_id"] == "face1"


def test_main_writes_error_json_when_manifest_invalid(tmp_path, monkeypatch):
    mod = _load_step7_module()

    # Given: Preconditions
    manifest_path = tmp_path / "manifest.json"
    out_path = tmp_path / "out.json"
    manifest_path.write_text("[]", encoding="utf-8")

    monkeypatch.setattr(
        mod.sys,
        "argv",
        [
            "preprocess_ae_json.py",
            "--manifest_path",
            str(manifest_path),
            "--output_path",
            str(out_path),
        ],
    )

    # When:  Operation to execute
    mod.main()

    # Then:  Expected result/verification
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert "error" in payload
    assert isinstance(payload["error"], str)
