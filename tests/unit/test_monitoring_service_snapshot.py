#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the MonitoringService snapshot cache.

Context: /api/system_monitor used to run psutil (100ms blocking cpu_percent),
NVML and a mkdir on every request. While a large download saturated the
process, those calls made the CPU/GPU/RAM widget freeze. The snapshot cache
keeps the HTTP path free of any sampling call.
"""

from unittest.mock import patch

import pytest

from services import monitoring_service as monitoring_module
from services.monitoring_service import MonitoringService


SAMPLE_STATUS = {
    'cpu_percent': 12.5,
    'memory': {'percent': 40.0, 'used_gb': 6.4, 'total_gb': 16.0, 'available_gb': 9.6},
    'gpu': None,
    'disk': {'percent': 55.0, 'used_gb': 100.0, 'total_gb': 200.0, 'free_gb': 100.0},
    'timestamp': '2026-09-21T19:11:49+00:00',
}


@pytest.fixture(autouse=True)
def reset_snapshot():
    """Isolate the module-level snapshot between tests."""
    monitoring_module._SYSTEM_SNAPSHOT = None
    monitoring_module._SNAPSHOT_MONOTONIC = 0.0
    yield
    monitoring_module._SYSTEM_SNAPSHOT = None
    monitoring_module._SNAPSHOT_MONOTONIC = 0.0


class TestSystemStatusCache:
    """The HTTP-facing accessor must never sample the system."""

    def test_cached_status_serves_last_snapshot(self):
        # Given — a published snapshot
        with patch.object(MonitoringService, 'get_system_status', return_value=dict(SAMPLE_STATUS)) as sampler:
            MonitoringService.refresh_snapshot()
        assert sampler.call_count == 1

        # When — a request reads the metrics
        with patch.object(MonitoringService, 'get_system_status', side_effect=AssertionError('request path must not sample')):
            payload = MonitoringService.get_system_status_cached()

        # Then
        assert payload['cpu_percent'] == 12.5
        assert payload['memory']['percent'] == 40.0
        assert isinstance(payload['snapshot_age_s'], float)

    def test_cached_status_samples_once_when_empty(self):
        # Given — no snapshot yet (startup race)
        # When
        with patch.object(MonitoringService, 'get_system_status', return_value=dict(SAMPLE_STATUS)) as sampler:
            payload = MonitoringService.get_system_status_cached()

        # Then
        assert sampler.call_count == 1
        assert payload['cpu_percent'] == 12.5

    def test_cached_status_raises_when_sampling_fails(self):
        # Given / When / Then
        with patch.object(MonitoringService, 'get_system_status', side_effect=RuntimeError('psutil down')):
            with pytest.raises(RuntimeError):
                MonitoringService.get_system_status_cached()

    def test_refresh_snapshot_returns_none_on_failure(self):
        # Given / When
        with patch.object(MonitoringService, 'get_system_status', side_effect=RuntimeError('boom')):
            result = MonitoringService.refresh_snapshot()

        # Then
        assert result is None
        assert monitoring_module._SYSTEM_SNAPSHOT is None


class TestCpuUsageIsNonBlocking:
    """psutil.cpu_percent must be sampled without a blocking interval."""

    def test_cpu_usage_uses_interval_none(self):
        # Given
        captured = {}

        def fake_cpu_percent(interval=None):
            captured['interval'] = interval
            return 42.24

        # When
        with patch.object(monitoring_module.psutil, 'cpu_percent', fake_cpu_percent):
            value = MonitoringService.get_cpu_usage()

        # Then
        assert value == 42.2
        assert captured['interval'] is None

    def test_cpu_usage_returns_zero_on_error(self):
        # Given / When
        with patch.object(monitoring_module.psutil, 'cpu_percent', side_effect=RuntimeError('nope')):
            value = MonitoringService.get_cpu_usage()

        # Then
        assert value == 0.0


class TestSnapshotSampler:
    """The sampler publishes snapshots from a daemon thread."""

    def test_sampler_publishes_without_waiting_for_requests(self):
        # Given
        with patch.object(MonitoringService, 'get_system_status', return_value=dict(SAMPLE_STATUS)):
            # When
            MonitoringService.start_snapshot_sampler(interval_s=0.5)

            # Then — the sampler primes a snapshot immediately
            assert monitoring_module._SYSTEM_SNAPSHOT is not None
            payload = MonitoringService.get_system_status_cached()
            assert payload['cpu_percent'] == 12.5

        MonitoringService.stop_snapshot_sampler()
