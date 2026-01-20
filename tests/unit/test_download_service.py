#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for DownloadService.
Tests the download management functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from services.download_service import DownloadService, DownloadResult


class TestDownloadResult:
    """Test DownloadResult dataclass."""
    
    def test_download_result_creation(self):
        """Test creating a DownloadResult."""
        result = DownloadResult(
            success=True,
            download_id='test_123',
            filename='test.zip',
            filepath=Path('/tmp/test.zip'),
            size_bytes=1024,
            message='Success',
            status='completed'
        )
        
        assert result.success is True
        assert result.download_id == 'test_123'
        assert result.filename == 'test.zip'
        assert result.size_bytes == 1024


class TestDownloadServiceHelpers:
    """Test DownloadService helper methods."""
    
    def test_looks_like_zip_with_zip_content_type(self):
        """Test ZIP detection with content-type."""
        assert DownloadService._looks_like_zip('application/zip', '') is True
        assert DownloadService._looks_like_zip('application/octet-stream', '') is True
    
    def test_looks_like_zip_with_content_disposition(self):
        """Test ZIP detection with content-disposition."""
        assert DownloadService._looks_like_zip('', 'filename=test.zip') is True
    
    def test_looks_like_zip_empty(self):
        """Test ZIP detection with empty headers."""
        assert DownloadService._looks_like_zip('', '') is False
    
    def test_extract_filename_from_content_disposition(self):
        """Test filename extraction from Content-Disposition."""
        cd = 'attachment; filename="test_file.zip"'
        filename = DownloadService._extract_filename(cd, '2024-01-01', 'http://test.com')
        
        assert 'test_file' in filename
        assert filename.endswith('.zip')
    
    def test_extract_filename_utf8(self):
        """Test UTF-8 filename extraction."""
        cd = "attachment; filename*=UTF-8''test%20file.zip"
        filename = DownloadService._extract_filename(cd, '2024-01-01', 'http://test.com')
        
        assert 'test' in filename
        assert filename.endswith('.zip')
    
    def test_extract_filename_fallback(self):
        """Test filename fallback to timestamp."""
        filename = DownloadService._extract_filename(None, '2024/01/01 12:00:00', 'http://test.com')
        
        assert 'download_' in filename
        assert '20240101' in filename
    
    def test_extract_filename_adds_zip_for_folder(self):
        """Test that .zip extension is added for folder links."""
        cd = 'attachment; filename="folder"'
        url = 'https://www.dropbox.com/scl/fo/abc123'
        filename = DownloadService._extract_filename(cd, '2024-01-01', url)
        
        assert filename.endswith('.zip')
    
    def test_resolve_filepath_conflicts_no_conflict(self, tmp_path):
        """Test filepath resolution without conflicts."""
        filepath = DownloadService._resolve_filepath_conflicts(tmp_path, 'test.zip')
        
        assert filepath == tmp_path / 'test.zip'
    
    def test_resolve_filepath_conflicts_with_conflict(self, tmp_path):
        """Test filepath resolution with existing file."""
        # Create existing file
        existing = tmp_path / 'test.zip'
        existing.touch()
        
        filepath = DownloadService._resolve_filepath_conflicts(tmp_path, 'test.zip')
        
        assert filepath != existing
        assert 'test_1.zip' in str(filepath)
    
    def test_validate_download_non_folder_link(self, tmp_path):
        """Test validation for non-folder links."""
        test_file = tmp_path / 'test.zip'
        test_file.write_text('test content')
        
        result = DownloadService._validate_download(
            test_file,
            'text/html',
            'https://dropbox.com/s/abc/file.zip',
            100
        )
        
        # Non-folder links should always pass
        assert result is True
    
    def test_validate_download_folder_link_too_small(self, tmp_path):
        """Test validation fails for small folder ZIP."""
        test_file = tmp_path / 'test.zip'
        test_file.write_text('small')
        
        result = DownloadService._validate_download(
            test_file,
            'application/zip',
            'https://dropbox.com/scl/fo/abc',
            5  # Too small
        )
        
        assert result is False
    
    def test_validate_download_folder_link_valid(self, tmp_path):
        """Test validation passes for valid folder ZIP."""
        test_file = tmp_path / 'test.zip'
        test_file.write_bytes(b'x' * 2_000_000)  # 2MB
        
        result = DownloadService._validate_download(
            test_file,
            'application/zip',
            'https://dropbox.com/scl/fo/abc',
            2_000_000
        )
        
        assert result is True


class TestDownloadServiceProgressCallback:
    """Test progress callback creation."""
    
    def test_create_progress_callback(self):
        """Test creating a progress callback."""
        updates = []
        
        def mock_update(download_id, status, progress, message):
            updates.append((download_id, status, progress, message))
        
        callback = DownloadService.create_progress_callback('dl_123', mock_update)
        
        callback('downloading', 50, 'Downloading...')
        
        assert len(updates) == 1
        assert updates[0] == ('dl_123', 'downloading', 50, 'Downloading...')
    
    def test_progress_callback_handles_errors(self):
        """Test that callback handles update function errors gracefully."""
        def failing_update(download_id, status, progress, message):
            raise Exception("Update failed")
        
        callback = DownloadService.create_progress_callback('dl_123', failing_update)
        
        # Should not raise exception
        callback('downloading', 50, 'Test')


class TestDownloadServiceIntegration:
    """Integration tests for DownloadService (with mocked requests)."""
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_download_dropbox_file_success(self, mock_get, mock_head, tmp_path):
        """Test successful Dropbox file download."""
        # Mock HEAD response
        mock_head_response = Mock()
        mock_head_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'attachment; filename="test.zip"'
        }
        mock_head.return_value = mock_head_response
        
        # Mock GET response
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'attachment; filename="test.zip"',
            'content-length': '1024'
        }
        mock_get_response.iter_content = lambda chunk_size: [b'x' * 1024]
        mock_get.return_value = mock_get_response
        
        # Execute download
        result = DownloadService.download_dropbox_file(
            url='https://www.dropbox.com/s/abc/test.zip?dl=0',
            timestamp='2024-01-01 12:00:00',
            output_dir=tmp_path
        )
        
        assert result.success is True
        assert result.status == 'completed'
        assert result.filepath is not None
        assert result.filepath.exists()

    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_download_forced_filename_overrides_header(self, mock_get, mock_head, tmp_path):
        """When forced_filename is provided, it must be used (sanitized) instead of Content-Disposition."""
        # Mock HEAD response
        mock_head_response = Mock()
        mock_head_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'attachment; filename="ignored.zip"'
        }
        mock_head.return_value = mock_head_response

        # Mock GET response
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'attachment; filename="ignored.zip"',
            'content-length': '1024'
        }
        mock_get_response.iter_content = lambda chunk_size: [b'x' * 1024]
        mock_get.return_value = mock_get_response

        result = DownloadService.download_dropbox_file(
            url='https://www.dropbox.com/s/abc/test.zip?dl=0',
            timestamp='2024-01-01 12:00:00',
            output_dir=tmp_path,
            forced_filename='61 Camille.zip'
        )

        assert result.success is True
        assert result.filepath is not None
        assert result.filepath.name == '61_Camille.zip'
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_download_dropbox_file_network_error(self, mock_get, mock_head, tmp_path):
        """Test download with network error."""
        import requests
        
        mock_head.side_effect = requests.exceptions.Timeout("Connection timeout")
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")
        
        result = DownloadService.download_dropbox_file(
            url='https://www.dropbox.com/s/abc/test.zip',
            timestamp='2024-01-01',
            output_dir=tmp_path
        )
        
        assert result.success is False
        assert result.status == 'failed'
        assert 'Network error' in result.message or 'error' in result.message.lower()
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_download_with_progress_callback(self, mock_get, mock_head, tmp_path):
        """Test download with progress callback."""
        # Setup mocks
        mock_head.return_value = Mock(headers={'content-type': 'application/zip'})
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'filename="test.zip"',
            'content-length': '2048'
        }
        mock_response.iter_content = lambda chunk_size: [b'x' * 1024, b'y' * 1024]
        mock_get.return_value = mock_response
        
        # Track progress updates
        progress_updates = []
        
        def track_progress(status, progress, message):
            progress_updates.append((status, progress))
        
        result = DownloadService.download_dropbox_file(
            url='https://www.dropbox.com/s/abc/test.zip',
            timestamp='2024-01-01',
            output_dir=tmp_path,
            progress_callback=track_progress
        )
        
        assert result.success is True
        assert len(progress_updates) > 0
        # Should have at least one progress update
        assert any(status == 'downloading' for status, _ in progress_updates)
