"""
WebhookService
Provides a simple external JSON-based source of download links.
Respects project standards: service-layer only, robust error handling, caching, and status reporting.

Public methods:
- fetch_records(): List[Dict[str, str]] of {url, timestamp, source, url_type}
- get_service_status(): Dict[str, Any]
"""
from __future__ import annotations

from datetime import datetime
import logging
import time
from typing import Any, Dict, List, Optional

import requests

from config.settings import config

logger = logging.getLogger(__name__)

# In-memory cache
_cache_data: Optional[List[Dict[str, str]]] = None
_cache_fetched_at: float = 0.0
_last_error: Optional[str] = None
_last_status: Dict[str, Any] = {
    "available": False,
    "last_fetch_ts": None,
    "error": None,
    "records": 0,
}


def _classify_url_type(url: str) -> str:
    try:
        u = (url or "").lower()
        if "fromsmash.com" in u:
            return "fromsmash"
        if "swisstransfer.com" in u:
            return "swisstransfer"
        if "dropbox.com" in u or "dl.dropboxusercontent.com" in u:
            return "dropbox"
        # R2/Worker proxy URLs for Dropbox (example: https://<host>.workers.dev/dropbox/<...>/file)
        if "/dropbox/" in u and ("workers.dev" in u or "worker" in u):
            return "dropbox"
        return "external"
    except Exception:
        return "external"


def _normalize_timestamp(ts: Optional[str]) -> Optional[str]:
    """Best-effort normalization: accept ISO or 'YYYY-MM-DD HH:MM:SS'.
    Leave unchanged if parsing is uncertain; CSVService will also handle.
    """
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
        if not dt.tzinfo:
            return str(ts)
        return dt.astimezone().strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return str(ts)


def _validate_and_format(items: Any) -> List[Dict[str, str]]:
    """Validate raw JSON and return standardized rows.

    Expected input example:
    [
        {"url": "https://...", "timestamp": "2025-10-17T12:34:13+0200", "source": "webhook"}
    ]
    """
    rows: List[Dict[str, str]] = []
    if not isinstance(items, list):
        return rows
    for it in items:
        try:
            if not isinstance(it, dict):
                continue
            # New webhook schema: pre-normalized urls + metadata
            source_url = str(it.get("source_url") or "").strip()
            r2_url = str(it.get("r2_url") or "").strip()
            original_filename = str(it.get("original_filename") or "").strip()
            provider = str(it.get("provider") or "").strip()
            created_at = _normalize_timestamp(it.get("created_at"))

            if r2_url or source_url:
                preferred_url = r2_url or source_url
                fallback_url = source_url if (r2_url and source_url and source_url != r2_url) else ""
                url_type = (provider.lower() if provider else _classify_url_type(preferred_url))
                row_new: Dict[str, str] = {
                    "url": preferred_url,
                    "fallback_url": fallback_url,
                    "original_filename": original_filename,
                    "provider": provider,
                    "timestamp": created_at or "",
                    "source": "webhook",
                    "url_type": url_type,
                }
                rows.append(row_new)
                continue

            # Legacy webhook schema
            url = str(it.get("url") or "").strip()
            if not url:
                continue
            ts = _normalize_timestamp(it.get("timestamp"))
            src = str(it.get("source") or "webhook").strip() or "webhook"
            url_type = str(it.get("url_type") or "").strip() or _classify_url_type(url)
            row_legacy: Dict[str, str] = {
                "url": url,
                "timestamp": ts or "",
                "source": src,
                "url_type": url_type,
            }
            rows.append(row_legacy)
        except Exception as e:
            logger.debug(f"WebhookService: skipping invalid item due to error: {e}")
            continue
    return rows


def fetch_records() -> Optional[List[Dict[str, str]]]:
    """Fetch and cache webhook JSON records.

    Returns None on hard error; returns [] if no data.
    Respects WEBHOOK_CACHE_TTL for caching.
    """
    global _cache_data, _cache_fetched_at, _last_error, _last_status
    now = time.time()

    # Use cache if within TTL
    if _cache_data is not None and (now - _cache_fetched_at) < max(0, config.WEBHOOK_CACHE_TTL):
        return _cache_data

    url = config.WEBHOOK_JSON_URL
    timeout = max(1, config.WEBHOOK_TIMEOUT)

    # Simple retry: up to 2 retries (total 3 attempts) with small backoff
    attempts = 3
    backoff = 1.0
    last_exc: Optional[Exception] = None

    for attempt in range(1, attempts + 1):
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            rows = _validate_and_format(data)
            _cache_data = rows
            _cache_fetched_at = now
            _last_error = None
            _last_status.update({
                "available": True,
                "last_fetch_ts": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now)),
                "error": None,
                "records": len(rows),
            })
            return rows
        except Exception as e:
            last_exc = e
            _last_error = str(e)
            _last_status.update({
                "available": False,
                "last_fetch_ts": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now)),
                "error": _last_error,
            })
            if attempt < attempts:
                time.sleep(backoff)
                backoff *= 2
            else:
                logger.error(f"WebhookService: failed to fetch webhook JSON after {attempts} attempts: {e}")
                return None


def get_service_status() -> Dict[str, Any]:
    """Return last known status for observability."""
    # Shallow copy to avoid mutation
    return dict(_last_status)
