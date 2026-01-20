import re
from pathlib import Path
from datetime import datetime

import importlib
import importlib.util
import sys

import pytest

# Load ResultsArchiver via absolute path
PROJECT_ROOT = Path(__file__).parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SPEC_PATH = PROJECT_ROOT / 'services' / 'results_archiver.py'
spec = importlib.util.spec_from_file_location("results_archiver", str(SPEC_PATH))
results_archiver = importlib.util.module_from_spec(spec)
# Ensure module is visible to decorators (dataclasses) during exec
sys.modules[spec.name] = results_archiver  # type: ignore
spec.loader.exec_module(results_archiver)  # type: ignore


def test_archive_writes_into_timestamped_project_dir(tmp_path, monkeypatch):
    # Patch config.ARCHIVES_DIR to a temporary directory
    from config.settings import config as app_config
    monkeypatch.setattr(app_config, 'ARCHIVES_DIR', tmp_path)

    base_project = "13 Camille"

    # Create a dummy video file to hash
    video_dir = tmp_path / 'dummy_project'
    video_dir.mkdir(parents=True, exist_ok=True)
    video_path = video_dir / 'video1.mp4'
    video_path.write_bytes(b"fake-video-content")

    # Create dummy analysis files
    scenes = video_dir / 'video1_scenes.csv'
    scenes.write_text('t;scene', encoding='utf-8')
    audio = video_dir / 'video1_audio.json'
    audio.write_text('{"ok":true}', encoding='utf-8')
    tracking = video_dir / 'video1_tracking.json'
    tracking.write_text('{"tracks":[]}', encoding='utf-8')

    # Perform archiving
    out_dir = results_archiver.ResultsArchiver.archive_analysis_files(
        base_project, video_path, scenes_file=scenes, audio_file=audio, tracking_file=tracking
    )
    assert out_dir is not None

    # Verify that a timestamp-suffixed project directory was created
    created_dirs = [d for d in tmp_path.iterdir() if d.is_dir() and d.name.startswith(base_project)]
    assert created_dirs, "No archive project directory created"

    # Expect format: "<base> YYYY-MM-DD_HH-MM-SS"
    pattern = re.compile(r"^" + re.escape(base_project) + r" \d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$")
    assert any(pattern.match(d.name) for d in created_dirs), f"No timestamped dir matched among: {[d.name for d in created_dirs]}"

    # Verify files exist under hash dir
    # Hash dir is out_dir (returned path) and should contain copied files with stem names
    assert (out_dir / 'video1_scenes.csv').exists()
    assert (out_dir / 'video1_audio.json').exists()
    assert (out_dir / 'video1_tracking.json').exists()


def test_find_analysis_file_reads_from_timestamped_archives(tmp_path, monkeypatch):
    # Patch config.ARCHIVES_DIR to a temporary directory
    from config.settings import config as app_config
    monkeypatch.setattr(app_config, 'ARCHIVES_DIR', tmp_path)

    base_project = "18 Camille"

    # Prepare a real video file to compute hash
    projects_area = tmp_path / 'dummy_project'
    projects_area.mkdir(parents=True, exist_ok=True)
    video_path = projects_area / 'clipA.mp4'
    video_path.write_bytes(b"video-bytes-for-hash")

    # Compute the expected video hash using the service itself
    vhash = results_archiver.ResultsArchiver.compute_video_hash(video_path)
    assert vhash is not None

    # Manually create a timestamped archive project dir and place an artifact
    ts_dir = tmp_path / f"{base_project} 2025-10-06_08-11-22"
    hash_dir = ts_dir / vhash
    hash_dir.mkdir(parents=True, exist_ok=True)

    # Place a scenes file with stem name
    scenes_file = hash_dir / 'clipA_scenes.csv'
    scenes_file.write_text('t;scene', encoding='utf-8')

    # Ask the archiver to find that file using the base project name and video path
    found = results_archiver.ResultsArchiver.find_analysis_file(base_project, video_path, results_archiver.SCENES_SUFFIX)
    assert found is not None
    assert found.name == 'clipA_scenes.csv'
