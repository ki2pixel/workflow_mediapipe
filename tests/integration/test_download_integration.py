#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for DownloadService.
Tests the complete download workflow with real HTTP interactions (mocked).
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import time

from services.download_service import DownloadService, DownloadResult
from services.csv_service import CSVService


class TestDownloadServiceIntegration:
    """Integration tests for DownloadService with CSVService."""
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_full_dropbox_download_workflow(self, mock_get, mock_head, tmp_path):
        """Test complete Dropbox download workflow end-to-end."""
        # Setup mock responses
        mock_head_response = Mock()
        mock_head_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'attachment; filename="test_archive.zip"'
        }
        mock_head.return_value = mock_head_response
        
        # Mock GET response with chunked data
        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'attachment; filename="test_archive.zip"',
            'content-length': '2048000'  # 2MB
        }
        # Simulate chunked download
        chunks = [b'x' * 512000 for _ in range(4)]  # 4 chunks of 512KB
        mock_get_response.iter_content = lambda chunk_size: iter(chunks)
        mock_get.return_value = mock_get_response
        
        # Track progress updates
        progress_updates = []
        
        def track_progress(status, progress, message):
            progress_updates.append({
                'status': status,
                'progress': progress,
                'message': message,
                'timestamp': time.time()
            })
        
        # Execute download
        result = DownloadService.download_dropbox_file(
            url='https://www.dropbox.com/scl/fo/abc123/folder?dl=0',
            timestamp='2024-11-18 13:00:00',
            output_dir=tmp_path,
            progress_callback=track_progress
        )
        
        # Verify result
        assert result.success is True
        assert result.status == 'completed'
        assert result.filename == 'test_archive.zip'
        assert result.filepath.exists()
        assert result.size_bytes == 2048000
        
        # Verify progress updates
        assert len(progress_updates) > 0
        assert any(u['status'] == 'downloading' for u in progress_updates)
        assert any(u['status'] == 'completed' for u in progress_updates)
        
        # Verify final progress is 100%
        completed_updates = [u for u in progress_updates if u['status'] == 'completed']
        assert len(completed_updates) > 0
        assert completed_updates[-1]['progress'] == 100
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_download_with_url_normalization(self, mock_get, mock_head, tmp_path):
        """Test that URLs are properly normalized before download."""
        mock_head.return_value = Mock(headers={'content-type': 'application/zip'})
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'filename="test.zip"',
            'content-length': '1024'
        }
        mock_response.iter_content = lambda chunk_size: [b'test content']
        mock_get.return_value = mock_response
        
        # Test with URL containing &amp; instead of &
        result = DownloadService.download_dropbox_file(
            url='https://www.dropbox.com/s/abc?rlkey=123&amp;dl=0',
            timestamp='2024-11-18',
            output_dir=tmp_path
        )
        
        assert result.success is True
        
        # Verify that requests.get was called with normalized URL
        called_url = mock_get.call_args[0][0]
        assert '&amp;' not in called_url  # Should be normalized to &
        assert 'dl=1' in called_url  # Should have dl=1
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_folder_link_validation(self, mock_get, mock_head, tmp_path):
        """Test that folder links are validated properly."""
        mock_head.return_value = Mock(headers={'content-type': 'text/html'})
        
        # Simulate HTML response (invalid for folder download)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'content-type': 'text/html',
            'content-length': '5000'
        }
        mock_response.iter_content = lambda chunk_size: [b'<html>...</html>']
        mock_get.return_value = mock_response
        
        result = DownloadService.download_dropbox_file(
            url='https://www.dropbox.com/scl/fo/folder123?dl=0',
            timestamp='2024-11-18',
            output_dir=tmp_path
        )
        
        # Should fail validation (HTML response for folder link)
        assert result.success is False
        assert 'non valide' in result.message or 'Invalid' in result.message
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_concurrent_downloads(self, mock_get, mock_head, tmp_path):
        """Test multiple concurrent downloads."""
        import threading
        
        mock_head.return_value = Mock(headers={'content-type': 'application/zip'})
        
        def create_mock_response(filename):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {
                'content-type': 'application/zip',
                'content-disposition': f'filename="{filename}"',
                'content-length': '1024'
            }
            mock_response.iter_content = lambda chunk_size: [b'test']
            return mock_response
        
        # Different response for each call
        mock_get.side_effect = [
            create_mock_response('file1.zip'),
            create_mock_response('file2.zip'),
            create_mock_response('file3.zip')
        ]
        
        results = []
        
        def download_worker(url, timestamp):
            result = DownloadService.download_dropbox_file(
                url=url,
                timestamp=timestamp,
                output_dir=tmp_path
            )
            results.append(result)
        
        # Launch 3 concurrent downloads
        threads = [
            threading.Thread(target=download_worker, args=(f'https://dropbox.com/s/file{i}', f'2024-11-18-{i}'))
            for i in range(1, 4)
        ]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # Verify all downloads succeeded
        assert len(results) == 3
        assert all(r.success for r in results)
        assert len(set(r.filename for r in results)) == 3  # All different filenames


class TestDownloadServiceWithCSVService:
    """Integration tests combining DownloadService with CSVService."""
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_download_with_csv_tracking(self, mock_get, mock_head, tmp_path):
        """Test download with CSV tracking integration."""
        mock_head.return_value = Mock(headers={'content-type': 'application/zip'})
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'filename="tracked.zip"',
            'content-length': '1024'
        }
        mock_response.iter_content = lambda chunk_size: [b'content']
        mock_get.return_value = mock_response
        
        # Track progress updates via callback
        progress_updates = []
        
        def csv_progress_callback(status, progress, message):
            progress_updates.append({
                'status': status,
                'progress': progress,
                'message': message
            })
        
        # Execute download with tracking
        result = DownloadService.download_dropbox_file(
            url='https://dropbox.com/s/test',
            timestamp='2024-11-18',
            output_dir=tmp_path,
            progress_callback=csv_progress_callback
        )
        
        assert result.success is True
        
        # Verify that progress callback was called
        assert len(progress_updates) > 0
        
        # Verify that we received completion status
        completed_updates = [u for u in progress_updates if u['status'] == 'completed']
        assert len(completed_updates) > 0
        assert completed_updates[-1]['progress'] == 100


class TestDownloadServiceErrorHandling:
    """Integration tests for error handling scenarios."""
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_network_timeout_handling(self, mock_get, mock_head, tmp_path):
        """Test handling of network timeouts."""
        import requests
        
        mock_head.side_effect = requests.exceptions.Timeout("Connection timeout")
        mock_get.side_effect = requests.exceptions.Timeout("Read timeout")
        
        result = DownloadService.download_dropbox_file(
            url='https://dropbox.com/s/timeout',
            timestamp='2024-11-18',
            output_dir=tmp_path
        )
        
        assert result.success is False
        assert 'timeout' in result.message.lower() or 'error' in result.message.lower()
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_http_error_handling(self, mock_get, mock_head, tmp_path):
        """Test handling of HTTP errors."""
        import requests
        
        mock_head.return_value = Mock(headers={})
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        result = DownloadService.download_dropbox_file(
            url='https://dropbox.com/s/notfound',
            timestamp='2024-11-18',
            output_dir=tmp_path
        )
        
        assert result.success is False
        assert '404' in result.message or 'error' in result.message.lower()
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_disk_full_handling(self, mock_get, mock_head, tmp_path):
        """Test handling of disk full errors."""
        mock_head.return_value = Mock(headers={'content-type': 'application/zip'})
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'content-type': 'application/zip',
            'content-length': '1024'
        }
        mock_response.iter_content = lambda chunk_size: [b'data']
        mock_get.return_value = mock_response
        
        # Make the output directory read-only to simulate disk full
        import os
        import stat
        
        read_only_dir = tmp_path / 'readonly'
        read_only_dir.mkdir()
        os.chmod(read_only_dir, stat.S_IRUSR | stat.S_IXUSR)
        
        try:
            result = DownloadService.download_dropbox_file(
                url='https://dropbox.com/s/test',
                timestamp='2024-11-18',
                output_dir=read_only_dir
            )
            
            # Should fail due to permission error
            assert result.success is False
        finally:
            # Restore permissions for cleanup
            os.chmod(read_only_dir, stat.S_IRWXU)
