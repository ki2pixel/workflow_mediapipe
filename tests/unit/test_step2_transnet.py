#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests unitaires pour STEP2 (TransNetV2 Scene Detection)
Couvre la matrice des perspectives : TC-N-01, TC-B-01, TC-B-02, TC-B-03, TC-E-01.
Formalisme Given / When / Then conforme à .agents/rules/test-strategy.md.
"""

import io
import re
import sys
import csv
import json
import tempfile
from pathlib import Path
from importlib import util as _import_util

import numpy as np
import pytest

BASE_PATH = Path(__file__).resolve().parent.parent.parent
STEP2_DIR = BASE_PATH / "workflow_scripts" / "step2"
if str(STEP2_DIR) not in sys.path:
    sys.path.insert(0, str(STEP2_DIR))

from zero_copy_pipeline import (
    FRAME_H,
    FRAME_W,
    FRAME_C,
    FRAME_BYTES,
    WINDOW_SIZE,
    WINDOW_STRIDE,
    PADDING_LEFT,
    ZeroCopyTransNetPipeline,
    extract_windows_chunked_zero_copy,
    build_reference_windows_global_pad,
    predictions_to_scenes,
    write_scenes_to_csv,
)


class TestZeroCopyIngestion:
    """Tests unitaires pour l'ingestion asynchrone zéro-copie et sliding_window_view."""

    @pytest.mark.parametrize("n_frames", [2501, 2510, 2524, 2525, 2526])
    def test_tc_b_01_boundary_2501_to_2524_no_overflow(self, n_frames: int):
        # Given: Une séquence de trames brutes dans l'intervalle critique [2501, 2524] ou adjacent
        rng = np.random.default_rng(42)
        raw_frames = rng.integers(0, 256, (n_frames, FRAME_H, FRAME_W, FRAME_C), dtype=np.uint8)

        # When: Découpage par double-tampon (capacité 2600 trames) et padding in-place
        windows_zero_copy = extract_windows_chunked_zero_copy(raw_frames, windows_per_chunk=50)
        windows_ref = build_reference_windows_global_pad(raw_frames)

        # Then: Aucune erreur d'index ni débordement de mémoire, parité bit-à-bit stricte
        assert windows_zero_copy.shape == windows_ref.shape
        np.testing.assert_array_equal(windows_zero_copy, windows_ref)

    @pytest.mark.parametrize("n_frames", [1, 25, 49, 50, 99, 100])
    def test_tc_b_02_ultra_short_sequences(self, n_frames: int):
        # Given: Des séquences ultra-courtes inférieures ou égales à la taille d'une fenêtre
        rng = np.random.default_rng(123)
        raw_frames = rng.integers(0, 256, (n_frames, FRAME_H, FRAME_W, FRAME_C), dtype=np.uint8)

        # When: Extraction des fenêtres zéro-copie avec padding des bords
        windows_zero_copy = extract_windows_chunked_zero_copy(raw_frames, windows_per_chunk=50)
        windows_ref = build_reference_windows_global_pad(raw_frames)

        # Then: Fenêtres valides [K, 100, 27, 48, 3] identiques à la référence globale
        assert windows_zero_copy.shape == windows_ref.shape
        assert windows_zero_copy.shape[1:] == (WINDOW_SIZE, FRAME_H, FRAME_W, FRAME_C)
        np.testing.assert_array_equal(windows_zero_copy, windows_ref)

    def test_tc_b_03_timecode_millisecond_format(self):
        # Given: Une liste de scènes arbitraires à cadencement 25.0 fps
        scenes = [[0, 24], [25, 74], [75, 124]]
        timecode_regex = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3}$")
        smpte_frame_regex = re.compile(r"^\d{2}:\d{2}:\d{2}:\d{2}$")

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "scenes_test.csv"

            # When: Écriture du fichier CSV des scènes
            write_scenes_to_csv(scenes, csv_path, fps=25.0)

            # Then: Le format timecode est strictement HH:MM:SS.mmm (rejet de HH:MM:SS:FF)
            assert csv_path.exists()
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            assert len(rows) == len(scenes)
            for row in rows:
                tc_in = row["Timecode In"]
                tc_out = row["Timecode Out"]
                assert timecode_regex.match(tc_in) is not None, f"Format invalide: {tc_in}"
                assert timecode_regex.match(tc_out) is not None, f"Format invalide: {tc_out}"
                assert smpte_frame_regex.match(tc_in) is None, f"Format SMPTE non autorisé: {tc_in}"
                assert smpte_frame_regex.match(tc_out) is None, f"Format SMPTE non autorisé: {tc_out}"

    def test_tc_e_01_truncated_stream_handling(self):
        # Given: Un flux binaire corrompu / tronqué ne respectant pas les frontières de trames
        pipeline = ZeroCopyTransNetPipeline(ffmpeg_threads=0)
        truncated_bytes = b"\x00" * (FRAME_BYTES // 2)
        stream = io.BytesIO(truncated_bytes)
        target_buf = bytearray(FRAME_BYTES)
        mv = memoryview(target_buf)

        # When: Lecture exacte dans le buffer via _read_exact_into
        bytes_read = pipeline._read_exact_into(stream, mv)

        # Then: Le nombre d'octets lus reflète la coupure (détecté comme trame incomplète)
        assert bytes_read == len(truncated_bytes)
        assert bytes_read % FRAME_BYTES != 0

    def test_empty_input_handling(self):
        # Given: Un tableau de trames vide (0 trames)
        raw_frames = np.empty((0, FRAME_H, FRAME_W, FRAME_C), dtype=np.uint8)

        # When: Extraction des fenêtres
        windows_zero_copy = extract_windows_chunked_zero_copy(raw_frames)
        windows_ref = build_reference_windows_global_pad(raw_frames)

        # Then: Retourne un tableau vide sans lever d'exception
        assert len(windows_zero_copy) == 0
        assert len(windows_ref) == 0

    @pytest.mark.parametrize(
        "preds, expected",
        [
            (np.array([], dtype=np.float32), []),
            (np.array([0.1, 0.2, 0.3], dtype=np.float32), [[0, 2]]),
            (np.array([0.1, 0.8, 0.2], dtype=np.float32), [[0, 1], [2, 2]]),
            (np.array([0.9, 0.9, 0.9], dtype=np.float32), [[0, 0], [1, 1], [2, 2]]),
        ],
    )
    def test_predictions_to_scenes_edge_cases(self, preds: np.ndarray, expected: list):
        # Given: Différents profils de probabilités de coupure
        # When: Conversion en segments de scènes
        result = predictions_to_scenes(preds, threshold=0.5)

        # Then: Les segments correspondent exactement aux transitions attendues
        assert result == expected


class TestDeviceSelection:
    """Tests pour la sélection de device (CPU/CUDA)."""

    def test_cpu_always_available(self):
        # Given: Un environnement Python standard
        # When: Sélection du device CPU
        import torch
        device = torch.device("cpu")

        # Then: Le device CPU est toujours disponible
        assert device.type == "cpu"

    def test_cuda_availability_check(self):
        # Given: La détection matérielle CUDA
        # When: Vérification de torch.cuda.is_available()
        import torch
        if torch.cuda.is_available():
            device = torch.device("cuda")
            assert device.type == "cuda"
        else:
            device = torch.device("cpu")
            assert device.type == "cpu"


class TestConfigParsing:
    """Tests pour le parsing de configuration."""

    def test_step2_transnet_json_values(self):
        # Given: Le fichier de configuration config/step2_transnet.json
        config_path = BASE_PATH / "config" / "step2_transnet.json"
        assert config_path.exists()

        # When: Chargement du JSON
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        # Then: Les hyperparamètres optimisés zéro-copie sont configurés
        assert cfg.get("threshold") == 0.5
        assert cfg.get("window") == 100
        assert cfg.get("stride") == 50
        assert cfg.get("padding") == 25
        assert cfg.get("ffmpeg_threads") == 0
        assert cfg.get("onnx_batch_size") in (8, 25)
        assert cfg.get("windows_per_chunk") in (8, 50)
        assert cfg.get("use_tf32") is False


_has_transnetv2_pytorch = _import_util.find_spec("transnetv2_pytorch") is not None


@pytest.mark.skipif(
    not _has_transnetv2_pytorch,
    reason="transnetv2_pytorch non disponible dans cet environnement",
)
class TestTransNetV2PyTorchModel:
    """Tests pour le modèle TransNetV2 PyTorch (actif seulement sous transnet_env)."""

    def test_input_validation_correct_shape(self):
        # Given: Modèle TransNetV2 PyTorch et tenseur valide [1, 100, 27, 48, 3]
        import torch
        from transnetv2_pytorch import TransNetV2
        model = TransNetV2().eval()
        valid_input = torch.randint(0, 256, (1, 100, 27, 48, 3), dtype=torch.uint8)

        # When: Inférence
        with torch.no_grad():
            output = model(valid_input)

        # Then: Sortie valide
        assert output is not None

    def test_input_validation_wrong_dtype(self):
        # Given: Tenseur avec mauvais dtype (int64)
        import torch
        from transnetv2_pytorch import TransNetV2
        model = TransNetV2().eval()
        invalid_input = torch.randint(0, 256, (1, 100, 27, 48, 3), dtype=torch.int64)

        # When/Then: TypeError attendu
        with pytest.raises(TypeError, match="Expected dtype torch.uint8, float32 or float16"):
            model(invalid_input)

    def test_color_histograms_validation(self):
        # Given: Tenseur valide [1, 100, 27, 48, 3]
        import torch
        from transnetv2_pytorch import ColorHistograms
        frames = torch.randint(0, 256, (1, 100, 27, 48, 3), dtype=torch.uint8)

        # When: Calcul histogrammes
        histograms = ColorHistograms.compute_color_histograms(frames)

        # Then: Forme [1, 100, 512]
        assert histograms.shape == (1, 100, 512)
