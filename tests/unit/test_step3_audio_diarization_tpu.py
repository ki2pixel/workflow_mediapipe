#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests unitaires pour STEP3 (VAD & Diarisation alternatif via Google Coral Edge TPU).

Couvre la FSM Hangover, le filtre médian VAD, le post-filtrage fusionné,
le clustering AHC condensé, l'extraction Log-Mel par lots, les embeddings
ECAPA-TDNN et le contrat JSON aval (STEP4/STEP5/STEP6).
"""

import sys
import pytest
from pathlib import Path
from importlib import util as _import_util
from unittest.mock import MagicMock, patch

if _import_util.find_spec("numpy") is None or _import_util.find_spec("sklearn") is None or _import_util.find_spec("scipy") is None:
    pytestmark = pytest.mark.skip(
        reason="numpy, scikit-learn ou scipy non disponibles dans cet environnement; tests STEP3 TPU ignorés."
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

BASE_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_PATH / "workflow_scripts" / "step3"))

try:
    from run_audio_diarization_tpu import (
        perform_clustering,
        run_vad_and_embedding,
        _write_audio_json_file,
        apply_fsm_hangover,
        apply_median_filter_vad,
        apply_vad_postfilter,
        fused_medfilt5_binarize_hangover_fsm,
        estimate_num_speakers,
        _compute_speaker_stats,
        compute_log_mel_spectrogram,
        compute_log_mel_spectrogram_batch,
        _pad_or_trim_mel,
        extract_ecapa_embedding_batch,
        compute_ahc_labels,
        _assert_edgetpu_delegate_active,
        _get_embedding_stride,
        _nearest_embedding_indices,
        _ecapa_session_batch_size,
        ECAPA_N_MELS,
        ECAPA_FIXED_N_FRAMES,
    )
except ImportError as e:
    pytestmark = pytest.mark.skip(reason=f"Impossible d'importer run_audio_diarization_tpu: {e}")


class TestStep3TPUFSM:
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


class TestStep3TPUMedianFilter:
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


class TestStep3FusedVADPostfilter:
    """Parité entre le noyau fusionné et la chaîne médian + seuil + FSM"""

    def test_fused_matches_legacy_chain(self):
        # Given: Probabilités aléatoires et paramètres de production
        rng = np.random.default_rng(20261017)
        probs = rng.random(4000).astype(np.float32)
        hop_sec = 0.48

        # When: Chaîne historique vs noyau fusionné
        legacy_flags = apply_fsm_hangover(
            [bool(value > 0.20) for value in apply_median_filter_vad(probs, 5)],
            hop_sec=hop_sec,
            hangover_sec=1.0,
        )
        fused_flags = apply_vad_postfilter(probs, 0.20, hop_sec, 1.0, 5)

        # Then: Décisions strictement identiques
        np.testing.assert_array_equal(
            np.asarray(fused_flags, dtype=bool),
            np.asarray(legacy_flags, dtype=bool),
        )

    def test_fused_edge_boundaries(self):
        # Given: Un signal qui commence et finit par du silence
        probs = np.zeros(20, dtype=np.float32)
        probs[5:10] = 0.9

        # When: Post-filtrage fusionné
        fused_flags = np.asarray(
            apply_vad_postfilter(probs, 0.20, 0.48, 1.0, 5), dtype=bool
        )
        legacy_flags = np.asarray(
            apply_fsm_hangover(
                [bool(value > 0.20) for value in apply_median_filter_vad(probs, 5)],
                hop_sec=0.48,
                hangover_sec=1.0,
            ),
            dtype=bool,
        )

        # Then: Même convention de bordure que scipy.signal.medfilt
        np.testing.assert_array_equal(fused_flags, legacy_flags)

    def test_short_input_falls_back_to_legacy_path(self):
        # Given: Moins de 5 probabilités
        probs = np.array([0.9, 0.9, 0.1], dtype=np.float32)

        # When/Then: Le chemin historique est utilisé sans erreur
        result = apply_vad_postfilter(probs, 0.20, 0.48, 1.0, 5)
        assert len(result) == 3

    def test_fused_kernel_exact_threshold(self):
        # Given: Seuil strict (une valeur égale au seuil n'est pas de la parole)
        probs = np.array([0.2] * 9, dtype=np.float32)

        # When: Noyau fusionné
        mask = fused_medfilt5_binarize_hangover_fsm(probs, np.float32(0.2), 3)

        # Then: Aucune frame active
        assert int(mask.sum()) == 0


class TestStep3TPUClusteringAdaptive:
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


class TestStep3AHCClustering:
    """Parité du clustering AHC condensé avec scikit-learn"""

    def test_compute_ahc_labels_matches_sklearn(self):
        from sklearn.cluster import AgglomerativeClustering
        from sklearn.metrics import adjusted_rand_score

        # Given: Trois groupes bien séparés d'embeddings normalisés
        rng = np.random.default_rng(7)
        centers = rng.standard_normal((3, 64)) * 4.0
        embeddings = np.vstack([
            center + rng.standard_normal((25, 64)) for center in centers
        ]).astype(np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        unit_embeddings = embeddings / np.maximum(norms, 1e-12)

        # When: fastcluster/scipy vs scikit-learn
        reference = AgglomerativeClustering(
            n_clusters=None,
            metric="cosine",
            linkage="average",
            distance_threshold=0.32,
        ).fit_predict(unit_embeddings)
        candidate = compute_ahc_labels(unit_embeddings)

        # Then: Partitionnement identique
        assert adjusted_rand_score(reference, candidate) == 1.0

    def test_compute_ahc_labels_edge_cases(self):
        # Given/When/Then: Cas limites sans exception
        assert compute_ahc_labels(np.empty((0, 8), dtype=np.float32)).tolist() == []
        single = np.ones((1, 8), dtype=np.float32)
        assert compute_ahc_labels(single).tolist() == [0]

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

        # When: Clustering
        results = perform_clustering(embeddings, segments)

        # Then: Les segments adjacents du même locuteur sont fusionnés
        assert len(results) > 0
        for result in results:
            assert "speaker" in result
            assert "start" in result
            assert "end" in result
            assert result["start"] < result["end"]

    def test_minor_speaker_reassignment_blas(self):
        # Given: Duo majeur + un cluster mineur proche de SPEAKER_00
        embeddings = np.array([
            [1.0, 0.0], [1.0, 0.0], [1.0, 0.0], [1.0, 0.0],
            [0.0, 1.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0],
            [0.9, 0.1],
        ])
        segments = [
            [0.0, 2.0], [2.1, 4.0], [4.1, 6.0], [6.1, 8.0],
            [8.1, 10.0], [10.1, 12.0], [12.1, 14.0], [14.1, 16.0],
            [16.1, 16.5],
        ]

        # When: Clustering avec réassignation des mineurs
        results = perform_clustering(embeddings, segments)

        # Then: Le cluster mineur est réassigné à SPEAKER_00, sans nouveau label
        assert results[-1]["speaker"] == "SPEAKER_00"
        assert {result["speaker"] for result in results} == {"SPEAKER_00", "SPEAKER_01"}


class TestStep3TPUSpeakerStats:
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


class TestStep3TPUVAD:
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
        with patch("run_audio_diarization_tpu._yamnet_interp", interpreter):
            segments, embeddings = run_vad_and_embedding(
                Path("dummy.wav"), None,
                vad_threshold=0.20, hop_overlap=0.5,
                median_filter_size=5, hangover_sec=1.0
            )

        # Then: Les segments et embeddings sont extraits
        assert len(segments) > 0
        assert embeddings.shape[0] == len(segments)
        assert interpreter.invoke.call_count >= len(segments)


class TestStep3EmbeddingStride:
    """Validation de la réduction du coût ECAPA par stride temporel"""

    def test_nearest_embedding_mapping(self):
        # Given: Fenêtres toutes les 100 ms, embeddings sélectionnés toutes les 200 ms
        all_times = [0, 100, 200, 300, 400]
        selected_times = [0, 200, 400]

        # When: Association au plus proche
        mapping = _nearest_embedding_indices(all_times, selected_times)

        # Then: Les égalités sont résolues vers la gauche
        assert mapping.tolist() == [0, 0, 1, 1, 2]

    def test_embedding_stride_env_validation(self, monkeypatch):
        # Given/When/Then: Valeur valide ou repli à 1
        monkeypatch.setenv("STEP3_EMBEDDING_STRIDE", "4")
        assert _get_embedding_stride() == 4
        monkeypatch.setenv("STEP3_EMBEDDING_STRIDE", "invalid")
        assert _get_embedding_stride() == 1

    def test_ecapa_batch_size_depends_on_provider(self):
        # Given: Sessions CPU et OpenVINO
        cpu_session = MagicMock()
        cpu_session.get_providers.return_value = ["CPUExecutionProvider"]
        openvino_session = MagicMock()
        openvino_session.get_providers.return_value = [
            "OpenVINOExecutionProvider", "CPUExecutionProvider"
        ]

        # When/Then: Le batch OpenVINO est réduit pour maximiser le débit
        assert _ecapa_session_batch_size(cpu_session) == 32
        assert _ecapa_session_batch_size(openvino_session) == 8

    @patch("run_audio_diarization_tpu.wavfile.read")
    def test_run_vad_and_embedding_stride_replicates(self, mock_wavfile_read, tmp_path, monkeypatch):
        # Given: 5 fenêtres de parole, un stride de 2 et des embeddings identifiables
        sr = 16000
        mock_wavfile_read.return_value = (sr, np.zeros(sr * 3, dtype=np.int16))

        interpreter = MagicMock()
        interpreter.get_input_details.return_value = [{
            'shape': (15360,), 'dtype': np.int16, 'index': 0, 'quantization': (1.0, 0)
        }]
        interpreter.get_output_details.return_value = [
            {'index': 0, 'dtype': np.float32, 'quantization': (1.0, 0)},
            {'index': 1, 'dtype': np.float32, 'quantization': (1.0, 0)},
            {'index': 2, 'dtype': np.float32, 'quantization': (1.0, 0)},
        ]
        interpreter.get_tensor.side_effect = lambda index: (
            np.array([[0.8]], dtype=np.float32) if index == 0 else np.zeros((1, 128), dtype=np.float32)
        )

        model_path = tmp_path / "ecapa_dummy.onnx"
        model_path.write_bytes(b"dummy")
        counter = {"value": 0}

        def fake_batch(waveforms, model):
            start = counter["value"]
            counter["value"] += len(waveforms)
            ids = np.arange(start, start + len(waveforms), dtype=np.float32)
            return np.repeat(ids[:, None], 192, axis=1)

        monkeypatch.setenv("STEP3_EMBEDDING_STRIDE", "2")

        # When: Extraction avec sous-échantillonnage
        with patch("run_audio_diarization_tpu._yamnet_interp", interpreter), \
             patch("run_audio_diarization_tpu.get_extractor_model_cached", return_value=MagicMock()), \
             patch("run_audio_diarization_tpu.extract_ecapa_embedding_batch", side_effect=fake_batch):
            segments, embeddings = run_vad_and_embedding(
                Path("dummy.wav"), model_path,
                vad_threshold=0.20, hop_overlap=0.5,
                median_filter_size=5, hangover_sec=1.0,
            )

        # Then: Un embedding par fenêtre, répliqué depuis le plus proche
        assert len(segments) == 5
        assert embeddings.shape == (5, 192)
        np.testing.assert_array_equal(embeddings[0], embeddings[1])
        np.testing.assert_array_equal(embeddings[2], embeddings[3])
        assert embeddings[4, 0] != embeddings[2, 0]
        assert counter["value"] == 3


class TestStep3TPUJsonFormat:
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


class TestStep3ECAPALogMel:
    """Validation de l'extraction Log-Mel et des embeddings ECAPA-TDNN"""

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

    def test_batch_matches_legacy_pipeline(self):
        # Given: Un segment 3s et la chaîne historique de référence
        rng = np.random.default_rng(42)
        waveform = (rng.standard_normal(48000) * 0.1).astype(np.float32)
        legacy = compute_log_mel_spectrogram(waveform)
        legacy = _pad_or_trim_mel(legacy)
        legacy = legacy - np.mean(legacy, axis=1, keepdims=True)

        # When: Extraction vectorisée par lots
        batched = compute_log_mel_spectrogram_batch(waveform[np.newaxis, :])[0]

        # Then: Équivalence numérique stricte (< 1e-6)
        assert batched.shape == (ECAPA_N_MELS, ECAPA_FIXED_N_FRAMES)
        assert float(np.max(np.abs(batched - legacy.astype(np.float32)))) < 1e-6

    def test_batch_rows_are_independent(self):
        # Given: Deux segments distincts
        rng = np.random.default_rng(43)
        waveforms = (rng.standard_normal((2, 48000)) * 0.1).astype(np.float32)

        # When: Extraction groupée vs individuelle
        batched = compute_log_mel_spectrogram_batch(waveforms)
        singles = np.stack([
            compute_log_mel_spectrogram_batch(waveform[np.newaxis, :])[0]
            for waveform in waveforms
        ])

        # Then: Chaque ligne du lot est indépendante
        np.testing.assert_array_equal(batched, singles)

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

    def test_extract_ecapa_embedding_batch_shape(self):
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
        interpreter.get_tensor.return_value = np.random.randn(1, 1, 192).astype(np.float32)

        # When: Extraction de deux embeddings
        waveforms = [
            np.random.randn(48000).astype(np.float32),
            np.random.randn(48000).astype(np.float32),
        ]
        embeddings = extract_ecapa_embedding_batch(waveforms, interpreter)

        # Then: Deux vecteurs 192D float32, une invocation par segment
        assert embeddings.shape == (2, 192)
        assert embeddings.dtype == np.float32
        assert interpreter.invoke.call_count == 2

    def test_extract_ecapa_embedding_batch_empty(self):
        # Given: Aucun segment
        embeddings = extract_ecapa_embedding_batch([], MagicMock())

        # Then: Tableau vide (0, 192)
        assert embeddings.shape == (0, 192)


class TestStep3EdgeTPUGuard:
    """Validation de l'assertion anti-fallback XNNPACK"""

    def test_uncompiled_model_is_reported_without_exit(self, tmp_path):
        # Given: Un modèle non compilé pour l'Edge TPU
        model_path = tmp_path / "yamnet_quantized.tflite"
        model_path.write_bytes(b"plain-tflite-model")

        # When/Then: Le repli CPU est signalé mais le pipeline continue
        _assert_edgetpu_delegate_active(MagicMock(), model_path)

    def test_uncompiled_model_fails_in_strict_mode(self, tmp_path, monkeypatch):
        # Given: Mode strict activé
        model_path = tmp_path / "yamnet_quantized.tflite"
        model_path.write_bytes(b"plain-tflite-model")
        monkeypatch.setenv("STEP3_REQUIRE_EDGETPU", "1")

        # When/Then: L'initialisation échoue explicitement
        with pytest.raises(SystemExit):
            _assert_edgetpu_delegate_active(MagicMock(), model_path)

    def test_compiled_model_without_delegate_fails_in_strict_mode(self, tmp_path, monkeypatch):
        # Given: Un flatbuffer compilé mais aucun sous-graphe délégué
        model_path = tmp_path / "yamnet_compiled.tflite"
        model_path.write_bytes(b"edgetpu-custom-op")
        interpreter = MagicMock()
        interpreter._get_ops_details.return_value = [{"op_name": "CONV_2D"}]
        monkeypatch.setenv("STEP3_REQUIRE_EDGETPU", "1")

        # When/Then: L'initialisation échoue explicitement
        with pytest.raises(SystemExit):
            _assert_edgetpu_delegate_active(interpreter, model_path)

    def test_compiled_model_with_delegate_accepted(self, tmp_path):
        # Given: Un modèle compilé et des sous-graphes délégués
        model_path = tmp_path / "yamnet_compiled.tflite"
        model_path.write_bytes(b"edgetpu-custom-op")
        interpreter = MagicMock()
        interpreter._get_ops_details.return_value = [
            {"op_name": "DELEGATE"},
            {"op_name": "DELEGATE"},
        ]

        # When/Then: Aucune exception n'est levée
        _assert_edgetpu_delegate_active(interpreter, model_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
