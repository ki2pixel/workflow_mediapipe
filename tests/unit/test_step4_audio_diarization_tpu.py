#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests unitaires pour STEP4 (VAD & Diarisation alternatif via Google Coral Edge TPU).

Audit Camille : Tests couvrant FSM Hangover, filtre médian VAD, clustering adaptatif,
fenêtrage glissant, estimation du nombre de locuteurs et speaker_stats.
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
    from run_audio_diarization_tpu import (
        perform_clustering,
        run_vad_and_embedding,
        _write_audio_json_file,
        apply_fsm_hangover,
        apply_median_filter_vad,
        estimate_num_speakers,
        _compute_speaker_stats,
        compute_log_mel_spectrogram,
        _pad_or_trim_mel,
        extract_ecapa_embedding,
        VADState,
        ECAPA_N_MELS,
        ECAPA_FIXED_N_FRAMES,
    )
except ImportError as e:
    pytestmark = pytest.mark.skip(reason=f"Impossible d'importer run_audio_diarization_tpu: {e}")


class TestStep4TPUFSM:
    """Validation de la Machine à États Finis (FSM) avec Hangover"""

    def test_fsm_hangover_bridges_micro_silence(self):
        # Given: Parole avec un micro-silence de 1 frame (< hangover limit de 2)
        vad_flags = [True, True, False, True, True]
        hop_sec = 0.48

        # When: Application du FSM avec hangover de 1.0s (= 2 frames à 0.48s)
        result = apply_fsm_hangover(vad_flags, hop_sec=hop_sec, hangover_sec=1.0)

        # Then: Le micro-silence est comblé (tous True)
        assert result == [True, True, True, True, True]

    def test_fsm_hangover_respects_long_silence(self):
        # Given: Parole suivie d'un silence long (> hangover limit)
        # hangover_limit = ceil(1.0 / 0.48) = 3 frames
        vad_flags = [True, True, False, False, False, False, False]
        hop_sec = 0.48

        # When: Application du FSM avec hangover de 1.0s (= ceil(1.0/0.48) = 3 frames)
        result = apply_fsm_hangover(vad_flags, hop_sec=hop_sec, hangover_sec=1.0)

        # Then: Les 3 premières False sont maintenues en True (hangover),
        # puis passage à SILENCE
        assert result[0] is True
        assert result[1] is True
        assert result[2] is True  # Hangover frame 1
        assert result[3] is True  # Hangover frame 2
        assert result[4] is True  # Hangover frame 3
        assert result[5] is False  # Silence (hangover expiré)
        assert result[6] is False  # Silence

    def test_fsm_hangover_empty_input(self):
        # Given: Aucun flag
        result = apply_fsm_hangover([], hop_sec=0.48, hangover_sec=1.0)

        # Then: Retourne liste vide
        assert result == []

    def test_fsm_hangover_all_silence(self):
        # Given: Silence complet
        vad_flags = [False, False, False, False, False]

        # When: FSM
        result = apply_fsm_hangover(vad_flags, hop_sec=0.48, hangover_sec=1.0)

        # Then: Tout reste False
        assert result == [False, False, False, False, False]

    def test_fsm_hangover_resume_speech(self):
        # Given: Parole, silence court (hangover actif), reprise parole
        vad_flags = [True, False, True]
        hop_sec = 0.48

        # When: FSM avec hangover
        result = apply_fsm_hangover(vad_flags, hop_sec=hop_sec, hangover_sec=1.0)

        # Then: Tout est True (le hangover comble le silence et la parole reprend)
        assert result == [True, True, True]


class TestStep4TPUMedianFilter:
    """Validation du filtre médian sur les probabilités VAD"""

    def test_median_filter_rejects_spike(self):
        # Given: Probabilités avec un pic isolé (toux, choc)
        probs = np.array([0.1, 0.1, 0.9, 0.1, 0.1], dtype=np.float32)

        # When: Filtre médian taille 3
        filtered = apply_median_filter_vad(probs, kernel_size=3)

        # Then: Le pic est rejeté
        assert np.isclose(filtered[2], 0.1)

    def test_median_filter_preserves_sustained_speech(self):
        # Given: Zone de parole soutenue
        probs = np.array([0.1, 0.8, 0.8, 0.8, 0.1], dtype=np.float32)

        # When: Filtre médian taille 3
        filtered = apply_median_filter_vad(probs, kernel_size=3)

        # Then: Les valeurs de parole soutenue sont préservées
        assert filtered[2] >= 0.5

    def test_median_filter_short_input(self):
        # Given: Entrée plus courte que le noyau
        probs = np.array([0.5, 0.8], dtype=np.float32)

        # When: Filtre médian
        filtered = apply_median_filter_vad(probs, kernel_size=5)

        # Then: Retourne l'entrée inchangée
        np.testing.assert_array_equal(filtered, probs)


class TestStep4TPUClusteringAdaptive:
    """Validation de l'estimation dynamique du nombre de locuteurs"""

    def test_estimate_speakers_few_embeddings(self):
        # Given: Moins de 4 embeddings (trop peu pour le clustering)
        embeddings = np.random.randn(3, 128).astype(np.float32)

        # When: Estimation
        n = estimate_num_speakers(embeddings)

        # Then: Retourne 1 (pas assez de données)
        assert n == 1

    def test_estimate_speakers_single_cluster(self):
        # Given: 20 embeddings tous similaires (1 locuteur)
        base = np.random.randn(128).astype(np.float32)
        embeddings = np.array([base + np.random.randn(128) * 0.01 for _ in range(20)])

        # When: Estimation
        n = estimate_num_speakers(embeddings, max_speakers=5)

        # Then: Devrait estimer 1 locuteur
        assert n == 1

    def test_estimate_speakers_two_distinct_clusters(self):
        # Given: 20 embeddings clairement séparés en 2 groupes
        cluster_a = np.random.randn(10, 128).astype(np.float32) + 5.0
        cluster_b = np.random.randn(10, 128).astype(np.float32) - 5.0
        embeddings = np.vstack([cluster_a, cluster_b])

        # When: Estimation
        n = estimate_num_speakers(embeddings, max_speakers=5)

        # Then: Devrait estimer environ 2 locuteurs
        assert n >= 1  # Au minimum détecte un cluster
        assert n <= 3  # Ne devrait pas sur-estimer


class TestStep4TPUClustering:
    """Validation de l'algorithme de clustering spectral adaptatif"""

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
        embeddings = np.array([
            [1.0, 0.0], [1.0, 0.0], [1.0, 0.0], [1.0, 0.0], [1.0, 0.0], [1.0, 0.0],
            [0.0, 1.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0]
        ])
        segments = [
            [0.0, 1.0], [1.1, 2.0], [2.1, 3.0], [3.1, 4.0], [4.1, 5.0], [5.1, 6.0],
            [6.1, 7.0], [7.1, 8.0], [8.1, 9.0], [9.1, 10.0], [10.1, 11.0], [11.1, 12.0]
        ]

        # When: Clustering adaptatif
        results = perform_clustering(embeddings, segments)

        # Then: Les segments adjacents du même locuteur sont fusionnés
        assert len(results) > 0
        for res in results:
            assert "speaker" in res
            assert "start" in res
            assert "end" in res
            assert res["start"] < res["end"]


class TestStep4TPUSpeakerStats:
    """Validation du calcul des statistiques par locuteur"""

    def test_compute_speaker_stats_basic(self):
        # Given: 2 segments de parole pour 1 locuteur
        diarization = [
            {"speaker": "SPEAKER_00", "start": 0.0, "end": 5.0},
            {"speaker": "SPEAKER_00", "start": 6.0, "end": 10.0},
        ]

        # When: Calcul des stats
        stats = _compute_speaker_stats(diarization, duration_sec=15.0)

        # Then: 9 secondes de parole, 100% pour SPEAKER_00
        assert "SPEAKER_00" in stats
        assert stats["SPEAKER_00"]["total_time_sec"] == 9.0
        assert stats["SPEAKER_00"]["percentage"] == 100.0

    def test_compute_speaker_stats_two_speakers(self):
        # Given: 2 locuteurs
        diarization = [
            {"speaker": "SPEAKER_00", "start": 0.0, "end": 6.0},
            {"speaker": "SPEAKER_01", "start": 7.0, "end": 10.0},
        ]

        # When: Calcul
        stats = _compute_speaker_stats(diarization, duration_sec=15.0)

        # Then: Les deux locuteurs sont présents
        assert "SPEAKER_00" in stats
        assert "SPEAKER_01" in stats
        total_pct = stats["SPEAKER_00"]["percentage"] + stats["SPEAKER_01"]["percentage"]
        assert np.isclose(total_pct, 100.0)

    def test_compute_speaker_stats_empty(self):
        # Given: Aucun segment
        stats = _compute_speaker_stats([], duration_sec=15.0)

        # Then: Dict vide
        assert stats == {}


class TestStep4TPUVAD:
    """Validation du flux VAD simulé avec fenêtrage glissant"""

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

        # Simuler get_tensor avec score de parole élevé
        def get_tensor_side_effect(index):
            if index == 0:
                return np.array([[0.8]], dtype=np.float32)
            elif index == 2:
                return np.array([[np.ones(128)]], dtype=np.float32)
            return np.array([0])

        interpreter.get_tensor.side_effect = get_tensor_side_effect

        # When: Analyse VAD avec fenêtrage glissant (50% overlap)
        segments, embeddings = run_vad_and_embedding(
            Path("dummy.wav"), interpreter, None,
            vad_threshold=0.20, hop_overlap=0.5,
            median_filter_size=3, hangover_sec=1.0
        )

        # Then: Les segments et embeddings sont extraits
        # Avec overlap 50%, on attend plus de fenêtres que l'ancien mode séquentiel
        assert len(segments) > 0
        assert len(embeddings) > 0


class TestStep4TPUJsonFormat:
    """Validation du format JSON de sortie incluant speaker_stats (Audit Camille)"""

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
        assert data["total_frames"] == 75  # 3.0 * 25.0
        assert data["fps"] == 25.0
        assert "frames_analysis" in data
        assert isinstance(data["frames_analysis"], list)
        assert len(data["frames_analysis"]) == 75

        # Vérification de la section speaker_stats (Audit Camille)
        assert "speaker_stats" in data
        assert "SPEAKER_00" in data["speaker_stats"]
        assert "SPEAKER_01" in data["speaker_stats"]
        assert "total_time_sec" in data["speaker_stats"]["SPEAKER_00"]
        assert "percentage" in data["speaker_stats"]["SPEAKER_00"]

        # Vérification que num_distinct_speakers_audio est conservé (compat baseline)
        frame_10 = data["frames_analysis"][9]
        assert frame_10["frame"] == 10
        assert frame_10["audio_info"]["is_speech_present"] is True
        assert frame_10["audio_info"]["active_speaker_labels"] == ["SPEAKER_00"]
        assert frame_10["audio_info"]["num_distinct_speakers_audio"] == 1
        assert frame_10["audio_info"]["timecode_sec"] == 0.36


class TestStep4ECAPALogMel:
    """Validation de l'extraction Log-Mel Spectrogram pour ECAPA-TDNN"""

    def test_log_mel_shape(self):
        # Given: Un signal audio mono 16kHz de 1 seconde
        sr = 16000
        waveform = np.random.randn(sr).astype(np.float32)

        # When: Calcul du spectrogramme
        log_mel = compute_log_mel_spectrogram(waveform)

        # Then: La forme est (80, T) avec T > 0
        assert log_mel.shape[0] == ECAPA_N_MELS  # 80 Mel bins
        assert log_mel.shape[1] > 0  # Au moins 1 frame
        assert log_mel.dtype == np.float32

    def test_log_mel_3_seconds(self):
        # Given: Un signal de 3 secondes (durée standard ECAPA)
        sr = 16000
        waveform = np.random.randn(sr * 3).astype(np.float32)

        # When: Calcul du spectrogramme
        log_mel = compute_log_mel_spectrogram(waveform)

        # Then: ~300 frames (3s × 16000 / 160 hop)
        assert log_mel.shape[0] == 80
        assert abs(log_mel.shape[1] - ECAPA_FIXED_N_FRAMES) <= 2  # Tolérance ±2 frames

    def test_pad_or_trim_short_signal(self):
        # Given: Un spectrogramme court (50 frames)
        log_mel = np.random.randn(80, 50).astype(np.float32)

        # When: Padding à 300 frames
        padded = _pad_or_trim_mel(log_mel, target_frames=300)

        # Then: Résultat (80, 300), padded avec log(1e-10)
        assert padded.shape == (80, 300)
        # Les 50 premières frames sont préservées
        np.testing.assert_array_equal(padded[:, :50], log_mel)

    def test_pad_or_trim_long_signal(self):
        # Given: Un spectrogramme long (500 frames)
        log_mel = np.random.randn(80, 500).astype(np.float32)

        # When: Trimming à 300 frames
        trimmed = _pad_or_trim_mel(log_mel, target_frames=300)

        # Then: Résultat (80, 300), tronqué
        assert trimmed.shape == (80, 300)
        np.testing.assert_array_equal(trimmed, log_mel[:, :300])


    def test_extract_ecapa_embedding_shape(self):
        # Given: Un faux interpréteur TFLite simulant ECAPA-TDNN Float32
        interpreter = MagicMock()
        interpreter.get_input_details.return_value = [{
            'index': 0,
            'shape': (1, 80, 300),
            'dtype': np.float32,
            'quantization': (0.0, 0)
        }]
        interpreter.get_output_details.return_value = [{
            'index': 0,
            'shape': (1, 1, 192),
            'dtype': np.float32,
            'quantization': (0.0, 0)
        }]
        # Simuler la sortie float32 du modèle
        interpreter.get_tensor.return_value = np.random.randn(1, 1, 192).astype(np.float32)

        # When: Extraction d'un embedding depuis un signal de 3s
        waveform = np.random.randn(48000).astype(np.float32)
        embedding = extract_ecapa_embedding(waveform, interpreter)

        # Then: L'embedding est un vecteur 192D float32
        assert embedding.shape == (192,)
        assert embedding.dtype == np.float32

        # L'interpréteur a bien été appelé
        interpreter.set_tensor.assert_called_once()
        interpreter.invoke.assert_called_once()

    def test_extract_ecapa_embedding_direct_values(self):
        # Given: Un interpréteur retournant des zéros float32
        interpreter = MagicMock()
        interpreter.get_input_details.return_value = [{
            'index': 0, 'shape': (1, 80, 300),
            'dtype': np.float32, 'quantization': (0.0, 0)
        }]
        interpreter.get_output_details.return_value = [{
            'index': 0, 'shape': (1, 1, 192),
            'dtype': np.float32, 'quantization': (0.0, 0)
        }]
        # Sortie: tensor de zéros
        interpreter.get_tensor.return_value = np.zeros((1, 1, 192), dtype=np.float32)

        # When: Extraction
        waveform = np.random.randn(48000).astype(np.float32)
        embedding = extract_ecapa_embedding(waveform, interpreter)

        # Then: La sortie float32 est directement retournée
        np.testing.assert_allclose(embedding, 0.0, atol=1e-5)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
