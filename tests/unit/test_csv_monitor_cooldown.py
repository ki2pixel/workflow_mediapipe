#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the CSV monitor failure cooldown.

Context: a failed URL (missing R2 object, unreachable link) used to be
re-armed on every monitor cycle (15s). It is now retried with an exponential
cooldown derived from the persisted failure record.
"""

from datetime import datetime, timedelta

from services.csv_monitor import _cooldown_remaining_s


class TestFailureCooldown:
    """Cooldown grows with attempts and expires over time."""

    def test_first_failure_waits_one_monitor_interval(self):
        # Given
        failure = {'attempts': 1, 'last_attempt_at': datetime.now().isoformat()}

        # When
        remaining = _cooldown_remaining_s(failure)

        # Then
        assert 0 < remaining <= 15

    def test_cooldown_grows_with_attempts(self):
        # Given
        now = datetime.now().isoformat()
        first = {'attempts': 1, 'last_attempt_at': now}
        fourth = {'attempts': 4, 'last_attempt_at': now}

        # When / Then
        assert _cooldown_remaining_s(fourth) > _cooldown_remaining_s(first)

    def test_cooldown_is_capped(self):
        # Given — a long history of failures
        failure = {'attempts': 30, 'last_attempt_at': datetime.now().isoformat()}

        # When
        remaining = _cooldown_remaining_s(failure)

        # Then — capped by DOWNLOAD_COOLDOWN_MAX_S (1h by default)
        assert remaining <= 3600

    def test_expired_cooldown_allows_retry(self):
        # Given — the last attempt is older than the cooldown
        failure = {'attempts': 5, 'last_attempt_at': (datetime.now() - timedelta(hours=3)).isoformat()}

        # When
        remaining = _cooldown_remaining_s(failure)

        # Then
        assert remaining == 0.0

    def test_missing_or_invalid_timestamp_does_not_block(self):
        # Given / When / Then
        assert _cooldown_remaining_s({'attempts': 2, 'last_attempt_at': ''}) == 0.0
        assert _cooldown_remaining_s({'attempts': 2, 'last_attempt_at': 'not-a-date'}) == 0.0
