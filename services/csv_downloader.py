#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV Downloader Service
Handles downloading files from URLs asynchronously.
"""

import logging
import uuid
import urllib.parse
from datetime import datetime
from pathlib import Path

from config.settings import config
from services.csv_service import CSVService
from services.download_service import DownloadService

logger = logging.getLogger(__name__)

LOCAL_DOWNLOADS_DIR = config.LOCAL_DOWNLOADS_DIR

def execute_csv_download_worker(dropbox_url, timestamp_str, fallback_url=None, original_filename=None):
    """Worker background task to execute a CSV download with fallback try."""
    LOCAL_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    
    download_id = f"csv_{uuid.uuid4().hex[:8]}"
    
    download_info = {
        'id': download_id,
        'filename': 'Détermination en cours...',
        'original_url': dropbox_url,
        'url': dropbox_url,
        'url_type': 'dropbox',
        'status': 'pending',
        'progress': 0,
        'message': 'En attente de démarrage...',
        'timestamp': datetime.now(),
        'display_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'csv_timestamp': timestamp_str
    }
    
    CSVService.add_csv_download(download_id, download_info)
    
    def progress_callback(status, progress, message):
        """Callback to update CSVService with download progress."""
        update_kwargs = {
            'progress': progress,
            'message': message,
            'display_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'timestamp': datetime.now()
        }
        CSVService.update_csv_download(download_id, status, **update_kwargs)
    
    try:
        urls_to_try = [dropbox_url]
        if fallback_url and str(fallback_url).strip() and str(fallback_url).strip() != str(dropbox_url).strip():
            urls_to_try.append(str(fallback_url).strip())

        # R2 copies are short-lived on the worker side: once a URL is known to be
        # missing, start with the Dropbox source link instead of replaying a
        # doomed request on every retry.
        fallback_first = False
        if len(urls_to_try) == 2:
            known_failure = CSVService.get_download_failure_map().get(CSVService._normalize_url(dropbox_url))
            if known_failure and known_failure.get('kind') == 'not_found':
                urls_to_try = list(reversed(urls_to_try))
                fallback_first = True
                logger.info(
                    f"CSV DOWNLOAD: Known missing R2 object for {dropbox_url} - trying the Dropbox "
                    f"source URL first"
                )

        forced_name = str(original_filename).strip() if original_filename else None

        result = None
        last_attempt_url = urls_to_try[0]
        failed_attempts = []
        used_fallback = fallback_first

        for attempt_url in urls_to_try:
            last_attempt_url = attempt_url
            result = DownloadService.download_dropbox_file(
                url=attempt_url,
                timestamp=timestamp_str,
                output_dir=LOCAL_DOWNLOADS_DIR,
                progress_callback=progress_callback,
                forced_filename=forced_name
            )
            if result and result.success:
                if attempt_url != dropbox_url:
                    used_fallback = True
                break

            failed_attempts.append(result)

            # A missing object on the worker side is an expected situation: fall
            # back to the Dropbox source link right away, without extra retries.
            if result and result.error_kind == 'not_found' and attempt_url == dropbox_url:
                logger.warning(
                    f"CSV DOWNLOAD: R2_MISSING url={attempt_url} "
                    f"filename={forced_name or 'unknown'} - falling back to source URL"
                )

        if result and result.success:
            if used_fallback:
                message = f"{result.message} (R2 absent - repli Dropbox utilisé)"
            else:
                message = result.message
            CSVService.update_csv_download(
                download_id,
                'completed',
                progress=100,
                message=message,
                filename=result.filename,
                display_timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                timestamp=datetime.now()
            )
            
            try:
                CSVService.add_to_download_history_with_timestamp(dropbox_url, timestamp_str)
                if fallback_url and str(fallback_url).strip():
                    CSVService.add_to_download_history_with_timestamp(str(fallback_url).strip(), timestamp_str)
            except Exception as e:
                logger.error(f"Error adding to download history: {e}")

            for attempt_url in urls_to_try:
                try:
                    CSVService.clear_download_failure(attempt_url)
                except Exception as e:
                    logger.warning(f"Error clearing download failure for {attempt_url}: {e}")

            logger.info(f"CSV DOWNLOAD: File '{result.filename}' downloaded successfully ({result.size_bytes} bytes)")
        else:
            error_message = result.message if result else 'N/A'
            for failed in failed_attempts:
                failed_url = failed.url or last_attempt_url
                try:
                    CSVService.record_download_failure(
                        failed_url,
                        failed.error_kind or 'unknown_error',
                        failed.status_code,
                        failed.message,
                    )
                except Exception as e:
                    logger.warning(f"Error recording download failure for {failed_url}: {e}")

            CSVService.update_csv_download(
                download_id,
                'failed',
                message=error_message,
                filename=result.filename if (result and result.filename) else 'N/A',
                display_timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                timestamp=datetime.now()
            )
            logger.error(
                f"CSV DOWNLOAD: Failed - {error_message} "
                f"(kind={result.error_kind if result else 'n/a'}, last_url={last_attempt_url})"
            )
            
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"CSV DOWNLOAD: {error_msg}", exc_info=True)
        CSVService.update_csv_download(
            download_id,
            'failed',
            message=error_msg,
            display_timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            timestamp=datetime.now()
        )
    
    logger.info(f"CSV DOWNLOAD: Worker for {download_id} completed")
