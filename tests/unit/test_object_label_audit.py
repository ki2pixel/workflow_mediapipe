"""Tests de l'audit des pistes d'objets (sélection par segment, métriques de valeur)."""

import importlib.util
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_audit_module():
    spec = importlib.util.spec_from_file_location(
        "audit_object_labels", PROJECT_ROOT / "scripts" / "audit_object_labels.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["audit_object_labels"] = module
    spec.loader.exec_module(module)
    return module


audit = _load_audit_module()


def _write_ae(tmp_path: Path, name: str, frames: dict) -> Path:
    payload = {"schema": "ae_preprocessed", "schemaVersion": 1, "fps": 25, "dataByFrame": {
        str(frame): objects for frame, objects in frames.items()
    }}
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _csv(tmp_path: Path, rows) -> Path:
    """CSV au format réel du dépôt : `No,Timecode In,Timecode Out,Frame In,Frame Out`."""
    path = tmp_path / "cuts.csv"
    lines = ["No,Timecode In,Timecode Out,Frame In,Frame Out"]
    for index, (num, start, end) in enumerate(rows, start=1):
        lines.append(f"{num},{start},{end},{index},{index + 10}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_timecode_parsing_accepts_csv_formats():
    """Les CSV réels utilisent le point décimal ; la virgule est tolérée par sécurité."""
    # Given / When / Then
    assert audit.parse_timecode("00:00:01.500") == 1.5
    assert audit.parse_timecode("00:00:01,500") == 1.5
    assert audit.parse_timecode("01:02:03.250") == 3723.25
    assert audit.parse_timecode("12.5") == 12.5
    assert audit.parse_timecode("n/a") is None


def test_csv_segments_skip_header_and_invalid_rows():
    """Seules les lignes valides (3 colonnes, fin > début) deviennent des segments."""
    # Given
    content = (
        "No,Timecode In,Timecode Out,Frame In,Frame Out\n"
        "1,00:00:00.000,00:00:02.000,1,50\n"
        "ligne_invalide\n"
        "2,00:00:02.000,00:00:02.000,51,51\n"
    )

    # When
    segments = audit.parse_csv_segments(content)

    # Then
    assert len(segments) == 1
    assert segments[0]["num"] == "1"
    assert segments[0]["start"] == 0.0 and segments[0]["end"] == 2.0


def test_csv_line_splitting_keeps_quoted_commas():
    """Un champ entre guillemets conserve ses virgules."""
    # Given / When
    fields = audit.split_csv_line('1,"00:00:01,000",plain')

    # Then
    assert fields == ["1", "00:00:01,000", "plain"]


def test_selection_uses_presence_and_confidence_like_the_panel(tmp_path):
    """Le score reproduit le panneau : présence × (1 + confiance × 0,35)."""
    # Given : une piste dense et confiante, une piste rare et peu confiante
    frames = {}
    for frame in range(0, 26):
        objects = [{"id": "dense", "centroid_x": 500, "source": "face_landmarker", "label": "face",
                    "confidence": 0.9, "bbox_surface": 1000}]
        if frame < 5:
            objects.append({"id": "rare", "centroid_x": 1500, "source": "object_detector",
                            "label": "person", "confidence": 0.2, "bbox_surface": 99999})
        frames[frame] = objects
    ae_path = _write_ae(tmp_path, "clip_ae.json", frames)
    csv_path = _csv(tmp_path, [("1", "00:00:00.000", "00:00:01.000")])

    # When
    selection = audit.audit_segments(ae_path, csv_path, fps=25)["selections"][0]["best"]

    # Then
    assert selection["id"] == "dense"
    assert selection["presence"] == 26
    assert selection["center_x"] == 500


def test_selection_tie_breaks_on_bounding_box_surface(tmp_path):
    """À score égal, la piste la plus large gagne (départage du panneau)."""
    # Given
    frames = {frame: [
        {"id": "small", "centroid_x": 100, "source": "object_detector", "label": "person",
         "confidence": 0.5, "bbox_surface": 100},
        {"id": "big", "centroid_x": 900, "source": "object_detector", "label": "person",
         "confidence": 0.5, "bbox_surface": 5000},
    ] for frame in range(0, 5)}
    ae_path = _write_ae(tmp_path, "clip_ae.json", frames)
    csv_path = _csv(tmp_path, [("1", "00:00:00.000", "00:00:00.160")])

    # When
    selection = audit.audit_segments(ae_path, csv_path, fps=25)["selections"][0]["best"]

    # Then
    assert selection["id"] == "big"


def test_segment_without_any_track_has_no_candidate(tmp_path):
    """Un segment sans piste ne peut pas être recentré (fallback du panneau)."""
    # Given
    ae_path = _write_ae(tmp_path, "clip_ae.json", {5: []})
    csv_path = _csv(tmp_path, [("1", "00:00:01.000", "00:00:02.000")])

    # When
    result = audit.audit_segments(ae_path, csv_path, fps=25)

    # Then
    assert result["segments"] == 1
    assert result["segments_with_candidate"] == 0
    assert result["selections"][0]["best"] is None


def test_value_metrics_reward_a_segment_gaining_a_person_track(tmp_path):
    """V1/V2 : un segment sans visage gagne une piste personne grâce au correctif."""
    # Given : « avant », seules les frames avec visage existent ; « après », la personne est là
    before = _write_ae(tmp_path, "before_ae.json", {
        0: [{"id": "face_1", "centroid_x": 960, "source": "face_landmarker", "label": "face",
             "confidence": 0.95, "bbox_surface": 4000}],
    })
    after = _write_ae(tmp_path, "after_ae.json", {
        0: [{"id": "face_1", "centroid_x": 960, "source": "face_landmarker", "label": "face",
             "confidence": 0.95, "bbox_surface": 4000}],
        30: [{"id": "person_1", "centroid_x": 1400, "source": "object_detector", "label": "person",
              "confidence": 0.7, "bbox_surface": 20000}],
        31: [{"id": "person_1", "centroid_x": 1410, "source": "object_detector", "label": "person",
              "confidence": 0.7, "bbox_surface": 20000}],
    })
    csv_path = _csv(tmp_path, [("1", "00:00:00.000", "00:00:00.500"), ("2", "00:00:01.000", "00:00:01.400")])

    # When
    audit_before = audit.audit_segments(before, csv_path, fps=25)
    audit_after = audit.audit_segments(after, csv_path, fps=25)
    metrics = audit.compare_selections(audit_before, audit_after)

    # Then
    assert audit_before["coverage_pct"] == 50.0
    assert audit_after["coverage_pct"] == 100.0
    assert metrics["segments_gaining_a_candidate"] == 1
    assert metrics["segments_with_changed_center"] == 0


def test_step4_label_inventory_reports_runs_and_labels(tmp_path):
    """L'inventaire STEP4 compte les libellés et l'intermittence du visage."""
    # Given
    payload = {"frames": [
        {"frame": 0, "tracked_objects": [{"source": "face_landmarker", "label": "face"}]},
        {"frame": 1, "tracked_objects": [{"source": "object_detector", "label": "person"}]},
        {"frame": 2, "tracked_objects": [{"source": "object_detector", "label": "person"}]},
        {"frame": 3, "tracked_objects": [{"source": "object_detector", "label": "car"}]},
    ]}
    path = tmp_path / "clip.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    # When
    result = audit.audit_step4_labels(path)

    # Then
    assert result["frames"] == 4
    assert result["face_rate_pct"] == 25.0
    assert result["object_rate_pct"] == 75.0
    assert result["label_counts"] == {"person": 2, "car": 1}
    assert result["faceless_run_max"] == 3
    assert result["faceless_runs_under_threshold"] == 1
    assert result["frames_in_short_runs"] == 3
