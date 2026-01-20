"""
CSV Service
Centralized service for CSV monitoring functionality.
"""

import logging
import os
import json
import threading
import re
from datetime import datetime, timezone
from typing import Dict, Any, Set, Optional, List
import tempfile
import shutil
import urllib.parse
import html
from pathlib import Path
from config.settings import config

logger = logging.getLogger(__name__)

# Import WebhookService for external JSON source
try:
    from services.webhook_service import fetch_records as webhook_fetch_records, get_service_status as webhook_status
    WEBHOOK_SERVICE_AVAILABLE = True
except Exception:
    WEBHOOK_SERVICE_AVAILABLE = False
    def webhook_status():
        return {"available": False, "error": "WebhookService not available"}

# Note: CSV monitoring state and downloads tracking are now managed in app_new.py
# This service acts as an interface to those global variables

# Download history
DOWNLOAD_HISTORY_FILE = config.BASE_PATH_SCRIPTS / "download_history.json"
_SHARED_GROUP = config.DOWNLOAD_HISTORY_SHARED_GROUP
_SHARED_FILE_MODE = 0o664

# Single-process reentrant lock to serialize access to download history file
# Use RLock to avoid deadlocks when a method holding the lock calls another
# method that also acquires the same lock (e.g., add_to_download_history_with_timestamp -> save_download_history).
_HISTORY_LOCK = threading.RLock()

# Optional in-memory cache for last known good history set to avoid bursts on transient read errors
_LAST_KNOWN_HISTORY_SET: Set[str] = set()


def _is_dropbox_url(url: str) -> bool:
    """Return True if the URL belongs to Dropbox domains.

    Args:
        url: URL string

    Returns:
        bool: True if hostname matches known Dropbox hostnames
    """
    try:
        from urllib.parse import urlparse
        parsed = urlparse((url or "").strip())
        host = (parsed.hostname or "").lower()
        # Known Dropbox hostnames
        return host in {"dropbox.com", "www.dropbox.com", "dl.dropboxusercontent.com"}
    except Exception:
        return False


def _is_dropbox_proxy_url(url: str) -> bool:
    """Return True if the URL looks like a worker/R2 proxy for Dropbox downloads."""
    try:
        u = (url or "").strip().lower()
        return "/dropbox/" in u and ("workers.dev" in u or "worker" in u)
    except Exception:
        return False


def _looks_like_archive_download(url: Optional[str], original_filename: Optional[str]) -> bool:
    """Heuristic to avoid auto-downloading non-archive Dropbox links (e.g. png previews)."""
    u = (url or "").strip().lower()
    fn = (original_filename or "").strip().lower()
    if fn.endswith('.zip'):
        return True
    if '/scl/fo/' in u:
        return True
    if u.endswith('.zip') or '.zip?' in u:
        return True
    return False


class CSVService:
    """
    Centralized service for CSV monitoring functionality.
    Handles CSV file monitoring and download tracking.
    """
    
    _initialized = False

    @staticmethod
    def initialize() -> None:
        """Initialize the CSV service."""
        if not CSVService._initialized:
            CSVService._initialized = True
            logger.info("CSV service initialized")
            # Best-effort migration to structured local-time format if needed
            try:
                if DOWNLOAD_HISTORY_FILE.exists():
                    CSVService.migrate_history_to_local_time()
                    # Best-effort normalization/dedup: unify URL variants to avoid re-downloads
                    try:
                        CSVService._normalize_and_deduplicate_history()
                    except Exception as norm_err:
                        logger.warning(f"History normalization skipped due to error: {norm_err}")
            except Exception as e:
                logger.warning(f"History migration skipped due to error: {e}")
    
    @staticmethod
    def get_monitor_status() -> Dict[str, Any]:
        """
        Get monitoring service status (CSV or Airtable).

        Returns:
            Monitor status dictionary with both CSV and Airtable information
        """
        # Import WorkflowState singleton
        from services.workflow_state import get_workflow_state
        
        workflow_state = get_workflow_state()
        monitor_status = workflow_state.get_csv_monitor_status()

        # Webhook is the single data source
        status = {
            "csv_monitor": monitor_status,
            "data_source": "webhook",
            "monitor_interval": config.WEBHOOK_MONITOR_INTERVAL,
            "webhook": webhook_status()
        }

        return status
    

    
    @staticmethod
    def get_download_history() -> Set[str]:
        """
        Load download history from file as a set of URLs (backward compatible).

        The underlying file may be:
        - A list of strings: ["url1", "url2", ...]
        - A list of objects: [{"url": "...", "timestamp": "YYYY-MM-DD HH:MM:SS"}, ...]

        Returns:
            Set[str]: URLs present in history
        """
        try:
            global _LAST_KNOWN_HISTORY_SET
            with _HISTORY_LOCK:
                if not DOWNLOAD_HISTORY_FILE.exists():
                    return set()
                # Avoid decoding errors on empty/incomplete writes
                if DOWNLOAD_HISTORY_FILE.stat().st_size == 0:
                    logger.error("Error loading download history: file size is 0 (likely interrupted write)")
                    # Fallback to backup if available
                    bak_path = DOWNLOAD_HISTORY_FILE.with_suffix('.json.bak')
                    if bak_path.exists() and bak_path.stat().st_size > 0:
                        try:
                            with open(bak_path, 'r', encoding='utf-8') as f_bak:
                                data = json.load(f_bak)
                            urls = CSVService._parse_history_to_set(data)
                            # refresh cache
                            _LAST_KNOWN_HISTORY_SET = set(urls)
                            return urls
                        except Exception:
                            pass
                    # Fallback to last known in-memory cache to avoid mass re-downloads
                    return set(_LAST_KNOWN_HISTORY_SET)

                with open(DOWNLOAD_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                urls = CSVService._parse_history_to_set(data)
                # update cache on success
                _LAST_KNOWN_HISTORY_SET = set(urls)
                return urls
        except Exception as e:
            logger.error(f"Error loading download history: {e}")
            # Fallback to backup first
            try:
                bak_path = DOWNLOAD_HISTORY_FILE.with_suffix('.json.bak')
                if bak_path.exists() and bak_path.stat().st_size > 0:
                    with open(bak_path, 'r', encoding='utf-8') as f_bak:
                        data = json.load(f_bak)
                    urls = CSVService._parse_history_to_set(data)
                    _LAST_KNOWN_HISTORY_SET = set(urls)
                    return urls
            except Exception:
                pass
            # Last resort, return cached set to avoid duplicates burst
            return set(_LAST_KNOWN_HISTORY_SET)

    @staticmethod
    def _parse_history_to_set(data: Any) -> Set[str]:
        """Convert history JSON content to a set of URLs supporting both formats."""
        if not isinstance(data, list):
            return set()
        if data and isinstance(data[0], dict):
            return {CSVService._normalize_url(str(item.get('url'))) for item in data if isinstance(item, dict) and item.get('url')}
        return {CSVService._normalize_url(str(u)) for u in data if isinstance(u, str)}

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Normalize URLs to prevent duplicates due to minor variations.

        Rules:
        - Trim whitespace
        - Unescape HTML entities (e.g., '&amp;' -> '&')
        - Recursively decode double-encoded sequences (e.g., amp%3Bdl=0 -> &dl=0)
        - Lowercase scheme and hostname
        - Remove default ports (80 for http, 443 for https)
        - Sort query parameters by key and value
        - Remove empty query parameters
        - For Dropbox links, ensure a single dl=1 param and collapse duplicates
        - Remove trailing slashes for non-root paths
        - Percent-decode path and then re-encode safely
        """
        if not url:
            return ""
        try:
            raw = url.strip()
            # First, unescape HTML entities that may come from CSV/HTML sources
            # Example: '...&amp;dl=0' -> '...&dl=0'
            try:
                raw = html.unescape(raw)
            except Exception:
                pass
            
            # Pre-process: recursively decode double-encoded sequences that may cause parsing issues
            # Example: "amp%3Bdl=0&dl=1" becomes "&dl=0&dl=1", which is then properly parsed
            prev_url = None
            max_decode_iterations = 3
            iteration = 0
            while prev_url != raw and iteration < max_decode_iterations:
                prev_url = raw
                # Decode common double-encoded patterns (HTML entity codes)
                if 'amp%3B' in raw or 'amp%3b' in raw:
                    raw = raw.replace('amp%3B', '&').replace('amp%3b', '&')
                # Detect and clean malformed ampersands that appear before valid params
                # Pattern: "?amp%3Bdl=0&dl=1" -> "?dl=1"
                if '%3B' in raw or '%3b' in raw:
                    # Try URL decode once to catch other double-encoded params
                    try:
                        decoded = urllib.parse.unquote(raw)
                        # Only accept if it still looks like a valid URL
                        if '://' in decoded:
                            raw = decoded
                    except Exception:
                        pass
                iteration += 1
            
            parsed = urllib.parse.urlsplit(raw)
            scheme = (parsed.scheme or '').lower()
            netloc = (parsed.hostname or '').lower()
            port = parsed.port
            # Preserve username/password if any
            if parsed.username or parsed.password:
                auth = ''
                if parsed.username:
                    auth += urllib.parse.quote(parsed.username)
                if parsed.password:
                    auth += f":{urllib.parse.quote(parsed.password)}"
                netloc = f"{auth}@{netloc}" if auth else netloc

            # Drop default ports
            if port and not (
                (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443)
            ):
                netloc = f"{netloc}:{port}"

            # Normalize path: decode, strip, remove duplicate slashes
            path = urllib.parse.unquote(parsed.path or '')
            if '//' in path:
                while '//' in path:
                    path = path.replace('//', '/')
            # Remove trailing slash unless root
            if path.endswith('/') and path != '/':
                path = path[:-1]
            # Re-encode path safely
            path = urllib.parse.quote(path, safe='/-._~')

            # Normalize query params
            q = urllib.parse.parse_qsl(parsed.query or '', keep_blank_values=False)
            # Special handling for Dropbox: force dl=1
            host_lower = (parsed.hostname or '').lower() if parsed.hostname else ''
            is_dropbox = host_lower.endswith('dropbox.com') or host_lower == 'dl.dropboxusercontent.com'
            filtered = []
            seen = set()
            for k, v in q:
                key = k.strip()
                val = v.strip()
                # Skip completely empty params
                if not key:
                    continue
                # Skip params with empty values (except legitimate ones like rlkey)
                if not val and key.lower() not in ('rlkey',):
                    # For Dropbox dl param, empty value is invalid
                    if is_dropbox and key.lower() == 'dl':
                        continue
                # collapse duplicates
                tup = (key, val)
                if tup in seen:
                    continue
                seen.add(tup)
                # We will handle dl param below for Dropbox
                if is_dropbox and key.lower() == 'dl':
                    continue
                filtered.append((key, val))

            if is_dropbox:
                filtered.append(('dl', '1'))

            # Sort for determinism
            filtered.sort(key=lambda kv: (kv[0].lower(), kv[1]))
            query = urllib.parse.urlencode(filtered, doseq=True)

            # Fragment is not relevant for downloads; drop it
            normalized = urllib.parse.urlunsplit((scheme, netloc, path, query, ''))
            return normalized
        except Exception:
            return url.strip()

    @staticmethod
    def _load_structured_history() -> List[Dict[str, str]]:
        """Load the history as a list of {url, timestamp} objects (best-effort).

        Returns:
            List[Dict[str, str]]: Each item contains 'url' and 'timestamp' (string)
        """
        try:
            if not DOWNLOAD_HISTORY_FILE.exists():
                return []
            with open(DOWNLOAD_HISTORY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                return []
            # If already structured
            if data and isinstance(data[0], dict):
                result: List[Dict[str, str]] = []
                for item in data:
                    if isinstance(item, dict) and item.get('url'):
                        ts = str(item.get('timestamp')) if item.get('timestamp') else None
                        result.append({
                            'url': CSVService._normalize_url(str(item.get('url'))),
                            'timestamp': ts if ts else ''
                        })
                return result
            # Flat list of URLs -> convert to objects with empty timestamp
            result = []
            for u in data:
                if isinstance(u, str) and u:
                    result.append({'url': CSVService._normalize_url(u), 'timestamp': ''})
            return result
        except Exception as e:
            logger.error(f"Error loading structured download history: {e}")
            return []

    @staticmethod
    def _now_ts_str() -> str:
        """Return current timestamp as 'YYYY-MM-DD HH:MM:SS' in LOCAL time."""
        # Use system local timezone
        return datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def migrate_history_to_local_time() -> Dict[str, Any]:
        """
        Convert existing download_history.json timestamps from UTC to local time.

        Assumes stored timestamps are in 'YYYY-MM-DD HH:MM:SS' and represent UTC.
        For each, convert to local timezone and re-save chronologically.

        Returns:
            dict with migration summary
        """
        try:
            items = CSVService._load_structured_history()
            if not items:
                return {"status": "noop", "updated": 0}

            updated = 0
            converted: List[Dict[str, str]] = []
            for item in items:
                url = item.get('url')
                ts = item.get('timestamp') or ''
                new_ts = ts
                if ts:
                    try:
                        # Parse as UTC naive and set tzinfo=UTC, then convert to local
                        dt_utc = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                        dt_local = dt_utc.astimezone()  # system local tz
                        new_ts = dt_local.strftime('%Y-%m-%d %H:%M:%S')
                        if new_ts != ts:
                            updated += 1
                    except Exception:
                        # Best-effort: try ISO parse
                        try:
                            dt_any = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                            dt_local = (dt_any if dt_any.tzinfo else dt_any.replace(tzinfo=timezone.utc)).astimezone()
                            new_ts = dt_local.strftime('%Y-%m-%d %H:%M:%S')
                            if new_ts != ts:
                                updated += 1
                        except Exception:
                            # Leave as is if unparseable
                            new_ts = ts
                converted.append({'url': url, 'timestamp': new_ts})

            # Sort chronologically, then by URL
            def _sort_key(item: Dict[str, str]):
                ts = item.get('timestamp') or '9999-12-31 23:59:59'
                return (ts, item.get('url') or '')

            converted.sort(key=_sort_key)

            with open(DOWNLOAD_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(converted, f, indent=2, ensure_ascii=False)

            return {"status": "success", "updated": updated, "total": len(converted)}
        except Exception as e:
            logger.error(f"Error migrating history to local time: {e}")
            return {"status": "error", "message": str(e)}
    
    @staticmethod
    def _ensure_shared_permissions(target: Path) -> None:
        """
        Apply shared group/permission settings to the target file if configured.
        """
        if not target or not target.exists():
            return
        if _SHARED_GROUP:
            try:
                shutil.chown(target, group=_SHARED_GROUP)
            except Exception as chown_err:
                logger.warning(f"Unable to assign shared group '{_SHARED_GROUP}' to {target}: {chown_err}")
        try:
            os.chmod(target, _SHARED_FILE_MODE)
        except Exception as chmod_err:
            logger.warning(f"Unable to set shared permissions on {target}: {chmod_err}")

    @staticmethod
    def save_download_history(history_set: Set[str]) -> None:
        """
        Save download history to file, as a chronologically sorted list of
        objects {url, timestamp}. Backward compatible with callers passing a set.

        Rules:
        - Preserve existing timestamps for URLs already present.
        - Assign current timestamp to new URLs.
        - Only persist URLs present in history_set (reflects clear/overwrite).
        - Sort by timestamp ASC, then URL for deterministic order.
        """
        try:
            with _HISTORY_LOCK:
                existing = CSVService._load_structured_history()
                # Map existing timestamps
                ts_by_url: Dict[str, str] = {}
                for item in existing:
                    url = item.get('url')
                    ts = item.get('timestamp') or ''
                    if url:
                        ts_by_url[url] = ts

                # Build new structured list
                structured: List[Dict[str, str]] = []
                # Normalize all URLs before persisting
                normalized_set = {CSVService._normalize_url(u) for u in history_set}
                for url in sorted(normalized_set):  # sort for stability before timestamp sort tie-breaker
                    ts = ts_by_url.get(url)
                    if not ts:
                        ts = CSVService._now_ts_str()
                    structured.append({'url': url, 'timestamp': ts})

                # Sort chronologically (empty timestamps last), then by URL
                def _sort_key(item: Dict[str, str]):
                    ts = item.get('timestamp') or '9999-12-31 23:59:59'
                    return (ts, item.get('url') or '')

                structured.sort(key=_sort_key)

                # Write atomically with backup
                tmp_fd, tmp_path_str = tempfile.mkstemp(prefix='download_history_', suffix='.json', dir=str(DOWNLOAD_HISTORY_FILE.parent))
                try:
                    with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f_tmp:
                        json.dump(structured, f_tmp, indent=2, ensure_ascii=False)

                    # Create backup of current file if exists
                    if DOWNLOAD_HISTORY_FILE.exists() and DOWNLOAD_HISTORY_FILE.stat().st_size > 0:
                        bak_path = DOWNLOAD_HISTORY_FILE.with_suffix('.json.bak')
                        try:
                            shutil.copyfile(DOWNLOAD_HISTORY_FILE, bak_path)
                            CSVService._ensure_shared_permissions(bak_path)
                        except Exception:
                            # Non-fatal
                            pass

                    os.replace(tmp_path_str, DOWNLOAD_HISTORY_FILE)
                    CSVService._ensure_shared_permissions(DOWNLOAD_HISTORY_FILE)

                    # Update in-memory cache on success
                    global _LAST_KNOWN_HISTORY_SET
                    _LAST_KNOWN_HISTORY_SET = set(normalized_set)
                finally:
                    # Ensure temp file removed if still present
                    try:
                        if os.path.exists(tmp_path_str):
                            os.remove(tmp_path_str)
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"Error saving download history: {e}")
    
    @staticmethod
    def add_to_download_history(url: str) -> bool:
        """
        Add URL to download history.
        
        Args:
            url: URL to add to history
            
        Returns:
            True if successful, False otherwise
        """
        try:
            history = CSVService.get_download_history()
            history.add(CSVService._normalize_url(url))
            # save_download_history will assign timestamp if new and keep ordering
            CSVService.save_download_history(history)
            return True
        except Exception as e:
            logger.error(f"Error adding to download history: {e}")
            return False

    @staticmethod
    def add_to_download_history_with_timestamp(url: str, timestamp_str: Optional[str]) -> bool:
        """
        Add URL to download history with a provided timestamp (if any).

        Preserves the earliest timestamp seen for a URL. If no valid timestamp is
        provided, uses current time.

        Args:
            url: URL to add
            timestamp_str: Optional timestamp string 'YYYY-MM-DD HH:MM:SS' or ISO; best-effort parsed

        Returns:
            True if persisted successfully, else False
        """
        try:
            with _HISTORY_LOCK:
                # Load existing structured history and map
                existing = CSVService._load_structured_history()
                ts_by_url: Dict[str, str] = {item['url']: (item.get('timestamp') or '') for item in existing if item.get('url')}

                # Normalize/choose timestamp
                ts_norm = None
                if timestamp_str:
                    # Try a few formats, else keep as-is
                    try:
                        # Try ISO first
                        dt = datetime.fromisoformat(str(timestamp_str).replace('Z', '+00:00'))
                        ts_norm = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        # Try common MySQL format
                        try:
                            dt = datetime.strptime(str(timestamp_str), '%Y-%m-%d %H:%M:%S')
                            ts_norm = dt.strftime('%Y-%m-%d %H:%M:%S')
                        except Exception:
                            # Fallback: keep raw string
                            ts_norm = str(timestamp_str)
                if not ts_norm:
                    ts_norm = CSVService._now_ts_str()

                norm_url = CSVService._normalize_url(url)
                # Preserve existing timestamp if it is earlier than the new one
                if norm_url in ts_by_url:
                    prev_ts = ts_by_url[norm_url] or ts_norm
                    # Keep lexicographically smaller timestamp as a simple heuristic
                    ts_by_url[norm_url] = min(prev_ts or ts_norm, ts_norm or prev_ts)
                else:
                    ts_by_url[norm_url] = ts_norm

                # Persist using save logic
                CSVService.save_download_history(set(ts_by_url.keys()))
                return True
        except Exception as e:
            logger.error(f"Error adding to download history with timestamp: {e}")
            return False
    
    @staticmethod
    def is_url_downloaded(url: str) -> bool:
        """
        Check if URL has been downloaded before.
        
        Args:
            url: URL to check
            
        Returns:
            True if URL was previously downloaded
        """
        history = CSVService.get_download_history()
        return CSVService._normalize_url(url) in history
    
    @staticmethod
    def get_csv_downloads_status() -> Dict[str, Any]:
        """
        Get status of CSV downloads.

        Returns:
            CSV downloads status dictionary
        """
        # Import WorkflowState singleton
        from services.workflow_state import get_workflow_state
        
        workflow_state = get_workflow_state()
        active_downloads = workflow_state.get_active_csv_downloads_dict()
        recent_statuses = workflow_state.get_kept_csv_downloads_list()

        return {
            "active_downloads": active_downloads,
            "recent_statuses": recent_statuses,
            "total_active": len(active_downloads),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    @staticmethod
    def add_csv_download(download_id: str, download_info: Dict[str, Any]) -> None:
        """
        Add a CSV download to tracking.

        Args:
            download_id: Unique download identifier
            download_info: Download information dictionary
        """
        # Import WorkflowState singleton
        from services.workflow_state import get_workflow_state
        
        workflow_state = get_workflow_state()
        download_data = {
            **download_info,
            "start_time": datetime.now(timezone.utc).isoformat()
        }
        workflow_state.add_csv_download(download_id, download_data)

        logger.info(f"CSV download added: {download_id}")
    
    @staticmethod
    def update_csv_download(download_id: str, status: str, **kwargs) -> None:
        """
        Update CSV download status.

        Args:
            download_id: Download identifier
            status: New status
            **kwargs: Additional fields to update
        """
        # Import WorkflowState singleton
        from services.workflow_state import get_workflow_state
        
        workflow_state = get_workflow_state()
        
        # Update download status with individual parameters
        progress = kwargs.get('progress')
        message = kwargs.get('message')
        filename = kwargs.get('filename')
        
        workflow_state.update_csv_download(
            download_id=download_id,
            status=status,
            progress=progress,
            message=message,
            filename=filename
        )

        # If download completed, move to history
        if status in ["completed", "failed", "cancelled", "unknown_error"]:
            workflow_state.move_csv_download_to_history(download_id)

        logger.debug(f"CSV download updated: {download_id} -> {status}")
    
    @staticmethod
    def remove_csv_download(download_id: str) -> None:
        """
        Remove CSV download from tracking.

        Args:
            download_id: Download identifier
        """
        # Import WorkflowState singleton
        from services.workflow_state import get_workflow_state
        
        workflow_state = get_workflow_state()
        workflow_state.remove_csv_download(download_id)

        logger.info(f"CSV download removed: {download_id}")
    
    @staticmethod
    def rewrite_dropbox_to_dl_host(url_str: str) -> str:
        """Rewrite a www.dropbox.com URL to dl.dropboxusercontent.com preserving path/query.

        Example:
        https://www.dropbox.com/scl/fo/<id>?rlkey=...&dl=1 ->
        https://dl.dropboxusercontent.com/scl/fo/<id>?rlkey=...&dl=1

        Args:
            url_str: Original Dropbox URL

        Returns:
            Rewritten URL string
        """
        try:
            parsed = urllib.parse.urlsplit(url_str)
            host = parsed.hostname or ""
            # Do NOT rewrite folder share links ('/scl/fo/') which are not served by dl.dropboxusercontent.com
            if (host.endswith("dropbox.com") and host != "dl.dropboxusercontent.com"
                    and not (parsed.path or '').lower().startswith('/scl/fo/')):
                new_netloc = "dl.dropboxusercontent.com"
                # preserve port if any (rare)
                if parsed.port and parsed.port not in (80, 443):
                    new_netloc = f"{new_netloc}:{parsed.port}"
                return urllib.parse.urlunsplit((parsed.scheme or "https", new_netloc, parsed.path, parsed.query, ""))
            return url_str
        except Exception:
            return url_str

    @staticmethod
    def _check_csv_for_downloads() -> None:
        """
        Check for new downloads using Webhook as the single data source.
        """
        try:
            # Import here to avoid circular imports
            from app_new import execute_csv_download_worker
            from services.workflow_state import get_workflow_state
            import threading
            import os

            # Fetch data from Webhook (single data source)
            if not WEBHOOK_SERVICE_AVAILABLE:
                logger.error("WebhookService not available - monitoring disabled")
                return

            logger.debug("Fetching data from Webhook")
            data_rows = webhook_fetch_records()
            source_type = "WEBHOOK"

            if data_rows is None:
                logger.warning(f"Could not fetch data from {source_type}")
                return

            # Get current download history (normalized URLs)
            download_history = CSVService.get_download_history()

            workflow_state = get_workflow_state()
            active_downloads = workflow_state.get_active_csv_downloads_dict()
            kept_downloads = workflow_state.get_kept_csv_downloads_list()

            tracked_urls: Set[str] = set()
            try:
                candidates = list(active_downloads.values()) + list(kept_downloads)
                for download in candidates:
                    if not isinstance(download, dict):
                        continue
                    status = str(download.get('status') or '').strip().lower()
                    if status in ('failed', 'cancelled', 'unknown_error'):
                        continue
                    raw_url = (download.get('original_url') or download.get('url') or '').strip()
                    if not raw_url:
                        continue
                    norm_existing = CSVService._normalize_url(raw_url)
                    if norm_existing:
                        tracked_urls.add(norm_existing)
            except Exception:
                tracked_urls = set()

            def _is_url_already_tracked(norm_primary: Optional[str], norm_fallback: Optional[str]) -> bool:
                if norm_primary and norm_primary in tracked_urls:
                    return True
                if norm_fallback and norm_fallback in tracked_urls:
                    return True
                return False

            total_rows = len(data_rows)
            skipped_missing_url = 0
            skipped_already_in_history = 0
            skipped_already_tracked = 0

            # Check for new URLs
            new_downloads = 0
            # Optional dry-run to avoid real downloads (useful for tests/CI):
            dry_run = os.environ.get('DRY_RUN_DOWNLOADS', 'false').lower() in ('true', '1')

            handled_in_this_pass: Set[str] = set()

            for row in data_rows:
                url = row.get('url')
                fallback_url = row.get('fallback_url')
                original_filename = row.get('original_filename')
                provider = row.get('provider')
                timestamp_str = row.get('timestamp')

                norm_url = CSVService._normalize_url(url) if url else None
                norm_fallback_url = CSVService._normalize_url(fallback_url) if fallback_url else None

                if norm_url and norm_url in handled_in_this_pass:
                    continue
                if norm_fallback_url and norm_fallback_url in handled_in_this_pass:
                    continue

                already_in_history = (
                    (norm_url and norm_url in download_history)
                    or (norm_fallback_url and norm_fallback_url in download_history)
                )
                if not norm_url:
                    skipped_missing_url += 1
                    continue
                if _is_url_already_tracked(norm_url, norm_fallback_url):
                    skipped_already_tracked += 1
                    handled_in_this_pass.add(norm_url)
                    if norm_fallback_url:
                        handled_in_this_pass.add(norm_fallback_url)
                    continue
                if already_in_history:
                    skipped_already_in_history += 1
                    # Common case: preferred URL removed from history, but fallback URL still present.
                    # This is expected behavior to prevent re-downloads across URL variants.
                    if (
                        norm_fallback_url
                        and norm_fallback_url in download_history
                        and norm_url not in download_history
                    ):
                        logger.debug(
                            f"{source_type} MONITOR: Skipping URL because fallback is already in download history "
                            f"(preferred={norm_url}, fallback={norm_fallback_url})"
                        )
                    continue

                try:
                    parsed_primary = urllib.parse.urlsplit(url or '')
                    scheme_primary = (parsed_primary.scheme or '').lower()
                    if scheme_primary and scheme_primary not in ('http', 'https'):
                        logger.debug(
                            f"{source_type} MONITOR: Ignoring unsupported URL scheme '{scheme_primary}': {url}"
                        )
                        handled_in_this_pass.add(norm_url)
                        if norm_fallback_url:
                            handled_in_this_pass.add(norm_fallback_url)
                        continue
                except Exception:
                    # If URL parsing fails, treat it as non-eligible.
                    logger.debug(
                        f"{source_type} MONITOR: Ignoring invalid URL (parse error): {url}"
                    )
                    handled_in_this_pass.add(norm_url)
                    if norm_fallback_url:
                        handled_in_this_pass.add(norm_fallback_url)
                    continue

                url_lower = (url or '').lower()
                provider_lower = str(provider or '').strip().lower()

                # Determine URL type for UI hints / routing
                url_type = (
                    str(row.get('url_type') or '').strip().lower()
                    or (
                        'fromsmash' if 'fromsmash.com' in url_lower else (
                            'swisstransfer' if 'swisstransfer.com' in url_lower else (
                                'dropbox' if (_is_dropbox_url(url) or _is_dropbox_proxy_url(url) or provider_lower == 'dropbox') else 'external'
                            )
                        )
                    )
                )

                is_dropbox_like = (
                    url_type == 'dropbox'
                    or provider_lower == 'dropbox'
                    or _is_dropbox_url(url)
                    or _is_dropbox_proxy_url(url)
                )

                # Auto-download is intentionally restricted:
                # - Prevents large backlog downloads from legacy entries.
                # - Focuses on the new webhook schema (original_filename / fallback_url) and R2 proxy URLs.
                has_new_schema_hints = bool(
                    (original_filename and str(original_filename).strip())
                    or (fallback_url and str(fallback_url).strip())
                    or _is_dropbox_proxy_url(url)
                )
                auto_download_allowed = (
                    is_dropbox_like
                    and _looks_like_archive_download(url, original_filename)
                    and has_new_schema_hints
                )

                if auto_download_allowed:
                    logger.info(
                        f"{source_type} MONITOR: New eligible URL detected: {url} (timestamp: {timestamp_str}) [type={url_type}]"
                    )
                    # Dropbox-like: proceed with auto-download (unless dry-run)
                    if dry_run:
                        logger.info(
                            f"[DRY RUN] Would start Dropbox download for URL: {url} (timestamp: {timestamp_str})"
                        )
                        CSVService.add_to_download_history_with_timestamp(norm_url, timestamp_str)
                        download_history.add(norm_url)
                        handled_in_this_pass.add(norm_url)
                        if norm_fallback_url:
                            CSVService.add_to_download_history_with_timestamp(norm_fallback_url, timestamp_str)
                            download_history.add(norm_fallback_url)
                            handled_in_this_pass.add(norm_fallback_url)
                        new_downloads += 1
                    else:
                        download_thread = threading.Thread(
                            target=execute_csv_download_worker,
                            args=(url, timestamp_str, fallback_url, original_filename),
                            name=f"Download-{str(timestamp_str).replace('/', '').replace(' ', '_').replace(':', '')}"
                        )
                        download_thread.daemon = True
                        download_thread.start()
                        handled_in_this_pass.add(norm_url)
                        if norm_fallback_url:
                            handled_in_this_pass.add(norm_fallback_url)
                        new_downloads += 1
                else:
                    # Non-eligible link: ignore it (no UI entry, no history write) to keep auto-download Dropbox-only.
                    logger.debug(
                        f"{source_type} MONITOR: Ignoring non-eligible URL (auto-download disabled): {url} "
                        f"(timestamp: {timestamp_str}) [type={url_type}]"
                    )
                    handled_in_this_pass.add(norm_url)
                    if norm_fallback_url:
                        handled_in_this_pass.add(norm_fallback_url)

            if new_downloads > 0:
                logger.info(f"{source_type} MONITOR: {new_downloads} new download(s) started")
            if new_downloads == 0:
                logger.debug(
                    f"{source_type} MONITOR: No new items (rows={total_rows}, "
                    f"skipped_in_history={skipped_already_in_history}, skipped_tracked={skipped_already_tracked}, "
                    f"skipped_missing_url={skipped_missing_url})"
                )

        except Exception as e:
            logger.error(f"Error checking for downloads: {e}", exc_info=True)

    @staticmethod
    def _normalize_and_deduplicate_history() -> None:
        """Normalize and deduplicate the persisted history file.

        Preserves earliest timestamp per logical URL.
        """
        try:
            existing = CSVService._load_structured_history()
            if not existing:
                return
            # Build minimal map url->timestamp keeping earliest timestamp (lexicographically smaller)
            ts_by_url: Dict[str, str] = {}
            for item in existing:
                url = CSVService._normalize_url(item.get('url') or '')
                ts = item.get('timestamp') or ''
                if not url:
                    continue
                if url in ts_by_url:
                    prev = ts_by_url[url]
                    ts_by_url[url] = min(prev or ts, ts or prev)
                else:
                    ts_by_url[url] = ts
            CSVService.save_download_history(set(ts_by_url.keys()))
        except Exception as e:
            logger.warning(f"Failed to normalize/deduplicate history: {e}")

    @staticmethod
    def clear_download_history() -> Dict[str, str]:
        """
        Clear download history.
        
        Returns:
            Result dictionary with status and message
        """
        try:
            # Persist as empty structured list
            with open(DOWNLOAD_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2)
            return {
                "status": "success",
                "message": "Download history cleared"
            }
        except Exception as e:
            logger.error(f"Error clearing download history: {e}")
            return {
                "status": "error",
                "message": f"Failed to clear download history: {str(e)}"
            }
    
    @staticmethod
    def get_statistics() -> Dict[str, Any]:
        """
        Get CSV service statistics.
        
        Returns:
            Statistics dictionary
        """
        history = CSVService.get_download_history()
        downloads_status = CSVService.get_csv_downloads_status()
        monitor_status = CSVService.get_monitor_status()

        return {
            "download_history_count": len(history),
            "active_downloads": downloads_status["total_active"],
            "monitor_status": monitor_status["csv_monitor"]["status"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
