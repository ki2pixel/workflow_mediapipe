#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download Service

Centralized service for managing file downloads from various sources (Dropbox, OneDrive, etc.).
Handles download execution, progress tracking, file validation, and error handling.
"""

import logging
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import requests

from config.settings import config
from services.csv_service import CSVService
from services.filesystem_service import FilesystemService

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Result of a download operation.
    
    Attributes:
        success: Whether the download succeeded
        download_id: Unique identifier for this download
        filename: Name of the downloaded file
        filepath: Full path to the downloaded file
        size_bytes: Size of downloaded file in bytes
        message: Status or error message
        status: Final status ('completed', 'failed', 'cancelled')
    """
    success: bool
    download_id: str
    filename: str
    filepath: Optional[Path]
    size_bytes: int
    message: str
    status: str


class DownloadService:
    """Service for managing file downloads.
    
    This service handles:
    - Dropbox file downloads
    - OneDrive file downloads
    - Progress tracking and callbacks
    - File validation (ZIP archives)
    - Error handling and retries
    """
    
    # Download configuration
    CHUNK_SIZE_BYTES = 512 * 1024  # 512KB chunks
    REQUEST_TIMEOUT = (15, 3600)  # (connect, read) timeouts
    MIN_ZIP_SIZE_BYTES = 1_000_000  # 1MB minimum for folder downloads
    
    @staticmethod
    def download_dropbox_file(
        url: str,
        timestamp: str,
        output_dir: Path,
        progress_callback: Optional[callable] = None,
        forced_filename: Optional[str] = None
    ) -> DownloadResult:
        """Download a file from Dropbox URL.
        
        Handles both direct file links and folder share links. Applies URL
        normalization, retries on failure, and validates ZIP archives.
        
        Args:
            url: Dropbox URL to download from
            timestamp: Original timestamp from CSV/source
            output_dir: Directory to save downloaded file
            progress_callback: Optional callback(status, progress, message) for updates
            
        Returns:
            DownloadResult with download outcome
        """
        download_id = f"csv_{uuid.uuid4().hex[:8]}"
        job_label = f"CSV-DL-{timestamp.replace('/', '').replace(' ', '_').replace(':', '')}"
        
        logger.info(f"DOWNLOAD [{job_label} ID: {download_id}]: Starting download from {url}")
        
        # Normalize and prepare URL
        try:
            normalized_url = CSVService._normalize_url(url)
            modified_url = normalized_url.replace("dl=0", "dl=1")
            logger.debug(f"DOWNLOAD [{job_label}]: Normalized URL: {modified_url}")
        except Exception as e:
            logger.error(f"DOWNLOAD [{job_label}]: URL normalization failed: {e}")
            return DownloadResult(
                success=False,
                download_id=download_id,
                filename='',
                filepath=None,
                size_bytes=0,
                message=f"URL normalization error: {e}",
                status='failed'
            )
        
        # Prepare request headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Try to determine if response will be a ZIP
        try:
            response_head = requests.head(modified_url, headers=headers, timeout=10, allow_redirects=True)
            ct_head = response_head.headers.get('content-type', '').lower()
            cd_head = response_head.headers.get('content-disposition', '').lower()
            
            logger.debug(f"DOWNLOAD [{job_label}]: HEAD response - Content-Type: {ct_head}")
            
            # If HEAD doesn't indicate ZIP, try alternate URL
            if not DownloadService._looks_like_zip(ct_head, cd_head):
                alt_url = CSVService.rewrite_dropbox_to_dl_host(modified_url)
                if alt_url != modified_url:
                    logger.info(f"DOWNLOAD [{job_label}]: Trying dl.dropboxusercontent.com")
                    modified_url = alt_url
        except Exception as e:
            logger.warning(f"DOWNLOAD [{job_label}]: HEAD request failed: {e}, proceeding anyway")
        
        # Execute download
        try:
            response = requests.get(
                modified_url,
                stream=True,
                allow_redirects=True,
                timeout=DownloadService.REQUEST_TIMEOUT,
                headers=headers
            )
            response.raise_for_status()
            
            logger.info(f"DOWNLOAD [{job_label}]: GET response status={response.status_code}")
            
            # Determine filename
            if forced_filename and str(forced_filename).strip():
                safe_forced = Path(str(forced_filename)).name
                safe_forced = FilesystemService.sanitize_filename(safe_forced, max_length=230)
                # Ensure archive-like extension for Dropbox folder links
                if "dropbox.com/scl/fo/" in modified_url.lower():
                    if not any(safe_forced.lower().endswith(ext) for ext in ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2']):
                        safe_forced = os.path.splitext(safe_forced)[0] + ".zip"
                filename = safe_forced
            else:
                filename = DownloadService._extract_filename(
                    response.headers.get('content-disposition'),
                    timestamp,
                    modified_url
                )
            
            # Handle filename conflicts
            filepath = DownloadService._resolve_filepath_conflicts(output_dir, filename)
            
            # Download with progress tracking
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            logger.info(f"DOWNLOAD [{job_label}]: Starting download to {filepath.name}")
            
            if progress_callback:
                progress_callback('downloading', 0, f'Starting download of {filename}')
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=DownloadService.CHUNK_SIZE_BYTES):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0 and progress_callback:
                            percentage = int((downloaded_size / max(total_size, 1)) * 100)
                            size_msg = f'{FilesystemService.format_bytes_human(downloaded_size)} / {FilesystemService.format_bytes_human(total_size)}'
                            progress_callback('downloading', percentage, size_msg)
            
            # Validate downloaded file
            final_bytes = filepath.stat().st_size if filepath.exists() else 0
            ct_final = response.headers.get('content-type', '').lower()
            
            if not DownloadService._validate_download(filepath, ct_final, modified_url, final_bytes):
                error_msg = f"Invalid ZIP response (Content-Type='{ct_final}', Size={final_bytes} bytes)"
                logger.error(f"DOWNLOAD [{job_label}]: {error_msg}")
                
                if progress_callback:
                    progress_callback('failed', 0, error_msg)
                
                return DownloadResult(
                    success=False,
                    download_id=download_id,
                    filename=filepath.name,
                    filepath=filepath,
                    size_bytes=final_bytes,
                    message=error_msg,
                    status='failed'
                )
            
            # Success
            success_msg = f"File {filepath.name} ({FilesystemService.format_bytes_human(final_bytes)}) downloaded"
            logger.info(f"DOWNLOAD [{job_label}]: {success_msg}")
            
            if progress_callback:
                progress_callback('completed', 100, success_msg)
            
            return DownloadResult(
                success=True,
                download_id=download_id,
                filename=filepath.name,
                filepath=filepath,
                size_bytes=final_bytes,
                message=success_msg,
                status='completed'
            )
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(f"DOWNLOAD [{job_label}]: {error_msg}")
            
            if progress_callback:
                progress_callback('failed', 0, error_msg)
            
            return DownloadResult(
                success=False,
                download_id=download_id,
                filename='',
                filepath=None,
                size_bytes=0,
                message=error_msg,
                status='failed'
            )
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"DOWNLOAD [{job_label}]: {error_msg}", exc_info=True)
            
            if progress_callback:
                progress_callback('failed', 0, error_msg)
            
            return DownloadResult(
                success=False,
                download_id=download_id,
                filename='',
                filepath=None,
                size_bytes=0,
                message=error_msg,
                status='failed'
            )
    
    @staticmethod
    def _looks_like_zip(content_type: str, content_disposition: str) -> bool:
        """Check if HTTP headers indicate a ZIP file.
        
        Args:
            content_type: Content-Type header value
            content_disposition: Content-Disposition header value
            
        Returns:
            True if headers suggest a ZIP file
        """
        if not content_type and not content_disposition:
            return False
        
        ct_lower = (content_type or '').lower()
        cd_lower = (content_disposition or '').lower()
        
        # Check for ZIP-related content types
        if 'zip' in ct_lower or 'octet-stream' in ct_lower:
            return True
        
        # Check if filename in Content-Disposition suggests a file
        if 'filename' in cd_lower:
            return True
        
        return False
    
    @staticmethod
    def _extract_filename(
        content_disposition: Optional[str],
        timestamp: str,
        url: str
    ) -> str:
        """Extract filename from Content-Disposition header or generate default.
        
        Args:
            content_disposition: Content-Disposition header value
            timestamp: Timestamp for fallback filename
            url: Download URL for context
            
        Returns:
            Sanitized filename
        """
        # Default filename based on timestamp
        default_filename = f"download_{timestamp.replace('/', '').replace(' ', '_').replace(':', '')}"
        
        if not content_disposition:
            filename = default_filename
        else:
            # Try UTF-8 encoded filename
            m_utf8 = re.search(r"filename\*=UTF-8''([^;\n\r]+)", content_disposition, re.IGNORECASE)
            if m_utf8:
                extracted = requests.utils.unquote(m_utf8.group(1))
                filename = FilesystemService.sanitize_filename(extracted, max_length=230)
            else:
                # Try simple quoted filename
                m_simple = re.search(r'filename="([^"]+)"', content_disposition, re.IGNORECASE)
                if m_simple:
                    extracted = m_simple.group(1)
                    # Decode if URL-encoded
                    if '%' in extracted:
                        try:
                            extracted = requests.utils.unquote(extracted)
                        except Exception:
                            pass
                    filename = FilesystemService.sanitize_filename(extracted, max_length=230)
                else:
                    filename = default_filename
        
        # Add .zip extension for Dropbox folder links
        if "dropbox.com/scl/fo/" in url.lower():
            if not any(filename.lower().endswith(ext) for ext in ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2']):
                filename = os.path.splitext(filename)[0] + ".zip"
        
        return filename
    
    @staticmethod
    def _resolve_filepath_conflicts(output_dir: Path, filename: str) -> Path:
        """Resolve filename conflicts by adding counter suffix.
        
        Args:
            output_dir: Directory where file will be saved
            filename: Desired filename
            
        Returns:
            Path object with unique filename
        """
        filepath = output_dir / filename
        
        if not filepath.exists():
            return filepath
        
        # File exists, add counter
        counter = 1
        stem = filepath.stem
        suffix = filepath.suffix
        
        while filepath.exists():
            new_name = f"{stem}_{counter}{suffix}"
            filepath = output_dir / new_name
            counter += 1
            
            if counter > 1000:  # Safety limit
                logger.warning(f"Exceeded conflict resolution limit for {filename}")
                break
        
        return filepath
    
    @staticmethod
    def _validate_download(
        filepath: Path,
        content_type: str,
        url: str,
        size_bytes: int
    ) -> bool:
        """Validate that downloaded file is valid (especially for ZIP archives).
        
        Args:
            filepath: Path to downloaded file
            content_type: Content-Type from response
            url: Original download URL
            size_bytes: Size of downloaded file
            
        Returns:
            True if file appears valid
        """
        if not filepath.exists():
            return False
        
        # Check if it's supposed to be a ZIP (folder share)
        is_folder_link = '/scl/fo/' in url.lower()
        
        if not is_folder_link:
            # Not a folder link, accept any response
            return True
        
        # For folder links, validate it's actually a ZIP
        ct_lower = content_type.lower()
        looks_like_zip = 'zip' in ct_lower or 'octet-stream' in ct_lower
        
        # Size check: folder ZIPs should be at least 1MB
        # Smaller responses are likely HTML interstitials
        if size_bytes < DownloadService.MIN_ZIP_SIZE_BYTES:
            logger.warning(f"Downloaded file too small for folder ZIP: {size_bytes} bytes")
            return False
        
        if not looks_like_zip:
            logger.warning(f"Content-Type doesn't indicate ZIP: {content_type}")
            return False
        
        return True
    
    @staticmethod
    def create_progress_callback(
        download_id: str,
        update_function: callable
    ) -> callable:
        """Create a progress callback that updates download status.
        
        Args:
            download_id: ID of the download to update
            update_function: Function(download_id, status, progress, message) to call
            
        Returns:
            Callback function(status, progress, message)
        """
        def callback(status: str, progress: int, message: str):
            try:
                update_function(download_id, status, progress, message)
            except Exception as e:
                logger.error(f"Progress callback error for {download_id}: {e}")
        
        return callback
