"""
Tests unitaires pour STEP5_EXPORT_VERBOSE_FIELDS (réduction taille JSON).

Vérifie que la variable d'environnement contrôle correctement l'export
des données volumineuses (landmarks, coefficients EOS) tout en préservant
la compatibilité avec STEP6.
"""

import os
import pytest
from unittest.mock import MagicMock
from utils.tracking_optimizations import apply_tracking_and_management


class TestExportVerboseFields:
    """Tests pour le contrôle de l'export des champs volumineux."""

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Sauvegarde et restaure les variables d'environnement."""
        original_verbose = os.environ.get('STEP5_EXPORT_VERBOSE_FIELDS')
        yield
        if original_verbose is not None:
            os.environ['STEP5_EXPORT_VERBOSE_FIELDS'] = original_verbose
        else:
            os.environ.pop('STEP5_EXPORT_VERBOSE_FIELDS', None)

    @pytest.fixture
    def mock_detection_with_verbose_fields(self):
        """Détection faciale avec landmarks et coefficients EOS."""
        return {
            "bbox": (100, 200, 150, 180),
            "centroid": (175, 290),
            "source_detector": "face_landmarker",
            "confidence": 0.95,
            "blendshapes": {"jawOpen": 0.12, "mouthSmile": 0.05},
            "landmarks": [[100.0, 150.0, -2.0]] * 68,  # 68 points EOS
            "eos": {
                "shape_coeffs": [0.1, 0.2, 0.3, 0.4, 0.5],
                "expression_coeffs": [0.01, 0.02, 0.03]
            }
        }

    @pytest.fixture
    def mock_detection_opencv_yunet_pyfeat(self):
        """Détection opencv_yunet_pyfeat avec 478 landmarks."""
        return {
            "bbox": (120, 220, 160, 190),
            "centroid": (200, 315),
            "source_detector": "face_landmarker",
            "confidence": 0.92,
            "blendshapes": {"jawOpen": 0.15, "mouthSmile": 0.08, "eyeBlinkLeft": 0.02},
            "landmarks": [[x, y, z] for x, y, z in zip(range(478), range(478), range(478))]
        }

    @pytest.fixture
    def mock_enhanced_speaking_detector(self):
        """Mock du détecteur de parole enrichi."""
        detector = MagicMock()
        result = MagicMock()
        result.is_speaking = True
        result.confidence = 0.85
        result.method = "audio_primary"
        result.sources = {"audio": {"is_speech_present": True}}
        detector.detect_speaking.return_value = result
        return detector

    def test_export_verbose_false_removes_landmarks_and_eos(
        self, mock_detection_with_verbose_fields, mock_enhanced_speaking_detector
    ):
        """Avec STEP5_EXPORT_VERBOSE_FIELDS=false, landmarks et eos ne sont pas exportés."""
        os.environ['STEP5_EXPORT_VERBOSE_FIELDS'] = 'false'
        
        active_objects = {}
        current_detections = [mock_detection_with_verbose_fields]
        next_id_counter = {"value": 0}

        result = apply_tracking_and_management(
            active_objects,
            current_detections,
            next_id_counter,
            distance_threshold=50,
            frames_unseen_to_deregister=5,
            enhanced_speaking_detector=mock_enhanced_speaking_detector,
            current_frame_num=1
        )

        assert len(result) == 1
        obj = result[0]
        
        assert "id" in obj
        assert "centroid_x" in obj
        assert "centroid_y" in obj
        assert "bbox_width" in obj
        assert "bbox_height" in obj
        assert "source" in obj
        assert "label" in obj
        assert "confidence" in obj
        assert "blendshapes" in obj
        
        assert "landmarks" not in obj
        assert "eos" not in obj

    def test_export_verbose_true_includes_landmarks_and_eos(
        self, mock_detection_with_verbose_fields, mock_enhanced_speaking_detector
    ):
        """Avec STEP5_EXPORT_VERBOSE_FIELDS=true, landmarks et eos sont exportés."""
        os.environ['STEP5_EXPORT_VERBOSE_FIELDS'] = 'true'
        
        active_objects = {}
        current_detections = [mock_detection_with_verbose_fields]
        next_id_counter = {"value": 0}

        result = apply_tracking_and_management(
            active_objects,
            current_detections,
            next_id_counter,
            distance_threshold=50,
            frames_unseen_to_deregister=5,
            enhanced_speaking_detector=mock_enhanced_speaking_detector,
            current_frame_num=1
        )

        assert len(result) == 1
        obj = result[0]
        
        assert "id" in obj
        assert "centroid_x" in obj
        
        assert "landmarks" in obj
        assert len(obj["landmarks"]) == 68
        assert "eos" in obj
        assert "shape_coeffs" in obj["eos"]
        assert "expression_coeffs" in obj["eos"]

    def test_export_verbose_variants(
        self, mock_detection_with_verbose_fields, mock_enhanced_speaking_detector
    ):
        """Test des différentes variantes de valeurs pour STEP5_EXPORT_VERBOSE_FIELDS."""
        active_objects = {}
        next_id_counter = {"value": 0}
        
        for true_value in ["true", "1", "yes", "on", "all"]:
            os.environ['STEP5_EXPORT_VERBOSE_FIELDS'] = true_value
            active_objects_copy = {}
            current_detections = [mock_detection_with_verbose_fields.copy()]
            
            result = apply_tracking_and_management(
                active_objects_copy,
                current_detections,
                {"value": 0},
                distance_threshold=50,
                frames_unseen_to_deregister=5,
                enhanced_speaking_detector=mock_enhanced_speaking_detector,
                current_frame_num=1
            )
            
            assert "landmarks" in result[0], f"Failed for value: {true_value}"
            assert "eos" in result[0], f"Failed for value: {true_value}"
        
        for false_value in ["false", "0", "no", "off", ""]:
            os.environ['STEP5_EXPORT_VERBOSE_FIELDS'] = false_value
            active_objects_copy = {}
            current_detections = [mock_detection_with_verbose_fields.copy()]
            
            result = apply_tracking_and_management(
                active_objects_copy,
                current_detections,
                {"value": 100},
                distance_threshold=50,
                frames_unseen_to_deregister=5,
                enhanced_speaking_detector=mock_enhanced_speaking_detector,
                current_frame_num=1
            )
            
            assert "landmarks" not in result[0], f"Failed for value: {false_value}"
            assert "eos" not in result[0], f"Failed for value: {false_value}"

    def test_opencv_yunet_pyfeat_large_landmarks(
        self, mock_detection_opencv_yunet_pyfeat, mock_enhanced_speaking_detector
    ):
        """Test avec opencv_yunet_pyfeat (478 landmarks volumineux)."""
        os.environ['STEP5_EXPORT_VERBOSE_FIELDS'] = 'false'
        
        active_objects = {}
        current_detections = [mock_detection_opencv_yunet_pyfeat]
        next_id_counter = {"value": 0}

        result = apply_tracking_and_management(
            active_objects,
            current_detections,
            next_id_counter,
            distance_threshold=50,
            frames_unseen_to_deregister=5,
            enhanced_speaking_detector=mock_enhanced_speaking_detector,
            current_frame_num=1
        )

        assert len(result) == 1
        obj = result[0]
        
        assert "blendshapes" in obj
        assert "jawOpen" in obj["blendshapes"]
        
        assert "landmarks" not in obj

    def test_non_face_objects_never_have_verbose_fields(self, mock_enhanced_speaking_detector):
        """Les objets non-faciaux n'ont jamais de landmarks/eos."""
        os.environ['STEP5_EXPORT_VERBOSE_FIELDS'] = 'true'
        
        detection_object = {
            "bbox": (50, 100, 200, 300),
            "centroid": (150, 250),
            "source_detector": "object_detector",
            "confidence": 0.88,
            "label": "person"
        }
        
        active_objects = {}
        current_detections = [detection_object]
        next_id_counter = {"value": 0}

        result = apply_tracking_and_management(
            active_objects,
            current_detections,
            next_id_counter,
            distance_threshold=50,
            frames_unseen_to_deregister=5,
            enhanced_speaking_detector=mock_enhanced_speaking_detector,
            current_frame_num=1
        )

        assert len(result) == 1
        obj = result[0]
        
        assert "landmarks" not in obj
        assert "eos" not in obj
        assert obj["source"] == "object_detector"

    def test_step6_compatibility_preserved(
        self, mock_detection_with_verbose_fields, mock_enhanced_speaking_detector
    ):
        """Vérifier que tous les champs requis par STEP6 sont présents."""
        os.environ['STEP5_EXPORT_VERBOSE_FIELDS'] = 'false'
        
        active_objects = {}
        current_detections = [mock_detection_with_verbose_fields]
        next_id_counter = {"value": 0}

        result = apply_tracking_and_management(
            active_objects,
            current_detections,
            next_id_counter,
            distance_threshold=50,
            frames_unseen_to_deregister=5,
            enhanced_speaking_detector=mock_enhanced_speaking_detector,
            current_frame_num=1
        )

        assert len(result) == 1
        obj = result[0]
        
        required_step6_fields = [
            "id",
            "centroid_x",
            "source",
            "label",
            "bbox_width",
            "bbox_height"
        ]
        
        for field in required_step6_fields:
            assert field in obj, f"Champ requis STEP6 manquant: {field}"
        
        assert "speaking_sources" in obj
        
        assert obj["bbox_width"] == 150
        assert obj["bbox_height"] == 180
        assert obj["centroid_x"] == 175
