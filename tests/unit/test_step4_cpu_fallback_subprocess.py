#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import importlib.util
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import patch


def _load_step4_script_module(monkeypatch):
    script_path = (
        Path(__file__).resolve().parents[2]
        / "workflow_scripts"
        / "step4"
        / "run_audio_analysis.py"
    )

    if "torch" not in sys.modules:
        fake_torch = types.SimpleNamespace()
        fake_torch.cuda = types.SimpleNamespace(
            is_available=lambda: False,
            empty_cache=lambda: None,
        )
        monkeypatch.setitem(sys.modules, "torch", fake_torch)

    spec = importlib.util.spec_from_file_location("run_audio_analysis", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestStep4CpuFallbackSubprocess:
    def test_cpu_fallback_subprocess_disables_cuda(self, tmp_path, monkeypatch):
        module = _load_step4_script_module(monkeypatch)
        module.LOG_DIR_PATH = tmp_path

        with patch.object(module.subprocess, "run") as mock_run:
            module._run_cpu_diarization_subprocess(
                wav_path=Path("/tmp/input.wav"),
                output_segments_json=Path("/tmp/out.json"),
                hf_token="hf_test_token",
            )

        assert mock_run.call_count == 1
        call_args, call_kwargs = mock_run.call_args

        cmd = call_args[0]
        env = call_kwargs["env"]

        assert env["AUDIO_DISABLE_GPU"] == "1"
        assert env["CUDA_VISIBLE_DEVICES"] == ""
        assert env["HUGGINGFACE_HUB_TOKEN"] == "hf_test_token"
        assert "--cpu_diarize_wav" in cmd
        assert "--cpu_diarize_out" in cmd
        assert "--hf_auth_token" not in cmd
        assert call_kwargs["stdout"] == subprocess.DEVNULL
        assert call_kwargs["stderr"] == subprocess.PIPE
        assert call_kwargs["check"] is True
        assert call_kwargs["text"] is True
