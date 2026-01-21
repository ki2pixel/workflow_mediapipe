import logging
import os
import shutil
import sqlite3
from pathlib import Path
from typing import Dict, Iterable, Optional, Sequence, Set, Tuple

from config.settings import config

logger = logging.getLogger(__name__)


class DownloadHistoryRepository:
    def __init__(
        self,
        db_path: Path,
        shared_group: Optional[str],
        shared_file_mode: int = 0o664,
    ):
        self._db_path = Path(db_path)
        self._shared_group = shared_group
        self._shared_file_mode = shared_file_mode

    @property
    def db_path(self) -> Path:
        return self._db_path

    def initialize(self) -> None:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS download_history (url TEXT PRIMARY KEY, timestamp TEXT NOT NULL DEFAULT '')"
            )
        self._ensure_shared_permissions(self._db_path)
        self._ensure_shared_permissions(self._db_path.with_name(self._db_path.name + "-wal"))
        self._ensure_shared_permissions(self._db_path.with_name(self._db_path.name + "-shm"))

    def count(self) -> int:
        self.initialize()
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM download_history").fetchone()
        if not row:
            return 0
        return int(row[0] or 0)

    def get_urls(self) -> Set[str]:
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute("SELECT url FROM download_history").fetchall()
        return {str(r[0]) for r in rows if r and r[0]}

    def get_ts_by_url(self) -> Dict[str, str]:
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute("SELECT url, timestamp FROM download_history").fetchall()
        result: Dict[str, str] = {}
        for row in rows:
            if not row or not row[0]:
                continue
            result[str(row[0])] = str(row[1] or "")
        return result

    def upsert(self, url: str, timestamp: str) -> None:
        self.initialize()
        url = str(url)
        ts = str(timestamp or "")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO download_history(url, timestamp)
                VALUES (?, ?)
                ON CONFLICT(url) DO UPDATE SET
                  timestamp =
                    CASE
                      WHEN download_history.timestamp IS NULL OR download_history.timestamp = '' THEN excluded.timestamp
                      WHEN excluded.timestamp IS NULL OR excluded.timestamp = '' THEN download_history.timestamp
                      ELSE MIN(download_history.timestamp, excluded.timestamp)
                    END
                """,
                (url, ts),
            )

    def upsert_many(self, entries: Iterable[Tuple[str, str]]) -> None:
        self.initialize()
        entries_list = [(str(u), str(t or "")) for (u, t) in entries if u]
        if not entries_list:
            return
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO download_history(url, timestamp)
                VALUES (?, ?)
                ON CONFLICT(url) DO UPDATE SET
                  timestamp =
                    CASE
                      WHEN download_history.timestamp IS NULL OR download_history.timestamp = '' THEN excluded.timestamp
                      WHEN excluded.timestamp IS NULL OR excluded.timestamp = '' THEN download_history.timestamp
                      ELSE MIN(download_history.timestamp, excluded.timestamp)
                    END
                """,
                entries_list,
            )

    def delete_all(self) -> None:
        self.initialize()
        with self._connect() as conn:
            conn.execute("DELETE FROM download_history")

    def replace_all(self, entries: Sequence[Tuple[str, str]]) -> None:
        self.initialize()
        normalized = [(str(u), str(t or "")) for (u, t) in entries if u]
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM download_history")
                if normalized:
                    conn.executemany(
                        "INSERT INTO download_history(url, timestamp) VALUES(?, ?)",
                        normalized,
                    )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            str(self._db_path),
            timeout=30,
            isolation_level=None,
        )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _ensure_shared_permissions(self, target: Path) -> None:
        if not target or not target.exists():
            return
        if self._shared_group:
            try:
                shutil.chown(target, group=self._shared_group)
            except Exception as e:
                logger.warning(f"Unable to assign shared group '{self._shared_group}' to {target}: {e}")
        try:
            os.chmod(target, self._shared_file_mode)
        except Exception as e:
            logger.warning(f"Unable to set shared permissions on {target}: {e}")


download_history_repository = DownloadHistoryRepository(
    db_path=config.DOWNLOAD_HISTORY_DB_PATH,
    shared_group=config.DOWNLOAD_HISTORY_SHARED_GROUP,
)
