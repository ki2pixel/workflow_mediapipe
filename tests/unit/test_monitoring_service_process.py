"""
Unit tests for MonitoringService.get_process_info
"""

import sys
from pathlib import Path

# Ensure project root on path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.monitoring_service import MonitoringService  # noqa: E402


def test_get_process_info_fields():
    info = MonitoringService.get_process_info()
    assert isinstance(info, dict)

    # Required keys
    for key in ("pid", "cpu_percent", "memory_mb", "threads", "uptime_seconds"):
        assert key in info

    # Types and value ranges
    assert isinstance(info["pid"], int)
    assert isinstance(info["cpu_percent"], (int, float))
    assert isinstance(info["memory_mb"], (int, float))
    assert isinstance(info["threads"], int)
    assert isinstance(info["uptime_seconds"], (int, float))

    # Sanity checks
    assert info["pid"] >= 0
    assert info["cpu_percent"] >= 0
    assert info["memory_mb"] >= 0
    assert info["threads"] >= 0
    assert info["uptime_seconds"] >= 0
