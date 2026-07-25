#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for CacheService.
Validates Flask-Caching integration, statistics tracking, and directory search.
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock

from services.cache_service import CacheService, cache_stats


class TestCacheServiceInitialize:
    """Test CacheService initialization."""

    def test_initialize_sets_cache_instance(self):
        mock_cache = Mock()
        CacheService.initialize(mock_cache)
        # Verify cache_instance was set
        import services.cache_service as cs
        with cs._stats_lock:
            assert cs.cache_instance is mock_cache


class TestCacheServiceStatistics:
    """Test cache statistics tracking."""

    def setup_method(self):
        CacheService.reset_stats()

    def test_get_cache_stats_defaults(self):
        stats = CacheService.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["errors"] == 0
        assert stats["hit_rate_percent"] == 0
        assert stats["total_requests"] == 0

    def test_get_cache_stats_with_data(self):
        import services.cache_service as cs
        with cs._stats_lock:
            cs.cache_stats["hits"] = 42
            cs.cache_stats["misses"] = 8
        stats = CacheService.get_cache_stats()
        assert stats["hits"] == 42
        assert stats["misses"] == 8
        assert stats["total_requests"] == 50
        assert stats["hit_rate_percent"] == 84.0

    def test_reset_stats(self):
        import services.cache_service as cs
        with cs._stats_lock:
            cs.cache_stats["hits"] = 99
            cs.cache_stats["misses"] = 1
        CacheService.reset_stats()
        stats = CacheService.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["uptime_seconds"] >= 0

    def test_clear_cache_when_no_instance(self):
        import services.cache_service as cs
        with cs._stats_lock:
            cs.cache_instance = None
        CacheService.clear_cache()

    def test_clear_cache_calls_clear_on_instance(self):
        mock_cache = Mock()
        CacheService.initialize(mock_cache)
        CacheService.clear_cache()
        mock_cache.clear.assert_called_once()


class TestCacheServiceFrontendConfig:
    """Test get_cached_frontend_config with cache interactions."""

    def test_generates_fresh_config_when_no_cache(self):
        import services.cache_service as cs
        with cs._stats_lock:
            cs.cache_instance = None
        with patch("config.workflow_commands.WorkflowCommandsConfig") as MockConfig:
            instance = MockConfig.return_value
            instance.get_config.return_value = {
                "STEP1": {
                    "display_name": "Test",
                    "cmd": ["python", "test.py"],
                }
            }
            result = CacheService.get_cached_frontend_config()
            assert "STEP1" in result
            assert result["STEP1"]["display_name"] == "Test"

    def test_returns_cached_config_on_cache_hit(self):
        mock_cache = Mock()
        mock_cache.get.return_value = {"STEP1": {"display_name": "Cached"}}
        CacheService.initialize(mock_cache)
        import services.cache_service as cs
        cs.cache_stats["hits"] = 0
        result = CacheService.get_cached_frontend_config()
        assert result["STEP1"]["display_name"] == "Cached"
        mock_cache.get.assert_called_once_with("frontend_config")

    def test_sanitizes_unsafe_step_keys(self):
        import services.cache_service as cs
        with cs._stats_lock:
            cs.cache_instance = None
        with patch("config.workflow_commands.WorkflowCommandsConfig") as MockConfig:
            instance = MockConfig.return_value
            instance.get_config.return_value = {
                "STEP<script>": {"display_name": "malicious"},
                "STEP1": {"display_name": "safe"},
            }
            result = CacheService.get_cached_frontend_config()
            assert "STEP1" in result
            assert "STEP<script>" not in result

    def test_handles_empty_config(self):
        import services.cache_service as cs
        with cs._stats_lock:
            cs.cache_instance = None
        with patch("config.workflow_commands.WorkflowCommandsConfig") as MockConfig:
            instance = MockConfig.return_value
            instance.get_config.return_value = {}
            result = CacheService.get_cached_frontend_config()
            assert result == {}


class TestCacheServiceLogContent:
    """Test get_cached_log_content."""

    def test_returns_from_cache_when_available(self):
        mock_cache = Mock()
        mock_cache.get.return_value = {"content": "cached log"}
        CacheService.initialize(mock_cache)
        import services.cache_service as cs
        cs.cache_stats["hits"] = 0
        result = CacheService.get_cached_log_content("STEP1", 0)
        assert result["content"] == "cached log"

    def test_fetches_from_service_on_cache_miss(self):
        import services.cache_service as cs
        with cs._stats_lock:
            cs.cache_instance = None
        with patch("services.workflow_service.WorkflowService.get_step_log_file") as mock_svc:
            mock_svc.return_value = {"content": "fresh log"}
            result = CacheService.get_cached_log_content("STEP1", 0)
            assert result["content"] == "fresh log"
            mock_svc.assert_called_once_with("STEP1", 0)


class TestCacheServiceStepStatus:
    """Test get_cached_step_status."""

    def test_returns_step_info_copy(self):
        mock_state = Mock()
        mock_state.get_step_info.return_value = {"status": "idle", "key": "val"}
        with patch("services.cache_service.get_workflow_state", return_value=mock_state):
            result = CacheService.get_cached_step_status("STEP1")
            assert result["status"] == "idle"
            # Should be a copy, not the original
            assert result is not mock_state.get_step_info.return_value

    def test_raises_for_nonexistent_step(self):
        mock_state = Mock()
        mock_state.get_step_info.return_value = None
        with patch("services.cache_service.get_workflow_state", return_value=mock_state):
            with pytest.raises(ValueError, match="not found"):
                CacheService.get_cached_step_status("NONEXISTENT")


class TestCacheServiceInvalidation:
    """Test cache invalidation."""

    def test_invalidate_noop_when_no_cache_instance(self):
        import services.cache_service as cs
        with cs._stats_lock:
            cs.cache_instance = None
        CacheService.invalidate_step_cache("STEP1")

    def test_invalidate_deletes_keys(self):
        mock_cache = Mock()
        CacheService.initialize(mock_cache)
        CacheService.invalidate_step_cache("STEP1")
        calls = [call[0][0] for call in mock_cache.delete.call_args_list]
        assert "step_status:STEP1" in calls
        assert any(key.startswith("log_content:STEP1") for key in calls)
