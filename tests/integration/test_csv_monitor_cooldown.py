#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for the monitor-side failure cooldown.

Context: a link whose R2 object is missing used to be re-downloaded on every
monitor cycle (every 15s). The monitor now respects an exponential cooldown
derived from the persisted failure record, and retries once it expires.

The failure map and the history are injected through the CSVService class. Both
the class and the monitor module are resolved at call time: other test files
reload `config.settings` / `services.csv_service` in sys.modules.
"""

import importlib
import threading
from datetime import datetime


def _eligible_record():
    return [{
        'url': 'https://server.kidpixel.workers.dev/dropbox/9529f228/6d6c3f94/file',
        'fallback_url': 'https://www.dropbox.com/scl/fo/tokenABC/Folder?rlkey=KEY&dl=1',
        'original_filename': '197 Camille.zip',
        'provider': 'dropbox',
        'timestamp': '2026-09-21 16:47:14',
        'source': 'webhook',
        'url_type': 'dropbox',
    }]


def _run_monitor_with_recorder(monkeypatch, records, failures=None, history=None):
    """Run one monitor pass; return the event signalled when a worker starts."""
    csv_monitor = importlib.import_module('services.csv_monitor')
    csv_service = importlib.import_module('services.csv_service')

    # Another test module sets DRY_RUN_DOWNLOADS=true at import time; the spawn
    # path under test requires the dry-run guard to be off explicitly.
    monkeypatch.setenv('DRY_RUN_DOWNLOADS', 'false')

    started = threading.Event()
    captured = []

    def recorder(url, ts, fallback_url=None, original_filename=None):
        captured.append((url, ts, fallback_url, original_filename))
        started.set()

    monkeypatch.setattr(csv_monitor, 'execute_csv_download_worker', recorder)
    monkeypatch.setattr(csv_service, 'webhook_fetch_records', lambda: records)
    monkeypatch.setattr(csv_service, 'WEBHOOK_SERVICE_AVAILABLE', True)
    monkeypatch.setattr(csv_service.CSVService, 'get_download_failure_map', staticmethod(lambda: dict(failures or {})))
    monkeypatch.setattr(csv_service.CSVService, 'get_download_history', staticmethod(lambda: set(history or ())))

    csv_monitor.check_csv_for_downloads()
    started.wait(2.0)
    return started, captured


def _normalize(url: str) -> str:
    return importlib.import_module('services.csv_service').CSVService._normalize_url(url)


def test_monitor_skips_url_in_cooldown(monkeypatch):
    # Given — a previous attempt failed (missing R2 object) seconds ago
    url = _eligible_record()[0]['url']
    failure_map = {_normalize(url): {
        'kind': 'not_found',
        'attempts': 1,
        'status_code': 404,
        'last_attempt_at': datetime.now().isoformat(),
    }}

    # When — the monitor runs again immediately
    started, captured = _run_monitor_with_recorder(monkeypatch, _eligible_record(), failures=failure_map)

    # Then — no download worker was spawned
    assert not started.is_set()
    assert captured == []


def test_monitor_retries_after_cooldown_expires(monkeypatch):
    # Given — the recorded failure is older than the cooldown window
    url = _eligible_record()[0]['url']
    failure_map = {_normalize(url): {
        'kind': 'not_found',
        'attempts': 2,
        'status_code': 404,
        'last_attempt_at': '2020-01-01T00:00:00',
    }}

    # When
    started, captured = _run_monitor_with_recorder(monkeypatch, _eligible_record(), failures=failure_map)

    # Then — the URL is retried, with its Dropbox fallback
    assert started.is_set()
    assert len(captured) == 1
    assert captured[0][0] == url
    assert captured[0][2] == _eligible_record()[0]['fallback_url']


def test_monitor_ignores_url_already_in_history(monkeypatch):
    # Given — the archive was already downloaded (both URLs recorded)
    record = _eligible_record()[0]
    history = {_normalize(record['url']), _normalize(record['fallback_url'])}

    # When
    started, captured = _run_monitor_with_recorder(monkeypatch, [record], history=history)

    # Then
    assert not started.is_set()
    assert captured == []
