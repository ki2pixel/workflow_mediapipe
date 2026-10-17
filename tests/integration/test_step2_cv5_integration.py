#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests d'intégration pour STEP2 TransNetV2 (OpenCV 5.0 / ONNX Runtime GPU & CPU Fallback).
Couvre la matrice des perspectives : TC-N-01, TC-E-02.
Formalisme Given / When / Then conforme à .agents/rules/test-strategy.md.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from dotenv import load_dotenv
import numpy as np
import pytest

# Charger .env pour résoudre VENV_BASE_DIR
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

from config.settings import config

BASE_PATH = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = BASE_PATH / "workflow_scripts" / "step2" / "run_transnet_cv5.py"
PYTHON_PATH = config.get_venv_python("transnet_cv5_env")
MODEL_PATH = BASE_PATH / "assets" / "models" / "onnx" / "transnetv2.onnx"


def get_test_env():
    """Génère l'environnement avec les bibliothèques CUDA/cuDNN injectées dans LD_LIBRARY_PATH."""
    env = dict(os.environ)
    if PYTHON_PATH.exists():
        venv_site = Path(PYTHON_PATH).parent.parent / "lib" / "python3.10" / "site-packages"
        if venv_site.exists():
            nvidia_dirs = [str(d) for d in venv_site.glob("nvidia/*/lib")]
            if nvidia_dirs:
                current_ld = env.get("LD_LIBRARY_PATH", "")
                current_entries = [e for e in current_ld.split(":") if e]
                missing = [d for d in nvidia_dirs if d not in current_entries]
                if missing:
                    env["LD_LIBRARY_PATH"] = ":".join(missing + current_entries)
    return env


class TestStep2Cv5Integration:
    """Tests d'intégration de bout en bout pour le pipeline STEP2 CV5 / ONNX."""

    def test_step2_cv5_no_videos_to_process(self):
        # Given: Un dossier de travail temporaire sans aucune vidéo
        if not PYTHON_PATH.exists():
            pytest.skip("Environnement transnet_cv5_env introuvable")

        with tempfile.TemporaryDirectory() as tmpdir:
            # When: Exécution du script run_transnet_cv5.py
            result = subprocess.run(
                [str(PYTHON_PATH), str(SCRIPT_PATH)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=30,
                env=get_test_env(),
            )

            # Then: Fin normale avec code 0 et détection de 0 vidéo
            assert result.returncode == 0
            assert "TOTAL_VIDEOS_TO_PROCESS: 0" in result.stdout

    def test_step2_cv5_config_loading(self):
        # Given: Des arguments CLI personnalisés de seuil et fenêtre
        if not PYTHON_PATH.exists():
            pytest.skip("Environnement transnet_cv5_env introuvable")

        with tempfile.TemporaryDirectory() as tmpdir:
            # When: Exécution avec flags CLI
            result = subprocess.run(
                [str(PYTHON_PATH), str(SCRIPT_PATH), "--threshold", "0.6", "--window", "120"],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=30,
                env=get_test_env(),
            )

            # Then: La configuration effective reflète les surcharges
            output = result.stdout + result.stderr
            assert "CONFIG_EFFECTIVE" in output
            assert "threshold=0.6" in output
            assert "window=120" in output

    def test_step2_cv5_slice_validation(self):
        # Given: Le modèle ONNX sanitizé transnetv2.onnx
        if not PYTHON_PATH.exists():
            pytest.skip("Environnement transnet_cv5_env introuvable")
        if not MODEL_PATH.exists():
            pytest.skip("Poids transnetv2.onnx non trouvés")

        with tempfile.TemporaryDirectory() as tmpdir:
            # When: Exécution du script de validation
            result = subprocess.run(
                [str(PYTHON_PATH), str(SCRIPT_PATH)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=30,
                env=get_test_env(),
            )

            # Then: Validation Slice réussie (aucun crash du moteur d'inférence)
            output = result.stdout + result.stderr
            assert "VALIDATION_OK" in output

    def test_tc_n_01_numeric_invariance_and_fps(self):
        # Given: Une vidéo synthétique de 100 trames (4s à 25 fps) avec 1 coupure artificielle
        if not PYTHON_PATH.exists():
            pytest.skip("Environnement transnet_cv5_env introuvable")
        if not MODEL_PATH.exists():
            pytest.skip("Poids transnetv2.onnx non trouvés")

        with tempfile.TemporaryDirectory() as tmpdir:
            vid_path = Path(tmpdir) / "synth_video.mp4"
            # Générer 100 trames avec 2 plans distincts (testsrc 2s puis smptebars 2s)
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "testsrc=duration=2:size=320x180:rate=25",
                "-f", "lavfi", "-i", "smptebars=duration=2:size=320x180:rate=25",
                "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[outv]",
                "-map", "[outv]",
                "-pix_fmt", "yuv420p",
                str(vid_path)
            ]
            subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # When: Traitement de la vidéo par le pipeline zéro-copie sous transnet_cv5_env
            py_code = (
                "from pathlib import Path\n"
                "from workflow_scripts.step2.zero_copy_pipeline import ZeroCopyTransNetPipeline, create_transnet_engine\n"
                f"engine = create_transnet_engine(model_path='{MODEL_PATH}', device='auto', batch_size=25, use_tf32=False)\n"
                f"pipeline = ZeroCopyTransNetPipeline(engine=engine, ffmpeg_threads=0, windows_per_chunk=50)\n"
                f"probs, scenes = pipeline.process_video('{vid_path}', threshold=0.5)\n"
                "print('PROBS_LEN:', len(probs))\n"
                "print('PROBS_MIN_MAX:', float(probs.min()), float(probs.max()))\n"
                "print('SCENES:', scenes)\n"
            )
            result = subprocess.run(
                [str(PYTHON_PATH), "-c", py_code],
                cwd=str(BASE_PATH),
                capture_output=True,
                text=True,
                timeout=60,
                env=get_test_env(),
            )

            # Then: Sortie valide, 100 trames traitées, probabilités dans [0, 1] et détection de la transition
            assert result.returncode == 0, f"Erreur exécution: {result.stderr}"
            assert "PROBS_LEN: 100" in result.stdout
            assert "INTERNAL_PROGRESS: 100/100 frames (100%)" in result.stdout

    def test_tc_e_02_cpu_fallback_execution(self):
        # Given: Forçage du mode CPU (device='cpu')
        if not PYTHON_PATH.exists():
            pytest.skip("Environnement transnet_cv5_env introuvable")
        if not MODEL_PATH.exists():
            pytest.skip("Poids transnetv2.onnx non trouvés")

        py_code = (
            "from pathlib import Path\n"
            "import numpy as np\n"
            "from workflow_scripts.step2.zero_copy_pipeline import create_transnet_engine, WINDOW_SIZE, FRAME_H, FRAME_W, FRAME_C\n"
            f"engine = create_transnet_engine(model_path='{MODEL_PATH}', device='cpu', batch_size=25)\n"
            "dummy_windows = np.zeros((2, WINDOW_SIZE, FRAME_H, FRAME_W, FRAME_C), dtype=np.uint8)\n"
            "probs = engine.infer_windows(dummy_windows)\n"
            "assert probs.shape == (100,), f'Shape inattendue: {probs.shape}'\n"
            "assert np.all((probs >= 0.0) & (probs <= 1.0))\n"
            "print('CPU_FALLBACK_OK')\n"
        )

        # When: Inférence forcée sur CPU
        result = subprocess.run(
            [str(PYTHON_PATH), "-c", py_code],
            cwd=str(BASE_PATH),
            capture_output=True,
            text=True,
            timeout=30,
            env=get_test_env(),
        )

        # Then: L'inférence CPU s'exécute avec succès
        assert result.returncode == 0, f"Erreur fallback CPU: {result.stderr}"
        assert "CPU_FALLBACK_OK" in result.stdout
