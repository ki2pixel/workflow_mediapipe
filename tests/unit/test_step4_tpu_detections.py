"""Tests du mapping de classes et des builders de détection du chemin STEP4 Coral TPU."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils import step4_tpu_detections as detections


def test_embedded_labels_match_the_companion_labelmap():
    """La liste embarquée doit être l'exacte copie du labelmap du modèle."""
    # Given
    labels = detections.EFFICIENTDET_LABELS

    # When / Then
    assert len(labels) == 91
    assert labels[0] == "???"
    assert labels[1] == "person"
    assert labels[-1] == "toothbrush"


def test_companion_labelmap_file_is_consistent():
    """Le fichier compagnon livré avec le modèle ne doit pas diverger."""
    # Given / When
    divergence = detections.verify_labelmap_file()

    # Then
    assert divergence is None


def test_labelmap_divergence_is_reported(tmp_path):
    """Un labelmap divergent est signalé (jamais bloquant) et un fichier absent aussi."""
    # Given
    divergent = tmp_path / "labelmap.txt"
    divergent.write_text("???\nperson\n", encoding="utf-8")

    # When
    message = detections.verify_labelmap_file(divergent)
    missing = detections.verify_labelmap_file(tmp_path / "absent.txt")

    # Then
    assert message is not None and "divergent" in message
    assert missing is not None and "illisible" in missing


def test_model_class_index_maps_to_coco_name():
    """L'indice modèle est décalé de +1 par rapport au labelmap (person = 0)."""
    # Given / When / Then
    assert detections.label_for_class_index(0) == "person"
    assert detections.label_for_class_index(2) == "car"
    assert detections.label_for_class_index(33) == "frisbee"
    assert detections.label_for_class_index(61) == "chair"
    assert detections.label_for_class_index(66) == "dining table"
    assert detections.label_for_class_index(83) == "book"
    assert detections.label_for_class_index(85) == "vase"
    assert detections.label_for_class_index(89) == "toothbrush"


def test_dead_and_out_of_range_class_indices_have_no_label():
    """Les 10 identifiants morts du COCO et les indices hors plage n'ont pas de libellé."""
    # Given
    dead = sorted(detections.DEAD_CLASS_INDICES)

    # When / Then
    assert dead == [11, 25, 28, 29, 44, 65, 67, 68, 70, 82]
    for index in dead:
        assert detections.label_for_class_index(index) is None
    assert detections.label_for_class_index(-1) is None
    assert detections.label_for_class_index(90) is None
    assert detections.label_for_class_index(200) is None


def test_resolve_class_label_falls_back_without_ever_claiming_person():
    """Le repli conserve le diagnostic et ne peut pas devenir « person »."""
    # Given / When / Then
    assert detections.resolve_class_label(0) == "person"
    assert detections.resolve_class_label(1.0000001) == "bicycle"
    assert detections.resolve_class_label(11) == "class_11"
    assert detections.resolve_class_label(200) == "class_200"
    assert detections.resolve_class_label("invalid") == "class_invalid"


def test_build_face_detection_publishes_the_canonical_face_dict():
    """Le visage porte le même contrat que le chemin séquentiel (label « face »)."""
    # Given
    bbox = (10, 20, 30, 40)
    centroid = (25, 40)
    blendshapes = {"jawOpen": 0.5}

    # When
    detection = detections.build_face_detection(centroid, bbox, blendshapes)

    # Then
    assert detection["source_detector"] == "face_landmarker"
    assert detection["label"] == "face"
    assert detection["confidence"] == 0.95
    assert detection["centroid"] == centroid
    assert detection["bbox"] == bbox
    assert detection["blendshapes"] == blendshapes


def test_build_object_detections_matches_the_legacy_layout():
    """Les champs et le calcul de boîte restent identiques au code d'origine."""
    # Given
    boxes = [[0.10, 0.20, 0.60, 0.40]]
    classes = [0.0]
    scores = [0.8]

    # When
    result = detections.build_object_detections(boxes, classes, scores, 1, 1920, 1080)

    # Then
    assert len(result) == 1
    detection = result[0]
    assert detection["label"] == "person"
    assert detection["source_detector"] == "object_detector"
    assert detection["blendshapes"] == {}
    assert detection["confidence"] == pytest.approx(0.8)
    assert detection["bbox"] == (384, 108, 384, 540)
    assert detection["centroid"] == (384 + 384 // 2, 108 + 540 // 2)


def test_build_object_detections_filters_caps_and_clamps():
    """Seuil de score, plafond d'objets et bornage à l'écran sont appliqués."""
    # Given
    boxes = [[0.0, 0.0, 2.0, 2.0]] * 7
    classes = [2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    scores = [0.9, 0.2, 0.4, 0.4, 0.4, 0.4, 0.4]

    # When
    result = detections.build_object_detections(boxes, classes, scores, 7, 1920, 1080)

    # Then
    assert len(result) == 4
    assert result[0]["label"] == "car"
    assert all(item["bbox"] == (0, 0, 1920, 1080) for item in result)
    assert all(item["centroid"] == (960, 540) for item in result)
    for item in result:
        assert item["bbox"][0] >= 0 and item["bbox"][1] >= 0
        assert item["bbox"][0] + item["bbox"][2] <= 1920
        assert item["bbox"][1] + item["bbox"][3] <= 1080


def test_build_object_detections_keeps_a_dead_class_as_diagnostic():
    """Un indice mort ne peut jamais être publié comme « person »."""
    # Given
    boxes = [[0.1, 0.1, 0.2, 0.2]]
    classes = [11.0]
    scores = [0.9]

    # When
    result = detections.build_object_detections(boxes, classes, scores, 1, 1920, 1080)

    # Then
    assert result[0]["label"] == "class_11"
