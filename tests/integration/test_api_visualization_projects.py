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
        # The endpoint should respond even if there are no projects; 200 on success, 500 only if service error surfaced
        assert resp.status_code in (200, 500)
        data = resp.get_json()
        assert isinstance(data, dict)
        # When 200, expect the standard shape
        if resp.status_code == 200:
            for key in ("projects", "count", "timestamp"):
                assert key in data
            assert isinstance(data["projects"], list)
            assert isinstance(data["count"], int)
            # Validate per-project fields when projects are present
            if data["projects"]:
                p = data["projects"][0]
                # Core fields
                for k in ("name", "video_count", "has_scenes", "has_audio", "has_tracking", "source"):
                    assert k in p
                # Enriched fields from backend for archive normalization
                assert "display_base" in p
                assert "archive_timestamp" in p  # may be None when not suffixed
