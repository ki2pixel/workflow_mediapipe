"""
Tests de parsing des logs GPU STEP5.

Objectif : garantir qu'un log worker indique clairement le passage en mode GPU
(`use_gpu=True`) et que l'ONNX Runtime liste bien `CUDAExecutionProvider`.
"""

from pathlib import Path
import re
import textwrap

import pytest


@pytest.fixture
def worker_gpu_log(tmp_path):
    """Crée un log de worker GPU simulant la sortie réelle."""
    content = textwrap.dedent(
        """
        2025-12-22 12:19:43,329 - [INFO] - ONNX Runtime configured: intra_threads=2, inter_threads=1, use_gpu=True
        2025-12-22 12:19:43,329 - [INFO] - FaceMesh ONNX providers active: ['CUDAExecutionProvider', 'CPUExecutionProvider']
        2025-12-22 12:19:45,106 - [INFO] - py-feat blendshape model loaded: ...
        """
    ).strip()
    log_path = tmp_path / "worker_GPU_test.log"
    log_path.write_text(content, encoding="utf-8")
    return log_path


@pytest.fixture
def gpu_log_path(pytestconfig, worker_gpu_log):
    """Retourne le chemin du log (réel via --step5-gpu-log ou fixture simulée)."""
    cli_path = pytestconfig.getoption("step5_gpu_log")
    if cli_path:
        candidate = Path(cli_path).expanduser()
        if not candidate.exists():
            pytest.skip(f"Le log passé en argument n'existe pas: {candidate}")
        return candidate
    return worker_gpu_log


@pytest.fixture
def parse_gpu_log():
    """Fixture utilitaire qui parse un log worker et retourne des indicateurs."""
    use_gpu_regex = re.compile(r"use_gpu\s*=\s*True", re.IGNORECASE)
    cuda_regex = re.compile(r"providers?[\w\s:=\[\]']*CUDAExecutionProvider", re.IGNORECASE)

    def _parse(path: Path):
        text = Path(path).read_text(encoding="utf-8")
        return {
            "raw": text,
            "use_gpu_true": bool(use_gpu_regex.search(text)),
            "cuda_provider": bool(cuda_regex.search(text)),
        }

    return _parse


def test_worker_log_reports_cuda_provider(gpu_log_path, parse_gpu_log):
    """Vérifie qu'un log GPU contient use_gpu=True et CUDAExecutionProvider."""
    result = parse_gpu_log(gpu_log_path)
    assert result["use_gpu_true"], "Le log ne contient pas use_gpu=True"
    assert result["cuda_provider"], "CUDAExecutionProvider absent du log"
