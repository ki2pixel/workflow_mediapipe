#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for PerformanceService.
Validates system profiling, metric recording, alert thresholds, and concurrency safety.
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch, MagicMock

from services.performance_service import (
    PerformanceService,
    PROFILING_STATS,
    PROFILING_LOCK,
    PERFORMANCE_HISTORY,
    PERFORMANCE_LOCK,
    PERFORMANCE_ALERTS,
    ALERT_THRESHOLDS,
    ALERT_THRESHOLD_LOCK,
)


class TestPerformanceServiceProfiling:
    """Test profiling context manager and stats."""

    def setup_method(self):
        PerformanceService.reset_profiling_stats()

    def test_profile_section_records_elapsed_time(self):
        with PerformanceService.profile_section("test_op"):
            pass
        # Re-read globals after reset_profiling_stats may have replaced them
        from services.performance_service import PROFILING_STATS, PROFILING_LOCK
        with PROFILING_LOCK:
            stats = PROFILING_STATS["test_op"]
            assert stats["calls"] == 1
            assert stats["total_time"] > 0
            assert stats["avg_time"] == stats["total_time"]

    def test_profile_section_increments_call_count(self):
        for _ in range(3):
            with PerformanceService.profile_section("repeated_op"):
                pass
        from services.performance_service import PROFILING_STATS, PROFILING_LOCK
        with PROFILING_LOCK:
            stats = PROFILING_STATS["repeated_op"]
            assert stats["calls"] == 3

    def test_reset_profiling_stats_clears_data(self):
        with PerformanceService.profile_section("op"):
            pass
        PerformanceService.reset_profiling_stats()
        from services.performance_service import PROFILING_STATS, PROFILING_LOCK
        with PROFILING_LOCK:
            assert len(PROFILING_STATS) == 0

    def test_get_profiling_summary_empty(self):
        PerformanceService.reset_profiling_stats()
        summary = PerformanceService.get_profiling_summary()
        assert summary["total_sections"] == 0

    def test_get_profiling_summary_sorted_by_total_time(self):
        PerformanceService.reset_profiling_stats()
        with PerformanceService.profile_section("fast"):
            pass
        with PerformanceService.profile_section("slow"):
            time.sleep(0.01)
        summary = PerformanceService.get_profiling_summary()
        assert summary["total_sections"] == 2
        # "slow" should appear first (higher total_time)
        assert summary["top_sections"][0]["name"] == "slow"
        assert summary["top_sections"][1]["name"] == "fast"


class TestPerformanceServiceRecording:
    """Test metric recording and history."""

    def setup_method(self):
        with PERFORMANCE_LOCK:
            PERFORMANCE_HISTORY.clear()
        with PERFORMANCE_LOCK:
            PERFORMANCE_ALERTS.clear()

    def test_record_api_response_stores_metric(self):
        PerformanceService.record_api_response_time("/api/test", 42.5, 200)
        with PERFORMANCE_LOCK:
            assert len(PERFORMANCE_HISTORY) == 1
            metric = PERFORMANCE_HISTORY[0]
            assert metric["endpoint"] == "/api/test"
            assert metric["response_time_ms"] == 42.5
            assert metric["status_code"] == 200
            assert metric["is_error"] is False

    def test_record_api_response_marks_error(self):
        PerformanceService.record_api_response_time("/api/test", 100.0, 500)
        with PERFORMANCE_LOCK:
            metric = PERFORMANCE_HISTORY[0]
            assert metric["is_error"] is True

    def test_record_system_metrics_stores_data(self):
        with patch("services.performance_service.MonitoringService.get_system_status") as mock_status:
            mock_status.return_value = {
                "cpu_percent": 45.0,
                "memory": {"percent": 60.0},
                "disk": {"percent": 30.0},
            }
            PerformanceService.record_system_metrics()
        with PERFORMANCE_LOCK:
            assert len(PERFORMANCE_HISTORY) == 1
            metric = PERFORMANCE_HISTORY[0]
            assert metric["type"] == "system"
            assert metric["cpu_percent"] == 45.0
            assert metric["memory_percent"] == 60.0

    def test_history_bounded_by_deque_maxlen(self):
        with PERFORMANCE_LOCK:
            PERFORMANCE_HISTORY.clear()
        for i in range(150):
            PerformanceService.record_api_response_time(f"/api/{i}", 1.0, 200)
        with PERFORMANCE_LOCK:
            assert len(PERFORMANCE_HISTORY) == 100  # maxlen=100


class TestPerformanceServiceAlerts:
    """Test performance alert generation and threshold management."""

    def setup_method(self):
        with PERFORMANCE_LOCK:
            PERFORMANCE_ALERTS.clear()

    def test_slow_response_triggers_alert(self):
        with ALERT_THRESHOLD_LOCK:
            ALERT_THRESHOLDS["response_time_ms"] = 100.0
        PerformanceService.record_api_response_time("/api/test", 500.0, 200)
        with PERFORMANCE_LOCK:
            alerts = list(PERFORMANCE_ALERTS)
        assert len(alerts) >= 1
        slow_alerts = [a for a in alerts if a["type"] == "slow_response"]
        assert len(slow_alerts) >= 1

    def test_fast_response_no_alert(self):
        with ALERT_THRESHOLD_LOCK:
            ALERT_THRESHOLDS["response_time_ms"] = 1000.0
        with PERFORMANCE_LOCK:
            PERFORMANCE_ALERTS.clear()
        PerformanceService.record_api_response_time("/api/test", 50.0, 200)
        with PERFORMANCE_LOCK:
            slow_alerts = [a for a in PERFORMANCE_ALERTS if a["type"] == "slow_response"]
        assert len(slow_alerts) == 0

    def test_update_alert_thresholds(self):
        PerformanceService.update_alert_thresholds({"cpu_percent": 75.0})
        with ALERT_THRESHOLD_LOCK:
            assert ALERT_THRESHOLDS["cpu_percent"] == 75.0

    def test_update_alert_thresholds_ignores_unknown_keys(self):
        before = dict(ALERT_THRESHOLDS)
        PerformanceService.update_alert_thresholds({"nonexistent_key": 999.0})
        with ALERT_THRESHOLD_LOCK:
            assert ALERT_THRESHOLDS == before

    def test_clear_alerts(self):
        with PERFORMANCE_LOCK:
            PERFORMANCE_ALERTS.append({"type": "test", "message": "test"})
        PerformanceService.clear_alerts()
        with PERFORMANCE_LOCK:
            assert len(PERFORMANCE_ALERTS) == 0

    def test_alerts_bounded_by_maxlen(self):
        with PERFORMANCE_LOCK:
            PERFORMANCE_ALERTS.clear()
        for i in range(100):
            with PERFORMANCE_LOCK:
                PERFORMANCE_ALERTS.append({"type": f"alert_{i}", "message": str(i)})
        with PERFORMANCE_LOCK:
            assert len(PERFORMANCE_ALERTS) <= 50


class TestPerformanceServiceConcurrency:
    """Test thread-safety of shared state mutations."""

    def test_concurrent_record_api_response(self):
        with PERFORMANCE_LOCK:
            PERFORMANCE_HISTORY.clear()

        def worker(idx):
            PerformanceService.record_api_response_time(f"/api/{idx}", float(idx), 200)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        with PERFORMANCE_LOCK:
            assert len(PERFORMANCE_HISTORY) == 20

    def test_concurrent_update_thresholds(self):
        def worker(val):
            PerformanceService.update_alert_thresholds({"cpu_percent": float(val)})

        threads = [threading.Thread(target=worker, args=(i + 50.0,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        with ALERT_THRESHOLD_LOCK:
            assert 50.0 <= ALERT_THRESHOLDS["cpu_percent"] <= 60.0


class TestPerformanceServiceDashboard:
    """Test dashboard statistics aggregation."""

    def test_get_dashboard_stats_includes_summary(self):
        with PERFORMANCE_LOCK:
            PERFORMANCE_HISTORY.clear()
        PerformanceService.record_api_response_time("/api/a", 10.0, 200)
        PerformanceService.record_api_response_time("/api/b", 20.0, 500)
        stats = PerformanceService.get_dashboard_stats()
        assert "summary" in stats
        assert stats["summary"]["total_api_calls"] == 2
        assert stats["summary"]["total_errors"] == 1
        assert stats["summary"]["avg_response_time_ms"] == 15.0

    def test_get_performance_metrics_structure(self):
        metrics = PerformanceService.get_performance_metrics()
        assert "profiling_stats" in metrics
        assert "cache_stats" in metrics
        assert "system_performance" in metrics
        assert "timestamp" in metrics


class TestPerformanceServiceHistorical:
    """Test historical data retrieval."""

    def test_get_historical_data_filters_by_type(self):
        with PERFORMANCE_LOCK:
            PERFORMANCE_HISTORY.clear()
        PerformanceService.record_api_response_time("/api/a", 1.0, 200)
        with patch("services.performance_service.MonitoringService.get_system_status") as mock_status:
            mock_status.return_value = {
                "cpu_percent": 50.0,
                "memory": {"percent": 70.0},
                "disk": {"percent": 20.0},
            }
            PerformanceService.record_system_metrics()

        api_data = PerformanceService.get_historical_data("api", 10)
        assert all(m.get("endpoint") for m in api_data["data"])

        sys_data = PerformanceService.get_historical_data("system", 10)
        assert all(m.get("type") == "system" for m in sys_data["data"])
