#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for DownloadHistoryRepository.
Validates SQLite WAL-mode persistence, parameterized queries, and transaction safety.
"""

import os
import sqlite3
import tempfile
import threading
import pytest
from pathlib import Path

from services.download_history_repository import DownloadHistoryRepository


@pytest.fixture
def temp_db_path():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.sqlite3"
        yield db_path


@pytest.fixture
def repo(temp_db_path):
    r = DownloadHistoryRepository(db_path=temp_db_path, shared_group=None)
    r.initialize()
    return r


class TestDownloadHistoryRepositoryInitialization:
    """Test database initialization and schema."""

    def test_initialize_creates_table(self, repo):
        conn = sqlite3.connect(str(repo.db_path))
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='download_history'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_initialize_is_idempotent(self, repo):
        repo.initialize()
        repo.initialize()

    def test_initialize_creates_db_file(self, temp_db_path):
        repo = DownloadHistoryRepository(db_path=temp_db_path, shared_group=None)
        assert not temp_db_path.exists()
        repo.initialize()
        assert temp_db_path.exists()

    def test_wal_mode_enabled(self, repo):
        conn = sqlite3.connect(str(repo.db_path))
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        conn.close()
        assert journal_mode.lower() == "wal"


class TestDownloadHistoryRepositoryCRUD:
    """Test basic CRUD operations."""

    def test_upsert_inserts_new_url(self, repo):
        repo.upsert("https://example.com/file1.zip", "2025-01-01 12:00:00")
        assert repo.count() == 1

    def test_upsert_updates_existing_url(self, repo):
        repo.upsert("https://example.com/file1.zip", "2025-01-01 00:00:00")
        repo.upsert("https://example.com/file1.zip", "2025-01-02 00:00:00")
        assert repo.count() == 1
        ts_map = repo.get_ts_by_url()
        assert ts_map["https://example.com/file1.zip"] == "2025-01-01 00:00:00"  # MIN preserved

    def test_upsert_many_inserts_batch(self, repo):
        entries = [
            ("https://a.com/f1.zip", "2025-01-01 12:00:00"),
            ("https://b.com/f2.zip", "2025-01-02 12:00:00"),
            ("https://c.com/f3.zip", ""),
        ]
        repo.upsert_many(entries)
        assert repo.count() == 3

    def test_upsert_many_empty_list(self, repo):
        repo.upsert_many([])
        assert repo.count() == 0

    def test_get_urls(self, repo):
        repo.upsert("https://a.com/f1.zip", "2025-01-01")
        repo.upsert("https://b.com/f2.zip", "2025-01-02")
        urls = repo.get_urls()
        assert "https://a.com/f1.zip" in urls
        assert "https://b.com/f2.zip" in urls
        assert len(urls) == 2

    def test_get_ts_by_url(self, repo):
        repo.upsert("https://a.com/f1.zip", "2025-01-01 12:00:00")
        ts_map = repo.get_ts_by_url()
        assert ts_map["https://a.com/f1.zip"] == "2025-01-01 12:00:00"

    def test_delete_all(self, repo):
        repo.upsert("https://a.com/f1.zip", "2025-01-01")
        repo.delete_all()
        assert repo.count() == 0

    def test_replace_all(self, repo):
        repo.upsert("https://old.com/file.zip", "2024-01-01")
        new_entries = [
            ("https://new1.com/file.zip", "2025-01-01"),
            ("https://new2.com/file.zip", "2025-01-02"),
        ]
        repo.replace_all(new_entries)
        assert repo.count() == 2
        urls = repo.get_urls()
        assert "https://old.com/file.zip" not in urls
        assert "https://new1.com/file.zip" in urls

    def test_replace_all_empty(self, repo):
        repo.upsert("https://a.com/file.zip", "2025-01-01")
        repo.replace_all([])
        assert repo.count() == 0


class TestDownloadHistoryRepositoryConcurrency:
    """Test thread-safety of repository operations."""

    def test_concurrent_upserts(self, repo):
        exceptions = []

        def worker(base_idx):
            try:
                for i in range(10):
                    idx = base_idx * 100 + i
                    repo.upsert(f"https://example.com/file_{idx}.zip", "2025-01-01 12:00:00")
            except Exception as e:
                exceptions.append(e)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(exceptions) == 0
        assert repo.count() == 100

    def test_concurrent_read_and_write(self, repo):
        exceptions = []

        def writer():
            try:
                for i in range(50):
                    repo.upsert(f"https://example.com/file_{i}.zip", "2025-01-01")
            except Exception as e:
                exceptions.append(e)

        def reader():
            try:
                for _ in range(50):
                    repo.get_urls()
                    repo.count()
                    repo.get_ts_by_url()
            except Exception as e:
                exceptions.append(e)

        t1 = threading.Thread(target=writer)
        t2 = threading.Thread(target=reader)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(exceptions) == 0


class TestDownloadHistoryRepositorySQLInjection:
    """Test protection against SQL injection in parameterized queries."""

    def test_upsert_parameters_escaped(self, repo):
        malicious_url = "https://example.com/file.zip' OR '1'='1"
        repo.upsert(malicious_url, "2025-01-01")
        assert repo.count() == 1

    def test_get_urls_returns_exact_match(self, repo):
        repo.upsert("https://real.com/file.zip", "2025-01-01")
        urls = repo.get_urls()
        assert "https://real.com/file.zip" in urls
        assert "https://real.com/file.zip' OR '1'='1" not in urls
