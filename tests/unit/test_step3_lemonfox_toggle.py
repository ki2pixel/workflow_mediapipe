"""Unit test for STEP3 (audio) Lemonfox toggle in WorkflowCommandsConfig."""

from config.workflow_commands import WorkflowCommandsConfig
from config.settings import config


def test_step3_command_uses_original_script_when_toggle_disabled(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_CORAL_TPU_ACCELERATION", False, raising=False)
    monkeypatch.setattr(config, "STEP3_METHOD", "", raising=False)
    monkeypatch.setattr(config, "STEP3_USE_LEMONFOX", False)
    cfg = WorkflowCommandsConfig()
    step3 = cfg.get_step_config("STEP3")
    assert step3 is not None
    cmd = step3["cmd"]
    assert any(str(p).endswith("workflow_scripts/step3/run_audio_analysis.py") for p in cmd)


def test_step3_command_uses_lemonfox_wrapper_when_toggle_enabled(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_CORAL_TPU_ACCELERATION", False, raising=False)
    monkeypatch.setattr(config, "STEP3_METHOD", "", raising=False)
    monkeypatch.setattr(config, "STEP3_USE_LEMONFOX", True)
    cfg = WorkflowCommandsConfig()
    step3 = cfg.get_step_config("STEP3")
    assert step3 is not None
    cmd = step3["cmd"]
    assert any(str(p).endswith("workflow_scripts/step3/run_audio_analysis_lemonfox.py") for p in cmd)


def test_step3_method_deepinfra_has_priority_over_legacy_toggle(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_CORAL_TPU_ACCELERATION", False, raising=False)
    monkeypatch.setattr(config, "STEP3_METHOD", "deepinfra", raising=False)
    monkeypatch.setattr(config, "STEP3_USE_LEMONFOX", True, raising=False)

    cfg = WorkflowCommandsConfig()
    step3 = cfg.get_step_config("STEP3")
    assert step3 is not None
    cmd = step3["cmd"]
    assert any(str(p).endswith("workflow_scripts/step3/run_audio_analysis_deepinfra.py") for p in cmd)


def test_step3_method_invalid_falls_back_to_legacy_toggle(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_CORAL_TPU_ACCELERATION", False, raising=False)
    monkeypatch.setattr(config, "STEP3_METHOD", "invalid_method", raising=False)
    monkeypatch.setattr(config, "STEP3_USE_LEMONFOX", True, raising=False)

    cfg = WorkflowCommandsConfig()
    step3 = cfg.get_step_config("STEP3")
    assert step3 is not None
    cmd = step3["cmd"]
    assert any(str(p).endswith("workflow_scripts/step3/run_audio_analysis_lemonfox.py") for p in cmd)


def test_step3_method_pyannote_has_priority_over_legacy_toggle(monkeypatch):
    monkeypatch.setattr(config, "ENABLE_CORAL_TPU_ACCELERATION", False, raising=False)
    monkeypatch.setattr(config, "STEP3_METHOD", "pyannote", raising=False)
    monkeypatch.setattr(config, "STEP3_USE_LEMONFOX", True, raising=False)

    cfg = WorkflowCommandsConfig()
    step3 = cfg.get_step_config("STEP3")
    assert step3 is not None
    cmd = step3["cmd"]
    assert any(str(p).endswith("workflow_scripts/step3/run_audio_analysis.py") for p in cmd)
