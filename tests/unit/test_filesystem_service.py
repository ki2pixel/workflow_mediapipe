# -*- coding: utf-8 -*-
import os
from pathlib import Path

import pytest

from services.filesystem_service import FilesystemService
import services.filesystem_service as fs_mod


@pytest.fixture
def temp_cache_root(tmp_path, monkeypatch):
    cache_root = tmp_path / 'cache_root'
    cache_root.mkdir()
    monkeypatch.setattr(fs_mod, 'CACHE_ROOT', cache_root, raising=True)
    return cache_root


@pytest.fixture
def allow_explorer_open(monkeypatch):
    monkeypatch.setattr(fs_mod.config, 'DISABLE_EXPLORER_OPEN', False, raising=True)
    monkeypatch.setattr(fs_mod.config, 'ENABLE_EXPLORER_OPEN', True, raising=True)
    return True


def test_find_cache_folder_by_number_single_match(temp_cache_root):
    # Given: A cache root containing a single directory starting with the requested number
    target = temp_cache_root / '115 Camille'
    target.mkdir()

    # When: Searching for the cache folder by number
    res = FilesystemService.find_cache_folder_by_number('115')

    # Then: The best match is the only matching folder
    assert res.number == '115'
    assert len(res.matches) == 1
    assert res.best_match == str(target.resolve())


def test_find_cache_folder_by_number_multiple_matches_best_exact(temp_cache_root):
    # Given: A cache root containing multiple directories that match the numeric prefix
    (temp_cache_root / '115 Camille').mkdir()
    (temp_cache_root / '115-Camille').mkdir()
    (temp_cache_root / '115CamilleOther').mkdir()

    # When: Searching for the cache folder by number
    res = FilesystemService.find_cache_folder_by_number('115')

    # Then: All matches are returned and best_match prefers an exact prefix match
    assert len(res.matches) == 3
    assert Path(res.best_match).name in {'115 Camille', '115-Camille'}


def test_find_cache_folder_by_number_invalid_input(temp_cache_root):
    # Given: A non-numeric input
    # When: Searching for a cache folder by number
    res = FilesystemService.find_cache_folder_by_number('abc')

    # Then: No matches are returned
    assert res.number in ('', 'abc')
    assert res.matches == []
    assert res.best_match is None


def test_open_path_in_explorer_rejects_outside(tmp_path, monkeypatch, temp_cache_root, allow_explorer_open):
    # Given: A path that exists but is outside CACHE_ROOT
    outside = tmp_path / 'outside'
    outside.mkdir()

    # When: Attempting to open the path in explorer
    ok, msg = FilesystemService.open_path_in_explorer(str(outside))

    # Then: The operation is rejected
    assert ok is False
    assert 'non autorisé' in msg or 'autorisé' in msg or 'hors' in msg.lower()


def test_open_path_in_explorer_missing(monkeypatch, temp_cache_root, allow_explorer_open):
    # Given: A missing directory under CACHE_ROOT
    missing = temp_cache_root / '999 Inconnu'

    # When: Attempting to open the missing path in explorer
    ok, msg = FilesystemService.open_path_in_explorer(str(missing))

    # Then: The operation fails with a clear message
    assert ok is False
    assert "n'existe" in msg or 'existe' in msg


def test_open_path_in_explorer_disabled_by_configuration(monkeypatch, temp_cache_root):
    # Given: Explorer opening is explicitly disabled by configuration
    monkeypatch.setattr(fs_mod.config, 'DISABLE_EXPLORER_OPEN', True, raising=True)
    monkeypatch.setattr(fs_mod.config, 'ENABLE_EXPLORER_OPEN', True, raising=True)
    monkeypatch.setattr(fs_mod.config, 'DEBUG', True, raising=True)

    # When: Attempting to open a valid directory under CACHE_ROOT
    target = temp_cache_root / '115 Camille'
    target.mkdir()
    ok, msg = FilesystemService.open_path_in_explorer(str(target))

    # Then: The operation is blocked
    assert ok is False
    assert 'désactivée' in msg


def test_open_path_in_explorer_disabled_in_production(monkeypatch, temp_cache_root):
    # Given: Production mode and explorer opening is not explicitly enabled
    monkeypatch.setattr(fs_mod.config, 'DISABLE_EXPLORER_OPEN', False, raising=True)
    monkeypatch.setattr(fs_mod.config, 'ENABLE_EXPLORER_OPEN', False, raising=True)
    monkeypatch.setattr(fs_mod.config, 'DEBUG', False, raising=True)

    # When: Attempting to open a valid directory under CACHE_ROOT
    target = temp_cache_root / '115 Camille'
    target.mkdir()
    ok, msg = FilesystemService.open_path_in_explorer(str(target))

    # Then: The operation is blocked
    assert ok is False
    assert 'production' in msg or 'headless' in msg


def test_open_path_in_explorer_disabled_in_headless(monkeypatch, temp_cache_root):
    # Given: Headless mode (no display env) and explorer opening is not explicitly enabled
    monkeypatch.delenv('DISPLAY', raising=False)
    monkeypatch.delenv('WAYLAND_DISPLAY', raising=False)
    monkeypatch.setattr(fs_mod.config, 'DISABLE_EXPLORER_OPEN', False, raising=True)
    monkeypatch.setattr(fs_mod.config, 'ENABLE_EXPLORER_OPEN', False, raising=True)
    monkeypatch.setattr(fs_mod.config, 'DEBUG', True, raising=True)

    # When: Attempting to open a valid directory under CACHE_ROOT
    target = temp_cache_root / '115 Camille'
    target.mkdir()
    ok, msg = FilesystemService.open_path_in_explorer(str(target))

    # Then: The operation is blocked
    assert ok is False
    assert 'headless' in msg


def test_sanitize_filename_basic():
    """Test basic filename sanitization."""
    # Given: A filename with spaces
    # When: Sanitizing the filename
    result = FilesystemService.sanitize_filename("Test File.mp4")
    # Then: Spaces are converted to underscores
    assert result == "Test_File.mp4"


def test_sanitize_filename_invalid_chars():
    """Test sanitization with invalid characters."""
    # Given: A filename containing characters invalid for filesystem paths
    # When: Sanitizing the filename
    result = FilesystemService.sanitize_filename("Test/File<>:*.mp4")
    # Then: Invalid characters are removed
    assert "/" not in result
    assert "<" not in result
    assert ">" not in result
    assert ":" not in result
    assert "*" not in result


def test_sanitize_filename_none():
    """Test sanitization with None input."""
    # Given: A None filename
    # When: Sanitizing the filename
    result = FilesystemService.sanitize_filename(None)
    # Then: A safe default is returned
    assert result == "fichier_nom_absent"


def test_sanitize_filename_truncation():
    """Test filename truncation for long names."""
    # Given: A filename longer than the allowed max length
    long_name = "a" * 250 + ".mp4"
    # When: Sanitizing with a max length constraint
    result = FilesystemService.sanitize_filename(long_name, max_length=230)
    # Then: The filename is truncated but keeps its extension
    assert len(result) <= 230
    assert result.endswith(".mp4")


def test_format_bytes_human_bytes():
    """Test byte formatting for small values."""
    # Given: A value lower than 1KB
    # When: Formatting bytes
    assert FilesystemService.format_bytes_human(512) == "512B"


def test_format_bytes_human_kilobytes():
    """Test byte formatting for KB values."""
    # Given: A value in the kilobytes range
    # When: Formatting bytes
    result = FilesystemService.format_bytes_human(2048)
    # Then: The output is in KB
    assert "KB" in result
    assert "2.0" in result


def test_format_bytes_human_megabytes():
    """Test byte formatting for MB values."""
    # Given: A value in the megabytes range
    # When: Formatting bytes
    result = FilesystemService.format_bytes_human(1048576 * 2)
    # Then: The output is in MB
    assert "MB" in result
    assert "2.0" in result


def test_format_bytes_human_negative():
    """Test byte formatting with negative value."""
    # Given: A negative bytes value
    # When: Formatting bytes
    result = FilesystemService.format_bytes_human(-100)
    # Then: The output is clamped
    assert result == "0B"


def test_find_videos_for_tracking(tmp_path):
    """Test finding videos for tracking."""
    # Given: A projects directory with videos, one of which already has a sibling JSON
    projets = tmp_path / "projets_extraits"
    projets.mkdir()
    
    video1 = projets / "video1.mp4"
    video1.touch()
    
    video2 = projets / "video2.mp4"
    video2.touch()
    json2 = projets / "video2.json"
    json2.touch()

    # When: Searching for videos needing tracking
    videos = FilesystemService.find_videos_for_tracking(tmp_path, None, None)

    # Then: Only the video without a sibling JSON is returned
    assert len(videos) == 1
    assert "video1.mp4" in videos[0]
