import os
from pathlib import Path
from datetime import datetime, timedelta

import importlib
import importlib.util
import sys
import types


def load_extract_archives_module_by_path(repo_root: Path):
    module_path = repo_root / "workflow_scripts" / "step1" / "extract_archives.py"
    spec = importlib.util.spec_from_file_location("extract_archives", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader, "Failed to create import spec for extract_archives.py"
    # Stub optional dependency 'rarfile' to avoid import errors during tests
    if "rarfile" not in sys.modules:
        sys.modules["rarfile"] = types.ModuleType("rarfile")
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def setup_module_paths(tmp_path, module):
    # Redirect LOG_DIR and related files to tmp_path
    log_dir = tmp_path / "logs" / "step1"
    log_dir.mkdir(parents=True, exist_ok=True)
    processed_file = log_dir / "processed_archives.txt"
    marker_file = log_dir / "processed_archives.last_reset"

    # Patch module-level constants
    setattr(module, "LOG_DIR", log_dir)
    setattr(module, "PROCESSED_ARCHIVES_FILE", processed_file)
    setattr(module, "PROCESSED_ARCHIVES_RESET_MARKER", marker_file)

    return log_dir, processed_file, marker_file


def test_no_reset_same_month(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    module = load_extract_archives_module_by_path(repo_root)
    log_dir, processed_file, marker_file = setup_module_paths(tmp_path, module)

    # Prepare files: processed has content, marker has current month
    processed_file.write_text("/abs/path/archive1.zip\n", encoding="utf-8")
    current_month = datetime.now().strftime("%Y-%m")
    marker_file.write_text(current_month, encoding="utf-8")

    # Call reset
    did_reset = module.reset_processed_archives_if_needed()

    # Assert: no reset, file unchanged, marker unchanged
    assert did_reset is False
    assert processed_file.read_text(encoding="utf-8").strip() == "/abs/path/archive1.zip"
    assert marker_file.read_text(encoding="utf-8").strip() == current_month


def test_reset_new_month_creates_backup_and_truncates(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    module = load_extract_archives_module_by_path(repo_root)
    log_dir, processed_file, marker_file = setup_module_paths(tmp_path, module)

    # last month marker
    last_month = (datetime.now().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    marker_file.write_text(last_month, encoding="utf-8")

    # processed has content
    processed_file.write_text("/abs/path/archive1.zip\n/abs/path/archive2.zip\n", encoding="utf-8")

    # Use a fixed 'now' in current month
    now = datetime.now()
    did_reset = module.reset_processed_archives_if_needed(now=now)

    # Assert
    assert did_reset is True
    # processed should be empty
    assert processed_file.exists() and processed_file.stat().st_size == 0
    # marker updated
    assert marker_file.read_text(encoding="utf-8").strip() == now.strftime("%Y-%m")
    # backup exists
    backups = list(log_dir.glob("processed_archives_*_backup_*.txt"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8").count("/abs/path/archive") == 2


def test_reset_when_no_files_creates_marker_only(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    module = load_extract_archives_module_by_path(repo_root)
    log_dir, processed_file, marker_file = setup_module_paths(tmp_path, module)

    # Ensure no processed file exists
    if processed_file.exists():
        processed_file.unlink()

    # No marker as well
    if marker_file.exists():
        marker_file.unlink()

    did_reset = module.reset_processed_archives_if_needed(now=datetime(2025, 10, 3, 11, 0, 0))

    assert did_reset is True
    assert marker_file.exists()
    assert marker_file.read_text(encoding="utf-8").strip() == "2025-10"
    # processed file should exist (emptied) only if created by function; tolerate missing file
    if processed_file.exists():
        assert processed_file.stat().st_size == 0
