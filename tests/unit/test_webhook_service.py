#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for WebhookService.
Validates JSON fetching, caching, URL classification, and error handling.
"""

import time
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from services.webhook_service import (
    fetch_records,
    get_service_status,
    _classify_url_type,
    _normalize_timestamp,
    _validate_and_format,
)


class TestWebhookURLExtraction:
    """Test URL classification."""

    def test_classify_fromsmash(self):
        result = _classify_url_type("https://fromsmash.com/somefile")
        assert result == "fromsmash"

    def test_classify_swisstransfer(self):
        result = _classify_url_type("https://www.swisstransfer.com/d/abc123")
        assert result == "swisstransfer"

    def test_classify_dropbox_direct(self):
        result = _classify_url_type("https://www.dropbox.com/s/somefile")
        assert result == "dropbox"

    def test_classify_dropbox_cdn(self):
        result = _classify_url_type("https://dl.dropboxusercontent.com/cdn/file")
        assert result == "dropbox"

    def test_classify_worker_dropbox(self):
        result = _classify_url_type("https://something.workers.dev/dropbox/abc/file")
        assert result == "dropbox"

    def test_classify_external_fallback(self):
        result = _classify_url_type("https://example.com/file.zip")
        assert result == "external"

    def test_classify_url_error_fallback(self):
        result = _classify_url_type(None)
        assert result == "external"


class TestWebhookTimestampNormalization:
    """Test timestamp normalization."""

    def test_normalize_iso_with_tz(self):
        result = _normalize_timestamp("2025-10-17T12:34:13+0200")
        assert result is not None

    def test_normalize_iso_with_z(self):
        result = _normalize_timestamp("2025-10-17T12:34:13Z")
        assert result is not None

    def test_normalize_simple_format(self):
        result = _normalize_timestamp("2025-10-17 12:34:13")
        assert result == "2025-10-17 12:34:13"

    def test_normalize_none(self):
        assert _normalize_timestamp(None) is None

    def test_normalize_empty(self):
        assert _normalize_timestamp("") is None

    def test_normalize_garbage_fallback(self):
        result = _normalize_timestamp("not-a-date")
        assert result == "not-a-date"


class TestWebhookValidation:
    """Test JSON validation and formatting."""

    def test_validate_empty_inputs(self):
        assert _validate_and_format(None) == []
        assert _validate_and_format("string") == []
        assert _validate_and_format({}) == []

    def test_validate_new_schema(self):
        items = [
            {
                "source_url": "https://example.com/video.mp4",
                "r2_url": "https://r2.example.com/video.mp4",
                "original_filename": "video.mp4",
                "provider": "dropbox",
                "created_at": "2025-10-17T12:34:13+0200",
            }
        ]
        rows = _validate_and_format(items)
        assert len(rows) == 1
        assert rows[0]["url"] == "https://r2.example.com/video.mp4"
        assert rows[0]["provider"] == "dropbox"
        assert rows[0]["url_type"] == "dropbox"

    def test_validate_new_schema_r2_only(self):
        items = [
            {
                "source_url": "",
                "r2_url": "https://r2.example.com/video.mp4",
                "provider": "",
                "created_at": "2025-10-17T12:34:13+0200",
            }
        ]
        rows = _validate_and_format(items)
        assert len(rows) == 1
        assert rows[0]["url"] == "https://r2.example.com/video.mp4"
        # provider blank, url_type falls back to classification
        assert rows[0]["url_type"] == "external"

    def test_validate_legacy_schema(self):
        items = [
            {
                "url": "https://fromsmash.com/file",
                "timestamp": "2025-10-17 12:34:13",
                "source": "webhook",
            }
        ]
        rows = _validate_and_format(items)
        assert len(rows) == 1
        assert rows[0]["url"] == "https://fromsmash.com/file"
        assert rows[0]["url_type"] == "fromsmash"

    def test_validate_legacy_no_url_skipped(self):
        items = [
            {
                "url": "",
                "timestamp": "2025-10-17 12:34:13",
                "source": "webhook",
            }
        ]
        rows = _validate_and_format(items)
        assert len(rows) == 0

    def test_validate_skips_invalid_items(self):
        items = [
            "not a dict",
            {"url": "https://valid.com/file"},
            None,
        ]
        rows = _validate_and_format(items)
        assert len(rows) == 1
        assert rows[0]["url"] == "https://valid.com/file"


class TestWebhookFetchRecords:
    """Test fetch_records with successful and failing HTTP calls."""

    def setup_method(self):
        import services.webhook_service as ws
        with ws._lock:
            ws._cache_data = None
            ws._cache_fetched_at = 0.0
            ws._last_error = None

    def test_fetch_successful(self):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "source_url": "https://www.dropbox.com/scl/fi/abc/video.mp4",
                "provider": "dropbox",
                "created_at": "2025-10-17T12:34:13+02:00",
            }
        ]
        with patch("requests.get", return_value=mock_response):
            rows = fetch_records()
        assert rows is not None
        assert len(rows) == 1
        assert rows[0]["url_type"] == "dropbox"

    def test_fetch_uses_cache_within_ttl(self):
        import services.webhook_service as ws
        with ws._lock:
            ws._cache_data = [{"url": "cached", "timestamp": "", "source": "webhook", "url_type": "external"}]
            ws._cache_fetched_at = time.time()
        rows = fetch_records()
        assert rows[0]["url"] == "cached"

    def test_fetch_http_error_returns_none(self):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.HTTPError("Server error")
        with patch("requests.get", return_value=mock_response):
            rows = fetch_records()
        assert rows is None

    def test_fetch_connection_error_returns_none(self):
        with patch("requests.get", side_effect=requests.ConnectionError("Timeout")):
            rows = fetch_records()
        assert rows is None


class TestWebhookServiceStatus:
    """Test get_service_status."""

    def test_returns_shallow_copy(self):
        status1 = get_service_status()
        status2 = get_service_status()
        assert status1 is not status2
        assert status1 == status2

    def test_status_has_expected_keys(self):
        status = get_service_status()
        assert "available" in status
        assert "error" in status
        assert "records" in status
