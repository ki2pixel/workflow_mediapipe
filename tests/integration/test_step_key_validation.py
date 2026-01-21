#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for frontend step_key sanitization in CacheService."""

import pytest

from services.cache_service import CacheService, _SAFE_STEP_KEY_PATTERN


class DummyWorkflowCommandsConfig:
    """Minimal replacement for WorkflowCommandsConfig used in tests."""

    def __init__(self, config):
        self._config = config

    def get_config(self):
        return self._config


def test_safe_pattern_allows_common_keys():
    """STEP*, STEP_* and STEP-* variations should be accepted."""
    assert _SAFE_STEP_KEY_PATTERN.match('STEP1')
    assert _SAFE_STEP_KEY_PATTERN.match('STEP_5')
    assert _SAFE_STEP_KEY_PATTERN.match('STEP-6')


def test_safe_pattern_rejects_unsafe_keys():
    """Keys containing spaces, slashes or HTML should be rejected."""
    for unsafe in ['STEP 1', 'STEP/1', 'DROP TABLE', '<img>']:
        assert not _SAFE_STEP_KEY_PATTERN.match(unsafe)


def test_get_cached_frontend_config_skips_unsafe_keys(monkeypatch):
    """
    Given: WorkflowCommandsConfig contains valid + invalid step keys
    When:  CacheService builds the frontend config
    Then:  Only safe step keys appear in the sanitized config (invalid are skipped)
    """
    fake_config = {
        'STEP1': {'display_name': 'Extraction'},
        'BAD KEY': {'display_name': 'Unsafe key with spaces'},
        '<img>': {'display_name': 'Definitely unsafe'},
    }

    dummy = DummyWorkflowCommandsConfig(fake_config)

    # Ensure CacheService instantiates our dummy config instead of the real one
    monkeypatch.setattr('config.workflow_commands.WorkflowCommandsConfig', lambda: dummy)

    # Reset cache stats for determinism
    cache_stats = CacheService.get_cache_stats()
    cache_stats['hits'] = 0
    cache_stats['misses'] = 0

    config = CacheService.get_cached_frontend_config()

    assert 'STEP1' in config
    assert 'BAD KEY' not in config
    assert '<img>' not in config
