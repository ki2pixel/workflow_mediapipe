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

        forced_name = str(original_filename).strip() if original_filename else None

        result = None
        last_attempt_url = dropbox_url
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
                break

        if result and result.success:
            CSVService.update_csv_download(
                download_id,
                'completed',
                progress=100,
                message=result.message,
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
            
            logger.info(f"CSV DOWNLOAD: File '{result.filename}' downloaded successfully ({result.size_bytes} bytes)")
        else:
            CSVService.update_csv_download(
                download_id,
                'failed',
                message=result.message if result else 'N/A',
                filename=result.filename if (result and result.filename) else 'N/A',
                display_timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                timestamp=datetime.now()
            )
            logger.error(
                f"CSV DOWNLOAD: Failed - {(result.message if result else 'N/A')} (last_url={last_attempt_url})"
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
