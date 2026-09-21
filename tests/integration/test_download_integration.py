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
    def test_full_dropbox_download_workflow(self, mock_get, mock_head, tmp_path, make_zip_bytes):
        """Test complete Dropbox download workflow end-to-end."""
        # Given
        payload = make_zip_bytes(512000 * 4)  # ~2MB of real ZIP content
        chunks = [payload[i:i + 512000] for i in range(0, len(payload), 512000)]

        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'attachment; filename="test_archive.zip"',
            'content-length': str(len(payload)),
        }
        mock_head.return_value = mock_head_response

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'attachment; filename="test_archive.zip"',
            'content-length': str(len(payload)),
        }
        mock_get_response.iter_content = lambda chunk_size: iter(chunks)
        mock_get.return_value = mock_get_response

        progress_updates = []

        def track_progress(status, progress, message):
            progress_updates.append({
                'status': status,
                'progress': progress,
                'message': message,
                'timestamp': time.time()
            })

        # When
        result = DownloadService.download_dropbox_file(
            url='https://www.dropbox.com/scl/fo/abc123/folder?dl=0',
            timestamp='2024-11-18 13:00:00',
            output_dir=tmp_path,
            progress_callback=track_progress
        )

        # Then
        assert result.success is True
        assert result.status == 'completed'
        assert result.filename == 'test_archive.zip'
        assert result.filepath.exists()
        assert result.size_bytes == len(payload)
        assert result.resumed_from == 0
        assert not list(tmp_path.glob('*.part'))

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
    def test_download_with_url_normalization(self, mock_get, mock_head, tmp_path, make_zip_bytes):
        """Test that URLs are properly normalized before download."""
        # Given
        payload = make_zip_bytes(2048)

        mock_head.return_value = Mock(
            status_code=200,
            headers={
                'content-type': 'application/zip',
                'content-length': str(len(payload)),
            },
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'filename="test.zip"',
            'content-length': str(len(payload))
        }
        mock_response.iter_content = lambda chunk_size: [payload]
        mock_get.return_value = mock_response

        # When — URL containing &amp; instead of &
        result = DownloadService.download_dropbox_file(
            url='https://www.dropbox.com/s/abc?rlkey=123&amp;dl=0',
            timestamp='2024-11-18',
            output_dir=tmp_path
        )

        # Then
        assert result.success is True

        # Verify that requests.get was called with normalized URL
        called_url = mock_get.call_args[0][0]
        assert '&amp;' not in called_url  # Should be normalized to &
        assert 'dl=1' in called_url  # Should have dl=1
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_folder_link_validation(self, mock_get, mock_head, tmp_path):
        """Test that folder links are validated properly."""
        # Given — an HTML error page served with a 200 for a folder zip
        html_payload = b'<html>...</html>' * 140000  # ~2MB, above the minimum size
        mock_head.return_value = Mock(
            status_code=200,
            headers={'content-type': 'text/html', 'content-length': str(len(html_payload))},
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'content-type': 'text/html',
            'content-length': str(len(html_payload))
        }
        mock_response.iter_content = lambda chunk_size: [html_payload]
        mock_get.return_value = mock_response

        # When
        result = DownloadService.download_dropbox_file(
            url='https://www.dropbox.com/scl/fo/folder123?dl=0',
            timestamp='2024-11-18',
            output_dir=tmp_path
        )

        # Then — should fail validation (HTML response for folder link)
        assert result.success is False
        assert result.error_kind == 'invalid_payload'
        assert 'non valide' in result.message or 'Invalid' in result.message
        assert not list(tmp_path.glob('*.zip'))
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_concurrent_downloads(self, mock_get, mock_head, tmp_path, make_zip_bytes):
        """Test multiple concurrent downloads."""
        # Given
        import threading
        import io
        import zipfile

        def build_payload(payload_size: int, entry_name: str) -> bytes:
            """Build a real ZIP archive in memory (thread-safe, per download)."""
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_STORED) as archive:
                archive.writestr(entry_name, b'\0' * payload_size)
            return buffer.getvalue()

        payloads = {
            'file1.zip': build_payload(4096, 'one.bin'),
            'file2.zip': build_payload(8192, 'two.bin'),
            'file3.zip': build_payload(12288, 'three.bin'),
        }

        mock_head.return_value = Mock(
            status_code=200,
            headers={'content-type': 'application/zip'},
        )

        def create_mock_response(filename):
            payload = payloads[filename]
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {
                'content-type': 'application/zip',
                'content-disposition': f'filename="{filename}"',
                'content-length': str(len(payload))
            }
            mock_response.iter_content = lambda chunk_size: [payload]
            return mock_response

        mock_get.side_effect = [create_mock_response(name) for name in payloads]

        results = []

        def download_worker(url, timestamp, forced_name):
            result = DownloadService.download_dropbox_file(
                url=url,
                timestamp=timestamp,
                output_dir=tmp_path,
                forced_filename=forced_name,
            )
            results.append(result)

        # When — launch 3 concurrent downloads
        threads = [
            threading.Thread(
                target=download_worker,
                args=(f'https://dropbox.com/s/file{i}', f'2024-11-18-{i}', f'file{i}.zip'),
            )
            for i in range(1, 4)
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Then — verify all downloads succeeded
        assert len(results) == 3
        assert all(r.success for r in results)
        assert len(set(r.filename for r in results)) == 3  # All different filenames


class TestDownloadServiceWithCSVService:
    """Integration tests combining DownloadService with CSVService."""
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_download_with_csv_tracking(self, mock_get, mock_head, tmp_path, make_zip_bytes):
        """Test download with CSV tracking integration."""
        # Given
        payload = make_zip_bytes(3072)

        mock_head.return_value = Mock(
            status_code=200,
            headers={
                'content-type': 'application/zip',
                'content-disposition': 'filename="tracked.zip"',
                'content-length': str(len(payload)),
            },
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'filename="tracked.zip"',
            'content-length': str(len(payload))
        }
        mock_response.iter_content = lambda chunk_size: [payload]
        mock_get.return_value = mock_response

        progress_updates = []

        def csv_progress_callback(status, progress, message):
            progress_updates.append({
                'status': status,
                'progress': progress,
                'message': message
            })

        # When
        result = DownloadService.download_dropbox_file(
            url='https://dropbox.com/s/test',
            timestamp='2024-11-18',
            output_dir=tmp_path,
            progress_callback=csv_progress_callback
        )

        # Then
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
    def test_network_timeout_handling(self, mock_get, mock_head, tmp_path, monkeypatch):
        """Test handling of network timeouts."""
        # Given
        import requests
        from config.settings import config

        monkeypatch.setattr(config, 'DOWNLOAD_RETRY_BACKOFF_S', 0.0, raising=False)
        mock_head.side_effect = requests.exceptions.Timeout("Connection timeout")
        mock_get.side_effect = requests.exceptions.Timeout("Read timeout")

        # When
        result = DownloadService.download_dropbox_file(
            url='https://dropbox.com/s/timeout',
            timestamp='2024-11-18',
            output_dir=tmp_path
        )

        # Then
        assert result.success is False
        assert result.error_kind == 'stalled'
        assert 'timeout' in result.message.lower() or 'error' in result.message.lower()
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_http_error_handling(self, mock_get, mock_head, tmp_path):
        """Test handling of HTTP errors (missing R2 object)."""
        # Given
        import requests

        mock_head.return_value = Mock(status_code=404, headers={})

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.reason = 'Not Found'
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        # When
        result = DownloadService.download_dropbox_file(
            url='https://dropbox.com/s/notfound',
            timestamp='2024-11-18',
            output_dir=tmp_path
        )

        # Then
        assert result.success is False
        assert result.error_kind == 'not_found'
        assert result.status_code == 404
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
