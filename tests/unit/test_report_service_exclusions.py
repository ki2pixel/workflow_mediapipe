import sys
from pathlib import Path
import types
import importlib.util
import pytest

# The reporting feature has been removed (backend and frontend). Skip this module.
pytest.skip("reporting feature removed: ReportService and report endpoints removed", allow_module_level=True)

# Fake VisualizationService providing an archived project with excluded filenames present
class FakeViz:
    @staticmethod
    def get_available_projects():
        return {
            "projects": [
                {
                    "name": "49 Camille",
                    "display_base": "49 Camille",
                    "archive_timestamp": "2025-11-01T10:00:00",
                    "source": "archives",
                    "videos": [
                        "valid_a.mp4",      # 90s
                        "m6+.mov",          # should be excluded
                        "BOUCLE BUG 9-16.mov",  # should be excluded
                        "valid_b.mp4",      # 360s
                    ],
                }
            ]
        }

    @staticmethod
    def get_project_timeline(project, video):
        # Provide durations for valid files only; excluded ones will never be queried
        mapping = {
            "valid_a.mp4": 90,
            "valid_b.mp4": 360,
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


def test_generate_monthly_archive_report_excludes_false_positives(monkeypatch, tmp_path):
    # Prepare fake 'services' and inject FakeViz
    fake_services = types.ModuleType("services")
    fake_viz = types.ModuleType("services.visualization_service")
    setattr(fake_viz, "VisualizationService", FakeViz)
    sys.modules.setdefault("services", fake_services)
    sys.modules.setdefault("services.visualization_service", fake_viz)

    # Inject minimal config.settings.config
    fake_config_pkg = types.ModuleType("config")
    fake_settings = types.ModuleType("config.settings")

    class _Cfg:
        pass

    cfg = _Cfg()
    cfg.BASE_PATH_SCRIPTS = tmp_path
    setattr(fake_settings, "config", cfg)
    sys.modules.setdefault("config", fake_config_pkg)
    sys.modules.setdefault("config.settings", fake_settings)

    # Import report_service directly
    project_root = Path(__file__).resolve().parents[2]
    rs_path = project_root / "services" / "report_service.py"
    spec = importlib.util.spec_from_file_location("services.report_service", rs_path)
    rs = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(rs)  # type: ignore

    result = rs.ReportService.generate_monthly_archive_report("2025-11")

    assert "error" not in result, result.get("error")
    # Only 2 valid videos should be counted (excluded ones removed)
    assert result["project_count"] == 1
    assert result["video_count"] == 2

    html = result["html"]
    # Ensure excluded names do not appear in the rendered HTML context (indirectly via counts)
    assert "49 Camille" in html
    assert "Vidéos</th>" in html or "Vidéos" in html
    # Check duration distribution corresponds to two valid videos: 90s (<2m)=1, 360s (>5m)=1, mid=0
    assert "moins de 2 minutes : 1" in html
    assert "entre 2 et 5 minutes : 0" in html
    assert "plus de 5 minutes : 1" in html
