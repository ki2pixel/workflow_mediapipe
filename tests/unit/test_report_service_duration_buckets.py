import sys
from pathlib import Path
import types
import importlib
import importlib.machinery
import importlib.util
import pytest

# The reporting feature has been removed (backend and frontend). Skip this module.
pytest.skip("reporting feature removed: ReportService no longer exposed via API or UI", allow_module_level=True)

# Define Fake VisualizationService first
class FakeViz:
    @staticmethod
    def get_available_projects():
        return {
            "projects": [
                {
                    "name": "36 Camille",
                    "display_base": "36 Camille",
                    "archive_timestamp": "2025-10-01T12:00:00",
                    "source": "archives",
                    "videos": [
                        "v_short.mp4",   # 90s -> < 2m
                        "v_mid.mp4",     # 180s -> 2-5m
                        "v_long.mp4",    # 360s -> > 5m
                        "v_edge2.mp4",   # 120s -> boundary 2m
                        "v_edge5.mp4",   # 300s -> boundary 5m (inclusive in mid)
                    ],
                }
            ]
        }

    @staticmethod
    def get_project_timeline(project, video):
        # Map names to durations seconds
        mapping = {
            "v_short.mp4": 90,
            "v_mid.mp4": 180,
            "v_long.mp4": 360,
            "v_edge2.mp4": 120,
            "v_edge5.mp4": 300,
        }
        dur = mapping.get(video, 0)
        return {
            "metadata": {
                "duration_seconds": dur,
                "total_frames": int(dur * 25),
                "fps": 25.0,
            },
            "scenes": {"available": False},
            "audio": {"available": False},
            "tracking": {"available": False},
            "archive_probe_source": {
                "metadata": {"provenance": "archives"}
            },
        }


def test_generate_monthly_archive_report_duration_buckets(monkeypatch, tmp_path):
    # Prepare a fake 'services' package to avoid importing heavy deps (flask_caching, etc.)
    fake_services = types.ModuleType("services")
    fake_viz = types.ModuleType("services.visualization_service")
    # Attach FakeViz as VisualizationService
    setattr(fake_viz, "VisualizationService", FakeViz)
    # Register in sys.modules before importing report_service
    sys.modules.setdefault("services", fake_services)
    sys.modules.setdefault("services.visualization_service", fake_viz)

    # Inject a fake config.settings with a minimal `config` object
    fake_config_pkg = types.ModuleType("config")
    fake_settings = types.ModuleType("config.settings")
    class _Cfg:
        pass
    cfg = _Cfg()
    cfg.BASE_PATH_SCRIPTS = tmp_path  # ensure templates are written in tmp
    setattr(fake_settings, "config", cfg)
    sys.modules.setdefault("config", fake_config_pkg)
    sys.modules.setdefault("config.settings", fake_settings)

    # Import report_service module directly from file path to bypass package __init__
    project_root = Path(__file__).resolve().parents[2]
    report_path = project_root / "services" / "report_service.py"
    spec = importlib.util.spec_from_file_location("services.report_service", report_path)
    rs = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(rs)  # type: ignore

    # Execute for October 2025
    result = rs.ReportService.generate_monthly_archive_report("2025-10")

    assert "error" not in result, result.get("error")
    assert result["project_count"] == 1
    assert result["video_count"] == 5

    # Inspect embedded projects context via HTML or recompute via internal structure
    # The HTML is rendered; instead we re-run aggregation inner pieces by calling again and
    # reusing the Jinja context would require refactor. We'll validate via presence of expected strings.
    html = result["html"]

    # Check per-project duration lines are present with correct counts
    # lt_2m: v_short (90s) => 1
    # between_2_5m: v_mid (180s), v_edge2 (120s), v_edge5 (300s) => 3
    # gt_5m: v_long (360s) => 1
    assert "36 Camille" in html
    assert "moins de 2 minutes : 1" in html
    assert "entre 2 et 5 minutes : 3" in html
    assert "plus de 5 minutes : 1" in html
