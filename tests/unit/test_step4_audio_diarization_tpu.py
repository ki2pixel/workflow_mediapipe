#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests unitaires pour STEP4 (VAD & Diarisation alternatif via Google Coral Edge TPU).
"""

import sys
import pytest
from pathlib import Path
from importlib import util as _import_util
from unittest.mock import MagicMock, patch

# Vérification dépendances (numpy, sklearn, scipy)
if _import_util.find_spec("numpy") is None or _import_util.find_spec("sklearn") is None or _import_util.find_spec("scipy") is None:
    pytestmark = pytest.mark.skip(
        reason="numpy, scikit-learn ou scipy non disponibles dans cet environnement; tests STEP4 TPU ignorés."
    )
else:
    import numpy as np

# --- MOCKING PYCORAL & TFLITE ---
mock_edgetpu = MagicMock()
mock_common = MagicMock()
mock_tflite = MagicMock()

sys.modules['pycoral'] = MagicMock()
sys.modules['pycoral.utils'] = MagicMock()
sys.modules['pycoral.utils.edgetpu'] = mock_edgetpu
mock_adapters = MagicMock()
mock_adapters.common = mock_common
sys.modules['pycoral.adapters'] = mock_adapters
sys.modules['pycoral.adapters.common'] = mock_common
sys.modules['tflite_runtime'] = MagicMock()
sys.modules['tflite_runtime.interpreter'] = mock_tflite

# Les vérifications d'import ont été déplacées au début du fichier.
BASE_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_PATH / "workflow_scripts" / "step4"))

try:
    from run_audio_diarization_tpu import perform_clustering, run_vad_and_embedding, _write_audio_json_file
except ImportError as e:
    pytestmark = pytest.mark.skip(reason=f"Impossible d'importer run_audio_diarization_tpu: {e}")

class TestStep4TPUClustering:
    """Validation de l'algorithme de clustering spectral (CPU)"""

    def test_perform_clustering_empty(self):
        # Given: Aucun embedding
        embeddings = np.array([])
        segments = []
        
        # When: Clustering
        results = perform_clustering(embeddings, segments)
        
        # Then: Retourne une liste vide
        assert results == []

    def test_perform_clustering_single(self):
        # Given: 1 seul embedding
        embeddings = np.array([[0.5, 0.5]])
        segments = [[0.0, 1.0]]
        
        # When: Clustering
        results = perform_clustering(embeddings, segments)
        
        # Then: Retourne 1 segment pour SPEAKER_00
        assert len(results) == 1
        assert results[0]["speaker"] == "SPEAKER_00"
        assert results[0]["start"] == 0.0
        assert results[0]["end"] == 1.0

    def test_perform_clustering_multiple(self):
        # Given: Des embeddings clairs pour 2 locuteurs
        # Locuteur 1: très fort sur X, Locuteur 2: très fort sur Y
        # Il faut plus de 10 échantillons pour que kneighbors_graph() ne lève pas d'erreur,
        # vu que le paramètre par défaut est n_neighbors=10 dans SpectralClustering.
        embeddings = np.array([
            [1.0, 0.0], [1.0, 0.0], [1.0, 0.0], [1.0, 0.0], [1.0, 0.0], [1.0, 0.0],  # SPEAKER 1
            [0.0, 1.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0]   # SPEAKER 2
        ])
        segments = [
            [0.0, 1.0], [1.1, 2.0], [2.1, 3.0], [3.1, 4.0], [4.1, 5.0], [5.1, 6.0],
            [6.1, 7.0], [7.1, 8.0], [8.1, 9.0], [9.1, 10.0], [10.1, 11.0], [11.1, 12.0]
        ]
        
        # When: Clustering
        results = perform_clustering(embeddings, segments)
        
        # Then: Les segments adjacents du même locuteur sont fusionnés
        assert len(results) > 0
        # On vérifie la structure de sortie
        for res in results:
            assert "speaker" in res
            assert "start" in res
            assert "end" in res
            assert res["start"] < res["end"]

class TestStep4TPUVAD:
    """Validation du flux VAD simulé"""
    
    @patch("run_audio_diarization_tpu.wavfile.read")
    def test_run_vad_and_embedding(self, mock_wavfile_read):
        # Given: Un faux fichier WAV de 3 secondes à 16kHz
        sr = 16000
        data = np.zeros(sr * 3, dtype=np.int16)
        mock_wavfile_read.return_value = (sr, data)
        
        interpreter = MagicMock()
        interpreter.get_input_details.return_value = [{
            'shape': (15360,),
            'dtype': np.int16,
            'index': 0,
            'quantization': (1.0, 0)
        }]
        interpreter.get_output_details.return_value = [
            {'index': 0, 'dtype': np.float32, 'quantization': (1.0, 0)},
            {'index': 1, 'dtype': np.float32, 'quantization': (1.0, 0)},
            {'index': 2, 'dtype': np.float32, 'quantization': (1.0, 0)}
        ]
        
        # Simuler get_tensor
        def get_tensor_side_effect(index):
            if index == 0:
                # Retourne un score de Speech (0.8) pour déclencher le VAD
                return np.array([[0.8]], dtype=np.float32)
            elif index == 2:
                # Retourne l'embedding
                return np.array([[np.ones(128)]], dtype=np.float32)
            return np.array([0])
            
        interpreter.get_tensor.side_effect = get_tensor_side_effect
 
        # When: Analyse VAD
        segments, embeddings = run_vad_and_embedding(Path("dummy.wav"), interpreter, None)
        
        # Then: Les segments et embeddings sont extraits
        assert len(segments) > 0
        assert len(embeddings) > 0
        assert len(segments) == len(embeddings)

class TestStep4TPUJsonFormat:
    """Validation du format JSON de sortie généré pour compatibilité STEP5/6"""
    
    def test_write_audio_json_file(self, tmp_path):
        import json
        # Given: Faux résultats de diarisation et paramètres associés
        output_json = tmp_path / "video_audio.json"
        video_path = Path("video.mp4")
        diarization_result = [
            {"speaker": "SPEAKER_00", "start": 0.0, "end": 1.0},
            {"speaker": "SPEAKER_01", "start": 1.5, "end": 2.5}
        ]
        duration_sec = 3.0
        fps = 25.0
        
        # When: Écriture du fichier JSON
        _write_audio_json_file(output_json, video_path, diarization_result, duration_sec, None, fps)
        
        # Then: Le fichier existe, est valide et contient la structure attendue
        assert output_json.exists()
        with open(output_json, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        assert data["video_filename"] == "video.mp4"
        assert data["total_frames"] == 75 # 3.0 * 25.0
        assert data["fps"] == 25.0
        assert "frames_analysis" in data
        assert isinstance(data["frames_analysis"], list)
        assert len(data["frames_analysis"]) == 75
        
        # Vérification d'une frame spécifique de parole (SPEAKER_00 actif entre 0s et 1s)
        # Frame 10 (0.36s)
        frame_10 = data["frames_analysis"][9]
        assert frame_10["frame"] == 10
        assert frame_10["audio_info"]["is_speech_present"] is True
        assert frame_10["audio_info"]["active_speaker_labels"] == ["SPEAKER_00"]
        assert frame_10["audio_info"]["num_distinct_speakers_audio"] == 1
        assert frame_10["audio_info"]["timecode_sec"] == 0.36

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

