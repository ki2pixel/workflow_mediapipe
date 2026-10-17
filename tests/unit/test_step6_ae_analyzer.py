#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
import json
from pathlib import Path

import pytest


def _load_step7_module():
    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "workflow_scripts" / "step6" / "preprocess_ae_json.py"
    spec = importlib.util.spec_from_file_location("workflow_scripts.step6.preprocess_ae_json", module_path)
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


def test_analyze_manifest_accepts_step5_active_speakers(tmp_path):
    """La STEP5 publie `active_speakers` : la confirmation audio doit marcher sans renommage.

    Sans ce repli, le champ d'entrée était toujours vide dans le flux standard et les
    paliers `best_audio_face` / `best_audio_person` ne se déclenchaient jamais.
    """
    mod = _load_step7_module()

    # Given: deux visages, seul le premier est confirmé par la diarisation, le second est plus large
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
                        "active_speakers": ["SPEAKER_01"],
                        "bbox_surface": 1000.0,
                        "confidence": 0.9,
                    },
                    {
                        "id": "face2",
                        "centroid_x": 900.0,
                        "source": "face_landmarker",
                        "label": "face",
                        "active_speakers": [],
                        "bbox_surface": 5000.0,
                        "confidence": 0.9,
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

    # Then:  le visage confirmé par l'audio l'emporte malgré une surface de bbox plus faible
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


def test_build_ae_payload_streaming_enriches_is_speaking_and_tier(tmp_path):
    mod = _load_step7_module()

    # Given: un tracking JSON avec 2 visages et 1 personne sur 2 frames, audio diarisation active sur frame 1
    tracking_path = tmp_path / "video_tracking.json"
    audio_path = tmp_path / "video_audio.json"
    _write_json(
        tracking_path,
        {
            "dataByFrame": {
                "1": [
                    {
                        "id": "face1",
                        "centroid_x": 100.0,
                        "source": "face_landmarker",
                        "label": "face",
                        "active_speakers": ["SPEAKER_01"],
                        "bbox_surface": 1000.0,
                        "confidence": 0.9,
                    },
                    {
                        "id": "person1",
                        "centroid_x": 500.0,
                        "source": "object_detector",
                        "label": "person",
                        "active_speakers": ["SPEAKER_02"],
                        "bbox_surface": 5000.0,
                        "confidence": 0.8,
                    },
                ],
                "2": [
                    {
                        "id": "face1",
                        "centroid_x": 105.0,
                        "source": "face_landmarker",
                        "label": "face",
                        "active_speakers": ["SPEAKER_01"],
                        "bbox_surface": 1000.0,
                        "confidence": 0.9,
                    },
                    {
                        "id": "person2",
                        "centroid_x": 600.0,
                        "source": "object_detector",
                        "label": "person",
                        "active_speakers": [],
                        "bbox_surface": 4000.0,
                        "confidence": 0.7,
                    },
                ],
            },
            "maxFrame": 2,
        },
    )
    _write_json(
        audio_path,
        {
            "frames": [
                {
                    "frame": 1,
                    "audio_info": {
                        "is_speech_present": True,
                        "active_speaker_labels": ["SPEAKER_01"],
                    },
                },
                {
                    "frame": 2,
                    "audio_info": {
                        "is_speech_present": False,
                        "active_speaker_labels": [],
                    },
                },
            ]
        },
    )

    # When: construction du payload AE pré-traité
    payload = mod.build_ae_payload_streaming(tracking_path, audio_path)

    # Then: chaque objet est enrichi de is_speaking et tier
    assert payload is not None
    data_by_frame = payload["dataByFrame"]

    # Frame 1 : face1 parle (Tier 4), person1 ne parle pas car SPEAKER_02 != SPEAKER_01 (Tier 1)
    f1_objs = {obj["id"]: obj for obj in data_by_frame["1"]}
    assert f1_objs["face1"]["is_speaking"] is True
    assert f1_objs["face1"]["tier"] == 4
    assert f1_objs["person1"]["is_speaking"] is False
    assert f1_objs["person1"]["tier"] == 1

    # Frame 2 : pas de parole -> face1 est Tier 2 (visage silencieux), person2 est Tier 1 (corps silencieux)
    f2_objs = {obj["id"]: obj for obj in data_by_frame["2"]}
    assert f2_objs["face1"]["is_speaking"] is False
    assert f2_objs["face1"]["tier"] == 2
    assert f2_objs["person2"]["is_speaking"] is False
    assert f2_objs["person2"]["tier"] == 1


def test_build_ae_payload_streaming_generates_segment_recommendations_with_csv(tmp_path):
    mod = _load_step7_module()

    # Given: tracking, audio et un CSV de cuts de STEP2
    tracking_path = tmp_path / "clip_tracking.json"
    audio_path = tmp_path / "clip_audio.json"
    csv_path = tmp_path / "clip.csv"

    # CSV avec 2 segments
    csv_path.write_text(
        "No,Timecode In,Timecode Out,Frame In,Frame Out\n"
        "1,00:00:00.000,00:00:00.080,1,2\n"
        "2,00:00:00.120,00:00:00.200,3,5\n",
        encoding="utf-8",
    )

    _write_json(
        tracking_path,
        {
            "dataByFrame": {
                "1": [
                    {
                        "id": "speakerA",
                        "centroid_x": 350.0,
                        "source": "face_landmarker",
                        "label": "face",
                        "active_speakers": ["SPEAKER_01"],
                        "bbox_surface": 1200.0,
                        "confidence": 0.95,
                    }
                ],
                "2": [
                    {
                        "id": "speakerA",
                        "centroid_x": 354.0,
                        "source": "face_landmarker",
                        "label": "face",
                        "active_speakers": ["SPEAKER_01"],
                        "bbox_surface": 1200.0,
                        "confidence": 0.95,
                    }
                ],
            },
            "maxFrame": 5,
        },
    )
    _write_json(
        audio_path,
        {
            "frames": [
                {
                    "frame": 1,
                    "audio_info": {"is_speech_present": True, "active_speaker_labels": ["SPEAKER_01"]},
                },
                {
                    "frame": 2,
                    "audio_info": {"is_speech_present": True, "active_speaker_labels": ["SPEAKER_01"]},
                },
            ]
        },
    )

    # When: build payload with CSV
    payload = mod.build_ae_payload_streaming(tracking_path, audio_path, csv_path)

    # Then: segment_recommendations est présent à la racine
    assert payload is not None
    assert "segment_recommendations" in payload
    recs = payload["segment_recommendations"]
    assert "1" in recs
    assert recs["1"]["recommended_object_id"] == "speakerA"
    assert recs["1"]["tier"] == 4
    assert recs["1"]["target_anchor_x"] == pytest.approx(352.0, abs=0.5)
    assert recs["1"]["needs_review"] is False

    # Segment 2 n'avait aucun objet détecté -> fallback needs_review = True
    assert "2" in recs
    assert recs["2"]["recommended_object_id"] is None
    assert recs["2"]["tier"] == 0
    assert recs["2"]["needs_review"] is True


def test_compute_segment_recommendations_trimmed_mean_and_ghost_rejection():
    mod = _load_step7_module()

    # Given: un segment de 20 frames avec un objet principal (15 frames) contenant 2 outliers
    # et une piste fantôme sur 1 seule frame
    data_by_frame = {}
    # Objet principal : 15 frames, X = 500 pour la plupart, mais 0 au début et 1000 à la fin
    x_coords = [0.0] + [500.0] * 13 + [1000.0]
    for idx, frame in enumerate(range(1, 16)):
        data_by_frame[frame] = [
            {
                "id": "main_face",
                "centroid_x": x_coords[idx],
                "source": "face_landmarker",
                "label": "face",
                "bbox_surface": 2000.0,
                "confidence": 0.9,
                "is_speaking": False,
            }
        ]
    # Piste fantôme sur frame 18 (1 frame < 3 frames et 1/20 = 5% < 10%)
    data_by_frame[18] = [
        {
            "id": "ghost",
            "centroid_x": 200.0,
            "source": "face_landmarker",
            "label": "face",
            "bbox_surface": 3000.0,
            "confidence": 0.99,
            "is_speaking": False,
        }
    ]

    segments = [{"num": "1", "start_frame": 1, "end_frame": 20}]
    audio_by_frame = {}

    # When: calcul des recommandations
    recs = mod.compute_segment_recommendations(data_by_frame, audio_by_frame, segments)

    # Then:
    # 1. main_face est retenu malgré le ghost à plus haute confiance
    assert recs["1"]["recommended_object_id"] == "main_face"
    assert recs["1"]["tier"] == 2  # face silencieuse
    # 2. La moyenne arithmétique brute aurait été (0 + 13*500 + 1000) / 15 = 500.0
    # Avec 15 éléments, k = floor(1.5) = 1 : les 2 extrêmes (0 et 1000) sont élagués
    # La moyenne tronquée est sum(13*500) / 13 = 500.0
    assert recs["1"]["target_anchor_x"] == 500.0
    # Spread est 1000 - 0 = 1000 px > 200 px -> needs_review = True
    assert recs["1"]["spread_x"] == 1000.0
    assert recs["1"]["needs_review"] is True


def test_analyze_manifest_applies_high_spread_label_for_person(tmp_path):
    mod = _load_step7_module()

    # Given: objet de type "person" (object_detector) avec spread > 200 px
    ae_path = tmp_path / "video_ae.json"
    _write_json(
        ae_path,
        {
            "dataByFrame": {
                "1": [
                    {
                        "id": "person1",
                        "centroid_x": 100.0,
                        "source": "object_detector",
                        "label": "person",
                        "video_speakers": [],
                        "bbox_surface": 3000.0,
                        "confidence": 0.9,
                    }
                ],
                "2": [
                    {
                        "id": "person1",
                        "centroid_x": 450.0,
                        "source": "object_detector",
                        "label": "person",
                        "video_speakers": [],
                        "bbox_surface": 3000.0,
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

    # When: analyse du manifest
    results = mod.analyze_manifest(manifest)

    # Then: LABEL_HIGH_SPREAD (12) est appliqué même si ce n'est pas un visage (conformité P0)
    assert results["1"]["label_color"] == 12
    assert results["1"]["selected_id"] == "person1"

