import os
from pathlib import Path
from datetime import datetime
import re

import pytest

# Import the module under test via absolute path
import importlib.util
import sys
from types import SimpleNamespace

SPEC_PATH = Path(__file__).parents[2] / 'workflow_scripts' / 'step1' / 'extract_archives.py'

# Inject a minimal dummy 'rarfile' module to satisfy imports without requiring the real package
if 'rarfile' not in sys.modules:
    class _DummyRarFile:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def infolist(self):
            return []
        def open(self, *args, **kwargs):
            raise FileNotFoundError

    sys.modules['rarfile'] = SimpleNamespace(
        RarFile=_DummyRarFile,
        BadRarFile=Exception,
    )

spec = importlib.util.spec_from_file_location("extract_archives", str(SPEC_PATH))
extract_archives = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extract_archives)  # type: ignore


def test_format_timestamp_fixed_datetime():
    fixed = datetime(2025, 10, 6, 7, 51, 55)
    ts = extract_archives._format_timestamp(fixed)
    assert ts == "2025-10-06_07-51-55"
    assert re.match(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}$", ts)


def test_compute_unique_project_dir_no_collision(tmp_path):
    base_name = "13 Camille"
    fixed = datetime(2025, 10, 6, 7, 51, 55)
    result = extract_archives.compute_unique_project_dir(base_name, tmp_path, now=fixed)
    # Sans collision, l'horodatage ne doit pas être ajouté
    assert result == tmp_path / "13 Camille"


def test_compute_unique_project_dir_with_collision(tmp_path):
    base_name = "13 Camille"
    fixed = datetime(2025, 10, 6, 7, 51, 55)

    # 1. Simuler l'existence du dossier de base (collision simple)
    base_dir = tmp_path / "13 Camille"
    base_dir.mkdir(parents=True, exist_ok=True)

    result_ts = extract_archives.compute_unique_project_dir(base_name, tmp_path, now=fixed)
    assert result_ts == tmp_path / "13 Camille 2025-10-06_07-51-55"

    # 2. Simuler l'existence du dossier de base ET du dossier horodaté (ultra-collision)
    first_ts = tmp_path / "13 Camille 2025-10-06_07-51-55"
    first_ts.mkdir(parents=True, exist_ok=True)

    result_counter = extract_archives.compute_unique_project_dir(base_name, tmp_path, now=fixed)
    assert result_counter == tmp_path / "13 Camille 2025-10-06_07-51-55-2"


def test_integration_extract_archive_uses_unique_name(tmp_path, monkeypatch):
    # Create a fake archive path
    fake_archive = tmp_path / "13_Camille_dataset.zip"
    fake_archive.write_bytes(b"dummy")

    # Patch secure extract functions to avoid real extraction and simply create a temp file
    def fake_secure_zip(src, dest, sanitizer):
        # Simulate that extraction created a file 'a.txt'
        (dest / "a.txt").parent.mkdir(parents=True, exist_ok=True)
        (dest / "a.txt").write_text("ok", encoding="utf-8")
        return True, 0

    monkeypatch.setattr(extract_archives, "secure_extract_zip", fake_secure_zip)

    # Force timestamp for determinism
    fixed = datetime(2025, 10, 6, 7, 51, 55)
    monkeypatch.setattr(extract_archives, "_format_timestamp", lambda now=None: fixed.strftime("%Y-%m-%d_%H-%M-%S"))

    # Run extraction
    ok = extract_archives.extract_archive(fake_archive, tmp_path)
    assert ok

    # Verify destination structure: <tmp>/<"13 Camille">/docs/a.txt
    project_dir = tmp_path / "13 Camille"
    assert project_dir.exists()
    assert (project_dir / "docs" / "a.txt").exists()
