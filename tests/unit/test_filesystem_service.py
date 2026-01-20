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


def test_find_cache_folder_by_number_single_match(temp_cache_root):
    target = temp_cache_root / '115 Camille'
    target.mkdir()

    res = FilesystemService.find_cache_folder_by_number('115')
    assert res.number == '115'
    assert len(res.matches) == 1
    assert res.best_match == str(target.resolve())


def test_find_cache_folder_by_number_multiple_matches_best_exact(temp_cache_root):
    (temp_cache_root / '115 Camille').mkdir()
    (temp_cache_root / '115-Camille').mkdir()
    (temp_cache_root / '115CamilleOther').mkdir()

    res = FilesystemService.find_cache_folder_by_number('115')
    assert len(res.matches) == 3
    assert Path(res.best_match).name in {'115 Camille', '115-Camille'}


def test_find_cache_folder_by_number_invalid_input(temp_cache_root):
    res = FilesystemService.find_cache_folder_by_number('abc')
    assert res.number in ('', 'abc')
    assert res.matches == []
    assert res.best_match is None


def test_open_path_in_explorer_rejects_outside(tmp_path, monkeypatch, temp_cache_root):
    outside = tmp_path / 'outside'
    outside.mkdir()
    ok, msg = FilesystemService.open_path_in_explorer(str(outside))
    assert ok is False
    assert 'non autorisé' in msg or 'autorisé' in msg or 'hors' in msg.lower()


def test_open_path_in_explorer_missing(monkeypatch, temp_cache_root):
    missing = temp_cache_root / '999 Inconnu'
    ok, msg = FilesystemService.open_path_in_explorer(str(missing))
    assert ok is False
    assert "n'existe" in msg or 'existe' in msg


def test_sanitize_filename_basic():
    """Test basic filename sanitization."""
    result = FilesystemService.sanitize_filename("Test File.mp4")
    assert result == "Test_File.mp4"


def test_sanitize_filename_invalid_chars():
    """Test sanitization with invalid characters."""
    result = FilesystemService.sanitize_filename("Test/File<>:*.mp4")
    assert "/" not in result
    assert "<" not in result
    assert ">" not in result
    assert ":" not in result
    assert "*" not in result


def test_sanitize_filename_none():
    """Test sanitization with None input."""
    result = FilesystemService.sanitize_filename(None)
    assert result == "fichier_nom_absent"


def test_sanitize_filename_truncation():
    """Test filename truncation for long names."""
    long_name = "a" * 250 + ".mp4"
    result = FilesystemService.sanitize_filename(long_name, max_length=230)
    assert len(result) <= 230
    assert result.endswith(".mp4")


def test_format_bytes_human_bytes():
    """Test byte formatting for small values."""
    assert FilesystemService.format_bytes_human(512) == "512B"


def test_format_bytes_human_kilobytes():
    """Test byte formatting for KB values."""
    result = FilesystemService.format_bytes_human(2048)
    assert "KB" in result
    assert "2.0" in result


def test_format_bytes_human_megabytes():
    """Test byte formatting for MB values."""
    result = FilesystemService.format_bytes_human(1048576 * 2)
    assert "MB" in result
    assert "2.0" in result


def test_format_bytes_human_negative():
    """Test byte formatting with negative value."""
    result = FilesystemService.format_bytes_human(-100)
    assert result == "0B"


def test_find_videos_for_tracking(tmp_path):
    """Test finding videos for tracking."""
    projets = tmp_path / "projets_extraits"
    projets.mkdir()
    
    video1 = projets / "video1.mp4"
    video1.touch()
    
    video2 = projets / "video2.mp4"
    video2.touch()
    json2 = projets / "video2.json"
    json2.touch()
    
    videos = FilesystemService.find_videos_for_tracking(tmp_path, None, None)
    
    assert len(videos) == 1
    assert "video1.mp4" in videos[0]
