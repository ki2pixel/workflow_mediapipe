"""
Integration tests for /api/system/diagnostics endpoint.
"""

import sys
from pathlib import Path

# Ensure project root on path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app_new import APP_FLASK  # noqa: E402

def test_system_diagnostics_endpoint_status_and_schema():
    app = APP_FLASK
    with app.test_client() as client:
        resp = client.get('/api/system/diagnostics')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)

        # Top-level keys
        for key in ("python", "ffmpeg", "gpu", "config_flags", "timestamp"):
            assert key in data

        # Python info
        py = data["python"]
        assert isinstance(py.get("version", ""), str)
        assert isinstance(py.get("implementation", ""), str)

        # FFmpeg info
        ff = data["ffmpeg"]
        assert "version" in ff

        # GPU info
        gpu = data["gpu"]
        assert "available" in gpu

        # Config flags must not include secrets
        flags = data["config_flags"]
        assert isinstance(flags, dict)
        # Ensure common secret-like keys are not present
        forbidden_keys = {"AIRTABLE_ACCESS_TOKEN", "FLASK_SECRET_KEY", "INTERNAL_WORKER_COMMS_TOKEN", "RENDER_REGISTER_TOKEN"}
        assert forbidden_keys.isdisjoint(set(flags.keys()))
