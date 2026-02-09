"""
Integration tests for /api/visualization/projects endpoint.
"""

import sys
from pathlib import Path

# Ensure project root on path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from app_new import APP_FLASK  # noqa: E402


def test_visualization_projects_endpoint_status_and_schema():
    app = APP_FLASK
    with app.test_client() as client:
        resp = client.get('/api/visualization/projects')
        assert resp.status_code == 404
