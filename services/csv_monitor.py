#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV Webhook Monitoring Service
Handles polling the webhook API and starting download workers.
"""

import os
import time
import logging
import threading
import urllib.parse
from datetime import datetime
from typing import Set, Optional

from config.settings import config

from services.csv_downloader import execute_csv_download_worker
from services.workflow_state import get_workflow_state

logger = logging.getLogger(__name__)

# Import WebhookService for external JSON source
try:
    from services.webhook_service import (
        fetch_records as webhook_fetch_records,
        get_service_status as webhook_status
    )
    WEBHOOK_SERVICE_AVAILABLE = True
except Exception:
    WEBHOOK_SERVICE_AVAILABLE = False
    def webhook_status():
        return {"available": False, "error": "WebhookService not available"}

WEBHOOK_MONITOR_INTERVAL = config.WEBHOOK_MONITOR_INTERVAL

def check_csv_for_downloads() -> None:
    """
    Check for new downloads using Webhook as the single data source.
    """
    import services.csv_service as csv_service_module
    CSVService = csv_service_module.CSVService
    _is_dropbox_url = csv_service_module._is_dropbox_url
    _is_dropbox_proxy_url = csv_service_module._is_dropbox_proxy_url
    _looks_like_archive_download = csv_service_module._looks_like_archive_download
    webhook_service_available = getattr(csv_service_module, 'WEBHOOK_SERVICE_AVAILABLE', False)
    webhook_fetch_records = getattr(csv_service_module, 'webhook_fetch_records', None)

    try:
        # Fetch data from Webhook (single data source)
        if not webhook_service_available or webhook_fetch_records is None:
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
                continue
            if _is_url_already_tracked(norm_url, norm_fallback_url):
                handled_in_this_pass.add(norm_url)
                if norm_fallback_url:
                    handled_in_this_pass.add(norm_fallback_url)
                continue
            if already_in_history:
                # Common case: preferred URL removed from history, but fallback URL still present.
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

    except Exception as e:
        logger.error(f"Error in check_csv_for_downloads: {e}", exc_info=True)


def csv_monitor_service():
    """Service de monitoring Webhook qui s'exécute en arrière-plan."""
    logger.info("WEBHOOK MONITOR: Service démarré.")

    workflow_state = get_workflow_state()

    while True:
        try:
            workflow_state.update_csv_monitor_status(
                status="checking",
                last_check=datetime.now().isoformat(),
                error=None
            )

            try:
                check_csv_for_downloads()
                logger.debug("Webhook monitor check completed successfully")
            except Exception as check_error:
                logger.error(f"Webhook monitor check error: {check_error}")
                workflow_state.update_csv_monitor_status(
                    status="error",
                    last_check=datetime.now().isoformat(),
                    error=str(check_error)
                )
                time.sleep(WEBHOOK_MONITOR_INTERVAL)
                continue

            workflow_state.update_csv_monitor_status(
                status="active",
                last_check=datetime.now().isoformat(),
                error=None
            )

        except Exception as e:
            error_msg = f"Erreur dans le service CSV monitor: {e}"
            logger.error(error_msg, exc_info=True)
            workflow_state.update_csv_monitor_status(
                status="error",
                last_check=datetime.now().isoformat(),
                error=error_msg
            )
            
        time.sleep(WEBHOOK_MONITOR_INTERVAL)
