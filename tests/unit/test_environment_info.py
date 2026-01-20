"""
Unit tests for MonitoringService.get_environment_info()
"""

import sys
from pathlib import Path

# Ensure project root on path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.monitoring_service import MonitoringService  # noqa: E402

def test_get_environment_info_structure_and_safety():
    info = MonitoringService.get_environment_info()
    assert isinstance(info, dict)
    for key in ("python", "ffmpeg", "gpu", "config_flags", "timestamp"):
        assert key in info

    py = info["python"]
    assert isinstance(py.get("version", ""), str)
    assert isinstance(py.get("implementation", ""), str)

    ff = info["ffmpeg"]
    assert "version" in ff

    gpu = info["gpu"]
    assert "available" in gpu

    flags = info["config_flags"]
    assert isinstance(flags, dict)
    forbidden_keys = {"AIRTABLE_ACCESS_TOKEN", "FLASK_SECRET_KEY", "INTERNAL_WORKER_COMMS_TOKEN", "RENDER_REGISTER_TOKEN"}
    assert forbidden_keys.isdisjoint(set(flags.keys()))
