"""
Integration tests for /api/system_monitor endpoint.
"""

import sys
from pathlib import Path

# Ensure project root on path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app_new import APP_FLASK  # noqa: E402


def test_system_monitor_endpoint_status_and_schema():
    app = APP_FLASK
    with app.test_client() as client:
        resp = client.get('/api/system_monitor')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)

        # Expected top-level keys
        for key in ("cpu_percent", "memory", "disk", "timestamp"):
            assert key in data

        # Memory structure
        mem = data.get("memory", {})
        assert "percent" in mem
        assert "used_gb" in mem
        assert "total_gb" in mem

        # Disk structure
        disk = data.get("disk", {})
        assert "percent" in disk
        assert "used_gb" in disk
        assert "total_gb" in disk
