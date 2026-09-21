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
    
    def test_validate_download_rejects_html_error_page(self, tmp_path):
        """A 200 answer carrying an HTML error page must never validate (missing R2 object)."""
        # Given
        test_file = tmp_path / 'test.zip'
        test_file.write_text('<html><body>Not found</body></html>')

        # When
        result = DownloadService._validate_download(
            test_file,
            'text/html',
            'https://dropbox.com/s/abc/file.zip',
            100
        )

        # Then
        assert result is False

    def test_validate_download_non_folder_link_accepts_valid_zip(self, tmp_path, make_zip_bytes):
        """A real ZIP served for a regular link validates."""
        # Given
        payload = make_zip_bytes(4096)
        test_file = tmp_path / 'test.zip'
        test_file.write_bytes(payload)

        # When
        result = DownloadService._validate_download(
            test_file,
            'application/zip',
            'https://dropbox.com/s/abc/file.zip',
            len(payload)
        )

        # Then
        assert result is True

    def test_validate_download_rejects_truncated_zip(self, tmp_path):
        """A truncated payload (no central directory) must be rejected."""
        # Given
        test_file = tmp_path / 'test.zip'
        test_file.write_bytes(b'PK\x03\x04' + b'x' * 5000)

        # When
        result = DownloadService._validate_download(
            test_file,
            'application/zip',
            'https://server.kidpixel.workers.dev/dropbox/a/b/file',
            5004
        )

        # Then
        assert result is False
    
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
    
    def test_validate_download_folder_link_valid(self, tmp_path, make_zip_bytes):
        """Test validation passes for a valid folder ZIP."""
        # Given
        payload = make_zip_bytes(2_000_000)
        test_file = tmp_path / 'test.zip'
        test_file.write_bytes(payload)

        # When
        result = DownloadService._validate_download(
            test_file,
            'application/zip',
            'https://dropbox.com/scl/fo/abc',
            len(payload)
        )

        # Then
        assert result is True

    def test_validate_download_folder_link_not_a_zip(self, tmp_path):
        """Folder links serving filler bytes must be rejected."""
        # Given
        test_file = tmp_path / 'test.zip'
        test_file.write_bytes(b'x' * 2_000_000)

        # When
        result = DownloadService._validate_download(
            test_file,
            'application/zip',
            'https://dropbox.com/scl/fo/abc',
            2_000_000
        )

        # Then
        assert result is False

    def test_is_valid_zip_payload(self, tmp_path, make_zip_bytes):
        """ZIP payload detection reads the archive central directory."""
        # Given
        valid_zip = tmp_path / 'valid.zip'
        valid_zip.write_bytes(make_zip_bytes(1024))
        not_a_zip = tmp_path / 'invalid.zip'
        not_a_zip.write_bytes(b'plain text payload')

        # When / Then
        assert DownloadService._is_valid_zip_payload(valid_zip) is True
        assert DownloadService._is_valid_zip_payload(not_a_zip) is False


class TestDownloadServiceResume:
    """Resumable download behaviour (.part file + HTTP Range)."""

    @staticmethod
    def _json_zip_headers(payload: bytes, extra: dict = None) -> dict:
        headers = {
            'content-type': 'application/zip',
            'content-length': str(len(payload)),
        }
        if extra:
            headers.update(extra)
        return headers

    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_resumes_from_existing_part_file(self, mock_get, mock_head, tmp_path, make_zip_bytes):
        """A previous partial download is resumed with a Range request."""
        # Given — 500 bytes of the payload are already on disk
        payload = make_zip_bytes(4096)
        part_file = tmp_path / '197_Camille.zip.part'
        part_file.write_bytes(payload[:500])

        mock_head.return_value = Mock(status_code=200, headers=self._json_zip_headers(payload, {'accept-ranges': 'bytes'}))

        response = Mock()
        response.status_code = 206
        response.headers = {
            'content-type': 'application/zip',
            'content-length': str(len(payload) - 500),
            'content-range': f'bytes 500-{len(payload) - 1}/{len(payload)}',
        }
        response.iter_content = lambda chunk_size: [payload[500:]]
        mock_get.return_value = response

        # When
        result = DownloadService.download_dropbox_file(
            url='https://server.kidpixel.workers.dev/dropbox/9529f228/6d6c3f94/file',
            timestamp='2026-09-21 16:47:14',
            output_dir=tmp_path,
            forced_filename='197 Camille.zip',
        )

        # Then
        assert result.success is True
        assert result.resumed_from == 500
        assert result.filepath.read_bytes() == payload
        assert mock_get.call_args.kwargs['headers']['Range'] == 'bytes=500-'
        assert not list(tmp_path.glob('*.part'))

    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_restarts_from_zero_when_range_rejected(self, mock_get, mock_head, tmp_path, make_zip_bytes, monkeypatch):
        """HTTP 416 discards the partial file and the retry starts clean."""
        # Given
        payload = make_zip_bytes(2048)
        (tmp_path / '108_Camille.zip.part').write_bytes(b'garbage-partial')

        mock_head.return_value = Mock(status_code=200, headers=self._json_zip_headers(payload))

        rejected = Mock(status_code=416, headers={})
        full = Mock(status_code=200, headers=self._json_zip_headers(payload))
        full.iter_content = lambda chunk_size: [payload]
        mock_get.side_effect = [rejected, full]

        monkeypatch.setattr('config.settings.config.DOWNLOAD_RETRY_BACKOFF_S', 0.0, raising=False)

        # When
        result = DownloadService.download_dropbox_file(
            url='https://server.kidpixel.workers.dev/dropbox/a/b/file',
            timestamp='2026-09-21 11:15:38',
            output_dir=tmp_path,
            forced_filename='108 Camille.zip',
        )

        # Then
        assert result.success is True
        assert result.filepath.read_bytes() == payload
        assert 'Range' not in mock_get.call_args_list[1].kwargs['headers']

    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_server_ignoring_range_does_not_duplicate_data(self, mock_get, mock_head, tmp_path, make_zip_bytes):
        """A 200 answer to a Range request restarts the file instead of appending."""
        # Given — a stale partial file exists but the server sends the full body
        payload = make_zip_bytes(2048)
        (tmp_path / '194_Camille.zip.part').write_bytes(b'stale-partial-bytes')

        mock_head.return_value = Mock(status_code=200, headers=self._json_zip_headers(payload))

        response = Mock(status_code=200, headers=self._json_zip_headers(payload))
        response.iter_content = lambda chunk_size: [payload]
        mock_get.return_value = response

        # When
        result = DownloadService.download_dropbox_file(
            url='https://server.kidpixel.workers.dev/dropbox/a/b/file',
            timestamp='2026-09-21 09:57:14',
            output_dir=tmp_path,
            forced_filename='194 Camille.zip',
        )

        # Then
        assert result.success is True
        assert result.filepath.read_bytes() == payload

    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_retries_after_stall_and_resumes(self, mock_get, mock_head, tmp_path, make_zip_bytes, monkeypatch):
        """A stalled stream keeps what was received and resumes on the retry."""
        # Given
        import requests
        from config.settings import config

        monkeypatch.setattr(config, 'DOWNLOAD_RETRY_BACKOFF_S', 0.0, raising=False)
        payload = make_zip_bytes(4096)
        half = len(payload) // 2

        mock_head.return_value = Mock(status_code=200, headers=self._json_zip_headers(payload))

        def stalling_chunks(chunk_size):
            yield payload[:half]
            raise requests.exceptions.ReadTimeout('Read timed out')

        stalled = Mock(status_code=200, headers=self._json_zip_headers(payload))
        stalled.iter_content = stalling_chunks

        resumed = Mock(status_code=206, headers={
            'content-type': 'application/zip',
            'content-length': str(len(payload) - half),
            'content-range': f'bytes {half}-{len(payload) - 1}/{len(payload)}',
        })
        resumed.iter_content = lambda chunk_size: [payload[half:]]

        mock_get.side_effect = [stalled, resumed]

        # When
        result = DownloadService.download_dropbox_file(
            url='https://server.kidpixel.workers.dev/dropbox/a/b/file',
            timestamp='2026-09-21 15:45:33',
            output_dir=tmp_path,
            forced_filename='149 Camille.zip',
        )

        # Then
        assert result.success is True
        assert result.attempts == 2
        assert result.resumed_from == half
        assert result.filepath.read_bytes() == payload
        assert mock_get.call_args_list[1].kwargs['headers']['Range'] == f'bytes={half}-'

    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_incomplete_download_never_becomes_a_zip(self, mock_get, mock_head, tmp_path, make_zip_bytes, monkeypatch):
        """A truncated stream leaves a .part file, never a plausible .zip."""
        # Given
        from config.settings import config

        monkeypatch.setattr(config, 'DOWNLOAD_RETRY_BACKOFF_S', 0.0, raising=False)
        payload = make_zip_bytes(4096)

        mock_head.return_value = Mock(status_code=200, headers=self._json_zip_headers(payload))

        response = Mock(status_code=200, headers=self._json_zip_headers(payload))
        response.iter_content = lambda chunk_size: [payload[:1000]]
        mock_get.return_value = response

        # When
        result = DownloadService.download_dropbox_file(
            url='https://server.kidpixel.workers.dev/dropbox/a/b/file',
            timestamp='2026-09-21 19:11:49',
            output_dir=tmp_path,
            forced_filename='197 Camille.zip',
        )

        # Then
        assert result.success is False
        assert result.error_kind == 'incomplete'
        assert not (tmp_path / '197_Camille.zip').exists()
        assert (tmp_path / '197_Camille.zip.part').exists()

    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_resume_continues_across_url_switch(self, mock_get, mock_head, tmp_path, make_zip_bytes, monkeypatch):
        """A stalled R2 attempt keeps its .part and the Dropbox fallback resumes it.

        The serving worker (scripts/R2/server.js) does not implement HTTP Range:
        it always answers 200 with the full body. The only way to resume a large
        archive is therefore the Dropbox URL, which shares the same target name.
        """
        # Given
        import requests
        from config.settings import config

        monkeypatch.setattr(config, 'DOWNLOAD_RETRY_BACKOFF_S', 0.0, raising=False)
        # Above MIN_ZIP_SIZE_BYTES: the Dropbox fallback is a /scl/fo/ folder link
        payload = make_zip_bytes(1_500_000)
        half = len(payload) // 2
        headers = self._json_zip_headers(payload)

        mock_head.return_value = Mock(status_code=200, headers=headers)

        def stalling_chunks(chunk_size):
            yield payload[:half]
            raise requests.exceptions.ReadTimeout('Read timed out')

        stalled = Mock(status_code=200, headers=headers)
        stalled.iter_content = stalling_chunks

        resumed = Mock(status_code=206, headers={
            'content-type': 'application/zip',
            'content-length': str(len(payload) - half),
            'content-range': f'bytes {half}-{len(payload) - 1}/{len(payload)}',
        })
        resumed.iter_content = lambda chunk_size: [payload[half:]]
        # The R2 URL exhausts its attempts (the worker ignores Range, so each
        # retry restarts from 0 and stalls again), then the Dropbox link resumes.
        mock_get.side_effect = [stalled, stalled, stalled, resumed]

        # When — the R2 URL stalls, then the worker falls back to the Dropbox link
        r2_attempt = DownloadService.download_dropbox_file(
            url='https://server.kidpixel.workers.dev/dropbox/9529f228/6d6c3f94/file',
            timestamp='2026-09-21 16:47:14',
            output_dir=tmp_path,
            forced_filename='197 Camille.zip',
        )

        # Then — the partial transfer is kept for the next URL
        assert r2_attempt.success is False
        assert r2_attempt.error_kind == 'stalled'
        assert r2_attempt.attempts == 3
        assert (tmp_path / '197_Camille.zip.part').exists()
        assert not (tmp_path / '197_Camille.zip').exists()

        # When — the worker falls back to the Dropbox source link
        dropbox_attempt = DownloadService.download_dropbox_file(
            url='https://www.dropbox.com/scl/fo/tokenABC/Folder?rlkey=KEY&dl=0',
            timestamp='2026-09-21 16:47:14',
            output_dir=tmp_path,
            forced_filename='197 Camille.zip',
        )

        # Then — the partial data is reused instead of restarting from zero
        assert dropbox_attempt.success is True
        assert dropbox_attempt.resumed_from == half
        assert mock_get.call_args_list[3].kwargs['headers']['Range'] == f'bytes={half}-'
        assert dropbox_attempt.filepath.read_bytes() == payload
        assert not list(tmp_path.glob('*.part'))

    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_progress_updates_are_throttled(self, mock_get, mock_head, tmp_path, make_zip_bytes):
        """Progress callbacks are time-based, not emitted per 512KB chunk."""
        # Given — 10 chunks that would historically produce 10 updates
        payload = make_zip_bytes(512 * 1024 * 10)
        chunks = [payload[i:i + 512 * 1024] for i in range(0, len(payload), 512 * 1024)]

        mock_head.return_value = Mock(status_code=200, headers=self._json_zip_headers(payload))

        response = Mock(status_code=200, headers=self._json_zip_headers(payload))
        response.iter_content = lambda chunk_size: iter(chunks)
        mock_get.return_value = response

        updates = []

        # When
        result = DownloadService.download_dropbox_file(
            url='https://server.kidpixel.workers.dev/dropbox/a/b/file',
            timestamp='2026-09-21 16:47:14',
            output_dir=tmp_path,
            forced_filename='197 Camille.zip',
            progress_callback=lambda status, progress, message: updates.append((status, progress)),
        )

        # Then
        assert result.success is True
        downloading_updates = [u for u in updates if u[0] == 'downloading']
        assert len(downloading_updates) <= 3
        assert updates[-1] == ('completed', 100)

    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_forbidden_and_server_errors_are_typed(self, mock_get, mock_head, tmp_path):
        """403 and 500/503 are reported with distinct error kinds."""
        # Given
        mock_head.return_value = Mock(status_code=403, headers={})

        forbidden = Mock(status_code=403, reason='Forbidden', headers={})
        mock_get.return_value = forbidden

        # When
        result = DownloadService.download_dropbox_file(
            url='https://server.kidpixel.workers.dev/dropbox/a/b/file',
            timestamp='2026-09-21 10:00:00',
            output_dir=tmp_path,
        )

        # Then
        assert result.success is False
        assert result.error_kind == 'auth'
        assert result.status_code == 403

        # Given — a server error is retryable but still typed
        server_error = Mock(status_code=503, reason='Service Unavailable', headers={})
        mock_get.return_value = server_error

        # When
        failed = DownloadService.download_dropbox_file(
            url='https://server.kidpixel.workers.dev/dropbox/a/b/file',
            timestamp='2026-09-21 10:00:00',
            output_dir=tmp_path,
        )

        # Then
        assert failed.success is False
        assert failed.error_kind == 'http_error'
        assert failed.status_code == 503

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
    def test_download_dropbox_file_success(self, mock_get, mock_head, tmp_path, make_zip_bytes):
        """Test successful Dropbox file download."""
        # Given
        payload = make_zip_bytes(4096)

        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'attachment; filename="test.zip"',
            'content-length': str(len(payload)),
        }
        mock_head.return_value = mock_head_response

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'attachment; filename="test.zip"',
            'content-length': str(len(payload)),
        }
        mock_get_response.iter_content = lambda chunk_size: [payload]
        mock_get.return_value = mock_get_response

        # When
        result = DownloadService.download_dropbox_file(
            url='https://www.dropbox.com/s/abc/test.zip?dl=0',
            timestamp='2024-01-01 12:00:00',
            output_dir=tmp_path
        )

        # Then
        assert result.success is True
        assert result.status == 'completed'
        assert result.filepath is not None
        assert result.filepath.exists()
        assert result.size_bytes == len(payload)
        assert not list(tmp_path.glob('*.part'))

    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_download_forced_filename_overrides_header(self, mock_get, mock_head, tmp_path, make_zip_bytes):
        """When forced_filename is provided, it must be used (sanitized) instead of Content-Disposition."""
        # Given
        payload = make_zip_bytes(2048)

        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.headers = {
            'content-type': 'application/zip',
            'content-disposition': 'attachment; filename="ignored.zip"',
            'content-length': str(len(payload)),
        }
        mock_head.return_value = mock_head_response

        mock_get_response = Mock()
        mock_get_response.status_code = 200
        mock_get_response.headers = dict(mock_head_response.headers)
        mock_get_response.iter_content = lambda chunk_size: [payload]
        mock_get.return_value = mock_get_response

        # When
        result = DownloadService.download_dropbox_file(
            url='https://www.dropbox.com/s/abc/test.zip?dl=0',
            timestamp='2024-01-01 12:00:00',
            output_dir=tmp_path,
            forced_filename='61 Camille.zip'
        )

        # Then
        assert result.success is True
        assert result.filepath is not None
        assert result.filepath.name == '61_Camille.zip'
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_download_dropbox_file_network_error(self, mock_get, mock_head, tmp_path, monkeypatch):
        """Test download with network error."""
        # Given
        import requests
        from config.settings import config

        monkeypatch.setattr(config, 'DOWNLOAD_RETRY_BACKOFF_S', 0.0, raising=False)
        mock_head.side_effect = requests.exceptions.Timeout("Connection timeout")
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        # When
        result = DownloadService.download_dropbox_file(
            url='https://www.dropbox.com/s/abc/test.zip',
            timestamp='2024-01-01',
            output_dir=tmp_path
        )

        # Then
        assert result.success is False
        assert result.status == 'failed'
        assert result.error_kind == 'network'
        assert 'Network error' in result.message or 'error' in result.message.lower()
    
    @patch('services.download_service.requests.head')
    @patch('services.download_service.requests.get')
    def test_download_with_progress_callback(self, mock_get, mock_head, tmp_path, make_zip_bytes):
        """Test download with progress callback."""
        # Given
        payload = make_zip_bytes(8192)
        half = len(payload) // 2

        mock_head.return_value = Mock(
            status_code=200,
            headers={
                'content-type': 'application/zip',
                'content-disposition': 'filename="test.zip"',
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
        mock_response.iter_content = lambda chunk_size: [payload[:half], payload[half:]]
        mock_get.return_value = mock_response

        progress_updates = []

        def track_progress(status, progress, message):
            progress_updates.append((status, progress))

        # When
        result = DownloadService.download_dropbox_file(
            url='https://www.dropbox.com/s/abc/test.zip',
            timestamp='2024-01-01',
            output_dir=tmp_path,
            progress_callback=track_progress
        )

        # Then
        assert result.success is True
        assert len(progress_updates) > 0
        assert any(status == 'downloading' for status, _ in progress_updates)
        assert progress_updates[-1] == ('completed', 100)
