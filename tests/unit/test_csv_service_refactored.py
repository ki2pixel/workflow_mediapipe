#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for refactored CSVService methods.
Tests the URL conversion and normalization functions moved from app_new.py.
"""
import pytest
from services.csv_service import CSVService


class TestURLConversion:
    """Test URL conversion methods."""

    def test_rewrite_dropbox_to_dl_host_basic(self):
        """Test basic Dropbox URL rewriting."""
        url = "https://www.dropbox.com/s/abc123/file.zip?dl=0"
        result = CSVService.rewrite_dropbox_to_dl_host(url)
        assert "dl.dropboxusercontent.com" in result
        assert "/s/abc123/file.zip" in result

    def test_rewrite_dropbox_to_dl_host_folder_link(self):
        """Test that folder links are not rewritten."""
        url = "https://www.dropbox.com/scl/fo/abc123?rlkey=xyz&dl=0"
        result = CSVService.rewrite_dropbox_to_dl_host(url)
        # Folder links should NOT be rewritten
        assert "www.dropbox.com" in result
        assert "dl.dropboxusercontent.com" not in result

    def test_rewrite_dropbox_to_dl_host_already_dl(self):
        """Test URL that's already dl.dropboxusercontent.com."""
        url = "https://dl.dropboxusercontent.com/s/abc123/file.zip"
        result = CSVService.rewrite_dropbox_to_dl_host(url)
        assert result == url


class TestURLNormalization:
    """Test URL normalization."""

    def test_normalize_url_basic(self):
        """Test basic URL normalization."""
        url = "https://example.com/file.zip"
        result = CSVService._normalize_url(url)
        assert result == "https://example.com/file.zip"

    def test_normalize_url_dropbox_dl_param(self):
        """Test Dropbox URL gets dl=1 parameter."""
        url = "https://www.dropbox.com/s/abc/file.zip?dl=0"
        result = CSVService._normalize_url(url)
        assert "dl=1" in result
        # Should not have dl=0
        assert "dl=0" not in result

    def test_normalize_url_html_unescape(self):
        """Test HTML entity unescaping."""
        url = "https://example.com/file.zip?foo=bar&amp;baz=qux"
        result = CSVService._normalize_url(url)
        # Should convert &amp; to &
        assert "&amp;" not in result
        assert "&" in result

    def test_normalize_url_removes_empty_params(self):
        """Test removal of empty query parameters."""
        url = "https://example.com/file.zip?foo=&bar=value"
        result = CSVService._normalize_url(url)
        # Empty params should be removed (except special ones like rlkey)
        assert "foo=" not in result or "foo" not in result

    def test_normalize_url_removes_trailing_slash(self):
        """Test removal of trailing slash for non-root paths."""
        url = "https://example.com/path/"
        result = CSVService._normalize_url(url)
        assert not result.endswith("/path/")

    def test_normalize_url_sorts_params(self):
        """Test query parameter sorting for determinism."""
        url = "https://example.com/file.zip?z=1&a=2&m=3"
        result = CSVService._normalize_url(url)
        # Params should be sorted alphabetically
        # Check that the query string is properly formed
        assert "?" in result
        query_part = result.split("?")[1]
        # Should have sorted params
        assert query_part.index("a=") < query_part.index("m=") < query_part.index("z=")
