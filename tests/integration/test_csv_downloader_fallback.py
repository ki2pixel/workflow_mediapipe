#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for the CSV download worker fallback chain.

Context: some .zip files are missing on the Cloudflare worker side (the R2 copy
is short-lived) while the original Dropbox link is valid. The worker must fall
back to the source URL, keep the failure visible in the UI message, and report
the typed failure so the monitor can apply a cooldown.

Failure bookkeeping is intercepted on the CSVService class: modules are resolved
at call time because other test files reload config/services in sys.modules.
"""

import importlib

import pytest
from unittest.mock import patch

from services.download_service import DownloadResult


R2_URL = 'https://server.kidpixel.workers.dev/dropbox/9529f228/6d6c3f94/file'
SOURCE_URL = 'https://www.dropbox.com/scl/fo/vbkfcn45bm6mbdipxy2wj/APM1TkkmWZGK-rOQteEkfzo?rlkey=x&dl=0'
TIMESTAMP = '2026-09-21 16:47:14'


def _downloader_module():
    """Resolve the downloader module currently registered (reload-safe)."""
    return importlib.import_module('services.csv_downloader')


@pytest.fixture
def failure_sink(monkeypatch):
    """Capture failure bookkeeping emitted by the download worker."""
    csv_service_cls = _downloader_module().CSVService
    recorded = []

    def fake_record(url, kind, status_code=None, error=''):
        recorded.append({'url': url, 'kind': kind, 'status_code': status_code, 'error': error})
        return True

    monkeypatch.setattr(csv_service_cls, 'record_download_failure', staticmethod(fake_record))
    monkeypatch.setattr(csv_service_cls, 'clear_download_failure', staticmethod(lambda url: None))
    return recorded


@pytest.fixture
def download_dir(tmp_path, monkeypatch):
    """Redirect the worker output directory to a temp folder."""
    target = tmp_path / 'downloads'
    target.mkdir()
    monkeypatch.setattr(_downloader_module(), 'LOCAL_DOWNLOADS_DIR', target)
    return target


def _failed(kind: str, status_code=None, message: str = 'failed', url: str = R2_URL) -> DownloadResult:
    return DownloadResult(
        success=False,
        download_id='csv_test',
        filename='197_Camille.zip',
        filepath=None,
        size_bytes=0,
        message=message,
        status='failed',
        status_code=status_code,
        error_kind=kind,
        attempts=1,
        url=url,
    )


def _succeeded(filename: str = '197_Camille.zip') -> DownloadResult:
    return DownloadResult(
        success=True,
        download_id='csv_test',
        filename=filename,
        filepath=None,
        size_bytes=2048,
        message=f'File {filename} (2.0KB) downloaded',
        status='completed',
        status_code=200,
        attempts=1,
        url=SOURCE_URL,
    )


class TestCSVDownloaderFallback:
    """R2 first, Dropbox source as fallback, typed failures reported."""

    @patch('services.csv_downloader.DownloadService.download_dropbox_file')
    def test_falls_back_to_source_url_when_r2_is_missing(self, mock_download, failure_sink, download_dir):
        # Given — the R2 object 404s, the Dropbox link works
        mock_download.side_effect = [_failed('not_found', 404, 'HTTP 404 (not_found) for url'), _succeeded()]

        updates = []
        with patch('services.csv_downloader.CSVService.update_csv_download',
                   side_effect=lambda download_id, status, **kwargs: updates.append((status, kwargs))):
            # When
            _downloader_module().execute_csv_download_worker(R2_URL, TIMESTAMP, SOURCE_URL, '197 Camille.zip')

        # Then — both URLs were attempted, in order
        assert mock_download.call_count == 2
        assert mock_download.call_args_list[0].kwargs['url'] == R2_URL
        assert mock_download.call_args_list[1].kwargs['url'] == SOURCE_URL

        # The user sees why the fallback was used
        completed = [kwargs for status, kwargs in updates if status == 'completed']
        assert len(completed) == 1
        assert 'repli Dropbox' in completed[0]['message']

        # The download eventually succeeded: no failure is kept (and any previous
        # trace is cleared), so the URL is not delayed by a cooldown.
        assert failure_sink == []

    @patch('services.csv_downloader.DownloadService.download_dropbox_file')
    def test_records_failure_when_every_url_fails(self, mock_download, failure_sink, download_dir):
        # Given — neither the R2 object nor the Dropbox link works
        mock_download.side_effect = [
            _failed('not_found', 404, 'HTTP 404 (not_found)'),
            _failed('stalled', None, 'Download stalled (timeout after 60s with no data received)', url=SOURCE_URL),
        ]

        with patch('services.csv_downloader.CSVService.update_csv_download'):
            # When
            _downloader_module().execute_csv_download_worker(R2_URL, TIMESTAMP, SOURCE_URL, '197 Camille.zip')

        # Then — both attempts are reported with their typed kind and URL
        assert len(failure_sink) == 2
        assert {entry['kind'] for entry in failure_sink} == {'not_found', 'stalled'}
        assert {entry['url'] for entry in failure_sink} == {R2_URL, SOURCE_URL}

    @patch('services.csv_downloader.DownloadService.download_dropbox_file')
    def test_known_missing_r2_object_uses_source_url_first(self, mock_download, failure_sink, download_dir, monkeypatch):
        # Given — the R2 object was already reported missing by a previous attempt
        csv_service_cls = _downloader_module().CSVService
        normalized_r2 = csv_service_cls._normalize_url(R2_URL)
        monkeypatch.setattr(
            csv_service_cls,
            'get_download_failure_map',
            staticmethod(lambda: {normalized_r2: {'kind': 'not_found', 'attempts': 1, 'status_code': 404}}),
        )
        mock_download.return_value = _succeeded()

        with patch('services.csv_downloader.CSVService.update_csv_download') as mock_update:
            # When
            _downloader_module().execute_csv_download_worker(R2_URL, TIMESTAMP, SOURCE_URL, '197 Camille.zip')

        # Then — the Dropbox link is tried first, without replaying the R2 request
        assert mock_download.call_count == 1
        assert mock_download.call_args_list[0].kwargs['url'] == SOURCE_URL
        completed = [call for call in mock_update.call_args_list if call.args[1] == 'completed']
        assert 'repli Dropbox' in completed[0].kwargs['message']

    @patch('services.csv_downloader.DownloadService.download_dropbox_file')
    def test_success_on_first_url_records_no_failure(self, mock_download, failure_sink, download_dir):
        # Given
        mock_download.return_value = _succeeded()

        with patch('services.csv_downloader.CSVService.update_csv_download') as mock_update:
            # When
            _downloader_module().execute_csv_download_worker(R2_URL, TIMESTAMP, SOURCE_URL, '197 Camille.zip')

        # Then
        assert mock_download.call_count == 1
        assert failure_sink == []
        completed = [call for call in mock_update.call_args_list if call.args[1] == 'completed']
        assert len(completed) == 1
        # No fallback hint when the primary URL worked
        assert 'repli Dropbox' not in completed[0].kwargs['message']
