#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download Service

Centralized service for managing file downloads from various sources (Dropbox, R2 worker proxy, ...).
Handles download execution, resumable streaming (.part + Range), progress tracking, file validation,
and typed error reporting.
"""

import logging
import os
import re
import time
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests

from config.settings import config
from services.csv_service import CSVService
from services.filesystem_service import FilesystemService

logger = logging.getLogger(__name__)

# Typed failure categories carried by DownloadResult.error_kind
ERROR_NOT_FOUND = 'not_found'
ERROR_AUTH = 'auth'
ERROR_HTTP = 'http_error'
ERROR_NETWORK = 'network'
ERROR_STALLED = 'stalled'
ERROR_INCOMPLETE = 'incomplete'
ERROR_INVALID_PAYLOAD = 'invalid_payload'
ERROR_LOCAL_IO = 'local_io'
ERROR_INTERNAL = 'internal'

# Retrying these would replay the exact same response: stop at the first failure
NON_RETRYABLE_ERROR_KINDS = frozenset({
    ERROR_NOT_FOUND,
    ERROR_AUTH,
    ERROR_INVALID_PAYLOAD,
    ERROR_LOCAL_IO,
    ERROR_INTERNAL,
})

_PART_SUFFIX = '.part'


def _safe_int(value: Any) -> Optional[int]:
    """Best-effort int conversion (headers coming from mocks/tests included)."""
    try:
        if value is None:
            return None
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _classify_status_code(status_code: Optional[int]) -> str:
    """Map an HTTP status code to a typed error kind."""
    if status_code is None:
        return ERROR_NETWORK
    if status_code in (404, 410):
        return ERROR_NOT_FOUND
    if status_code in (401, 403):
        return ERROR_AUTH
    return ERROR_HTTP


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
        status_code: Last HTTP status code observed
        error_kind: Typed failure category (see ERROR_* constants)
        bytes_downloaded: Bytes written during this call
        attempts: Number of HTTP attempts performed
        resumed_from: Offset the last attempt resumed from (0 when full restart)
        url: URL of the last attempt
    """
    success: bool
    download_id: str
    filename: str
    filepath: Optional[Path]
    size_bytes: int
    message: str
    status: str
    status_code: Optional[int] = None
    error_kind: Optional[str] = None
    bytes_downloaded: int = 0
    attempts: int = 0
    resumed_from: int = 0
    url: Optional[str] = None


@dataclass
class ProbeResult:
    """Best-effort HEAD probe result (never raises)."""
    status_code: Optional[int]
    content_type: str
    content_disposition: str
    content_length: Optional[int]
    accept_ranges: bool
    error: Optional[str] = None


@dataclass
class StreamResult:
    """Outcome of a single streaming attempt into the .part file."""
    ok: bool
    status_code: Optional[int]
    error_kind: Optional[str] = None
    error_message: str = ''
    total_on_disk: int = 0
    expected_total: Optional[int] = None
    content_type: str = ''
    restart_required: bool = False


class DownloadService:
    """Service for managing file downloads.

    This service handles:
    - Dropbox / R2 worker proxy file downloads
    - Resumable streaming through a `.part` file (HTTP Range)
    - Progress tracking and callbacks
    - File validation (ZIP archives, HTML/JSON error payloads)
    - Typed error reporting and bounded retries
    """

    # Download configuration (env-driven, see config/settings.py)
    CHUNK_SIZE_BYTES = max(1, int(getattr(config, 'DOWNLOAD_CHUNK_SIZE_BYTES', 512 * 1024)))
    REQUEST_TIMEOUT = (
        max(1, int(getattr(config, 'DOWNLOAD_CONNECT_TIMEOUT_S', 15))),
        max(1, int(getattr(config, 'DOWNLOAD_CHUNK_TIMEOUT_S', 60))),
    )
    MIN_ZIP_SIZE_BYTES = int(getattr(config, 'DOWNLOAD_MIN_ZIP_SIZE_BYTES', 1_000_000))

    @staticmethod
    def download_dropbox_file(
        url: str,
        timestamp: str,
        output_dir: Path,
        progress_callback: Optional[callable] = None,
        forced_filename: Optional[str] = None
    ) -> DownloadResult:
        """Download a file from a Dropbox or R2/worker proxy URL.

        Streams into `<name>.part`, resumes with HTTP Range when a previous
        attempt left data behind, and only renames to the final name once the
        payload is complete and validated.

        Args:
            url: URL to download from
            timestamp: Original timestamp from CSV/source
            output_dir: Directory to save downloaded file
            progress_callback: Optional callback(status, progress, message) for updates
            forced_filename: Optional filename override (from the webhook record)

        Returns:
            DownloadResult with download outcome
        """
        download_id = f"csv_{uuid.uuid4().hex[:8]}"
        job_label = f"CSV-DL-{timestamp.replace('/', '').replace(' ', '_').replace(':', '')}"
        attempts = 0
        resumed_from = 0
        last_status_code: Optional[int] = None
        last_error_kind: Optional[str] = None
        last_message = 'Download failed'

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
                status='failed',
                error_kind=ERROR_INTERNAL,
                url=url,
            )

        # 'identity' keeps Content-Length byte-exact (no transparent decompression),
        # which makes both the resume offset and the completeness check reliable.
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Encoding': 'identity',
        }

        probe = DownloadService._probe_remote(modified_url, headers, job_label)

        # Legacy behaviour: when the HEAD does not look like a ZIP, try the dl.* host
        if probe.content_type or probe.content_disposition:
            if not DownloadService._looks_like_zip(probe.content_type.lower(), probe.content_disposition.lower()):
                alt_url = CSVService.rewrite_dropbox_to_dl_host(modified_url)
                if alt_url != modified_url:
                    logger.info(f"DOWNLOAD [{job_label}]: Trying dl.dropboxusercontent.com")
                    modified_url = alt_url

        filename = DownloadService._resolve_target_filename(
            forced_filename=forced_filename,
            content_disposition=probe.content_disposition,
            timestamp=timestamp,
            url=modified_url,
        )
        target_path = DownloadService._resolve_filepath_conflicts(output_dir, filename)
        part_path = target_path.with_name(target_path.name + _PART_SUFFIX)

        max_attempts = max(1, int(getattr(config, 'DOWNLOAD_MAX_ATTEMPTS', 3)))
        backoff_s = max(0.0, float(getattr(config, 'DOWNLOAD_RETRY_BACKOFF_S', 1.0)))
        restart_required = False

        for attempt in range(1, max_attempts + 1):
            attempts = attempt

            if restart_required:
                DownloadService._discard_partial(part_path, job_label)
                restart_required = False

            offset = DownloadService._compute_resume_offset(part_path)
            if offset > 0:
                resumed_from = max(resumed_from, offset)
                logger.info(
                    f"DOWNLOAD [{job_label}]: Attempt {attempt}/{max_attempts} - resuming at "
                    f"{FilesystemService.format_bytes_human(offset)}"
                )
            else:
                logger.info(f"DOWNLOAD [{job_label}]: Attempt {attempt}/{max_attempts} - starting from 0")

            try:
                stream = DownloadService._stream_to_part(
                    url=modified_url,
                    part_path=part_path,
                    display_name=target_path.name,
                    offset=offset,
                    headers=headers,
                    job_label=job_label,
                    progress_callback=progress_callback,
                )
            except requests.exceptions.RequestException as e:
                last_status_code = None
                last_error_kind = DownloadService._classify_request_exception(e)
                last_message = DownloadService._format_transport_error(last_error_kind, e, job_label)
                logger.error(f"DOWNLOAD [{job_label}]: {last_message}")
            except OSError as e:
                last_status_code = None
                last_error_kind = ERROR_LOCAL_IO
                last_message = f"Local write error: {e}"
                logger.error(f"DOWNLOAD [{job_label}]: {last_message}")
            else:
                last_status_code = stream.status_code

                if stream.ok:
                    finalized, error_kind, message = DownloadService._finalize_download(
                        part_path=part_path,
                        target_path=target_path,
                        content_type=stream.content_type,
                        url=modified_url,
                        expected_size=stream.expected_total,
                    )
                    if finalized:
                        final_bytes = target_path.stat().st_size if target_path.exists() else 0
                        success_msg = (
                            f"File {target_path.name} "
                            f"({FilesystemService.format_bytes_human(final_bytes)}) downloaded"
                        )
                        logger.info(f"DOWNLOAD [{job_label}]: {success_msg}")
                        if progress_callback:
                            progress_callback('completed', 100, success_msg)
                        return DownloadResult(
                            success=True,
                            download_id=download_id,
                            filename=target_path.name,
                            filepath=target_path,
                            size_bytes=final_bytes,
                            message=success_msg,
                            status='completed',
                            status_code=stream.status_code,
                            bytes_downloaded=stream.total_on_disk,
                            attempts=attempt,
                            resumed_from=resumed_from,
                            url=modified_url,
                        )

                    last_error_kind = error_kind
                    last_message = message
                    logger.error(f"DOWNLOAD [{job_label}]: {message}")
                    if error_kind == ERROR_INVALID_PAYLOAD:
                        # Replaying the request would return the same payload
                        DownloadService._discard_partial(part_path, job_label)
                        break
                    restart_required = True
                else:
                    last_error_kind = stream.error_kind
                    last_message = stream.error_message
                    restart_required = bool(stream.restart_required)
                    logger.warning(
                        f"DOWNLOAD [{job_label}]: Attempt {attempt}/{max_attempts} failed "
                        f"({stream.error_kind}, HTTP {stream.status_code}): {stream.error_message}"
                    )
                    if stream.error_kind in NON_RETRYABLE_ERROR_KINDS:
                        break
                    if stream.restart_required:
                        DownloadService._discard_partial(part_path, job_label)
                        restart_required = False

            if attempt < max_attempts:
                delay = backoff_s * (2 ** (attempt - 1))
                if delay > 0:
                    time.sleep(delay)

        logger.error(
            f"DOWNLOAD [{job_label}]: FAILED after {attempts} attempt(s) - {last_message} "
            f"(kind={last_error_kind}, status={last_status_code}, target={target_path.name})"
        )
        if progress_callback:
            progress_callback('failed', 0, last_message)

        return DownloadResult(
            success=False,
            download_id=download_id,
            filename=target_path.name,
            filepath=None,
            size_bytes=0,
            message=last_message,
            status='failed',
            status_code=last_status_code,
            error_kind=last_error_kind,
            attempts=attempts,
            resumed_from=resumed_from,
            url=modified_url,
        )

    @staticmethod
    def _probe_remote(url: str, headers: Dict[str, str], job_label: str) -> ProbeResult:
        """Best-effort HEAD probe used to learn size, type and range support."""
        try:
            response = requests.head(
                url,
                headers=headers,
                timeout=max(1, int(getattr(config, 'DOWNLOAD_PROBE_TIMEOUT_S', 10))),
                allow_redirects=True,
            )
            response_headers = getattr(response, 'headers', {}) or {}
            status_code = _safe_int(getattr(response, 'status_code', None))
            content_type = str(response_headers.get('content-type', '') or '')
            content_disposition = str(response_headers.get('content-disposition', '') or '')
            content_length = _safe_int(response_headers.get('content-length'))
            accept_ranges = 'bytes' in str(response_headers.get('accept-ranges', '') or '').lower()

            logger.debug(
                f"DOWNLOAD [{job_label}]: HEAD status={status_code} type='{content_type or 'n/a'}' "
                f"length={content_length} range={'yes' if accept_ranges else 'no'}"
            )
            if status_code in (404, 410):
                logger.warning(
                    f"DOWNLOAD [{job_label}]: HEAD returned {status_code} - object may be absent "
                    f"upstream, confirming with GET"
                )

            return ProbeResult(
                status_code=status_code,
                content_type=content_type,
                content_disposition=content_disposition,
                content_length=content_length,
                accept_ranges=accept_ranges,
            )
        except Exception as e:
            logger.warning(f"DOWNLOAD [{job_label}]: HEAD request failed: {e}, proceeding anyway")
            return ProbeResult(
                status_code=None,
                content_type='',
                content_disposition='',
                content_length=None,
                accept_ranges=False,
                error=str(e),
            )

    @staticmethod
    def _resolve_target_filename(
        forced_filename: Optional[str],
        content_disposition: Optional[str],
        timestamp: str,
        url: str,
    ) -> str:
        """Resolve the final filename deterministically (needed for resume)."""
        if forced_filename and str(forced_filename).strip():
            safe_forced = Path(str(forced_filename)).name
            safe_forced = FilesystemService.sanitize_filename(safe_forced, max_length=230)
            if "dropbox.com/scl/fo/" in (url or '').lower():
                if not any(safe_forced.lower().endswith(ext) for ext in ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2']):
                    safe_forced = os.path.splitext(safe_forced)[0] + ".zip"
            return safe_forced

        return DownloadService._extract_filename(content_disposition, timestamp, url)

    @staticmethod
    def _compute_resume_offset(part_path: Path) -> int:
        """Bytes already written for this target (0 when nothing to resume)."""
        try:
            if part_path.exists():
                return int(part_path.stat().st_size)
        except OSError as e:
            logger.warning(f"Unable to inspect partial file {part_path}: {e}")
        return 0

    @staticmethod
    def _discard_partial(part_path: Path, job_label: str) -> None:
        """Drop an unusable partial file so the next attempt starts clean."""
        try:
            if part_path.exists():
                part_path.unlink()
                logger.info(f"DOWNLOAD [{job_label}]: Discarded partial file {part_path.name}")
        except OSError as e:
            logger.warning(f"DOWNLOAD [{job_label}]: Unable to remove partial file {part_path.name}: {e}")

    @staticmethod
    def _classify_request_exception(error: Exception) -> str:
        """Map a requests exception to a typed error kind."""
        if isinstance(error, requests.exceptions.Timeout):
            return ERROR_STALLED
        return ERROR_NETWORK

    @staticmethod
    def _format_transport_error(error_kind: Optional[str], error: Exception, job_label: str) -> str:
        """Human readable transport error, keeping the historical wording."""
        chunk_timeout = DownloadService.REQUEST_TIMEOUT[1]
        if error_kind == ERROR_STALLED:
            return f"Download stalled (timeout after {chunk_timeout}s with no data received): {error}"
        return f"Network error: {error}"

    @staticmethod
    def _stream_to_part(
        url: str,
        part_path: Path,
        display_name: str,
        offset: int,
        headers: Dict[str, str],
        job_label: str,
        progress_callback: Optional[callable] = None,
    ) -> StreamResult:
        """Stream the response body into the .part file (appending when resuming).

        Never raises for transport errors: they come back as a failed
        StreamResult so the caller can decide to retry with the bytes already
        on disk. Local write errors (ENOSPC, permissions) propagate as OSError.
        """
        request_headers = dict(headers)
        if offset > 0:
            request_headers['Range'] = f'bytes={offset}-'

        try:
            response = requests.get(
                url,
                stream=True,
                allow_redirects=True,
                timeout=DownloadService.REQUEST_TIMEOUT,
                headers=request_headers,
            )
        except requests.exceptions.RequestException as e:
            error_kind = DownloadService._classify_request_exception(e)
            return StreamResult(
                ok=False,
                status_code=None,
                error_kind=error_kind,
                error_message=DownloadService._format_transport_error(error_kind, e, job_label),
                total_on_disk=offset,
            )

        status_code = _safe_int(getattr(response, 'status_code', None))
        response_headers = getattr(response, 'headers', {}) or {}
        content_type = str(response_headers.get('content-type', '') or '')

        try:
            if status_code == 416:
                response.close()
                logger.warning(
                    f"DOWNLOAD [{job_label}]: HTTP 416 for range {offset} - partial file unusable, restarting from 0"
                )
                return StreamResult(
                    ok=False,
                    status_code=416,
                    error_kind=ERROR_INCOMPLETE,
                    error_message=f"Range {offset} rejected (HTTP 416)",
                    total_on_disk=offset,
                    restart_required=True,
                )

            if status_code is not None and status_code >= 400:
                error_kind = _classify_status_code(status_code)
                reason = str(getattr(response, 'reason', '') or '').strip()
                response.close()
                return StreamResult(
                    ok=False,
                    status_code=status_code,
                    error_kind=error_kind,
                    error_message=f"HTTP {status_code} ({error_kind}) {reason} for url: {url}".strip(),
                    total_on_disk=offset,
                    content_type=content_type,
                )

            logger.info(f"DOWNLOAD [{job_label}]: GET response status={status_code}")

            # The server may ignore Range and send the full body (200): never append in that case
            content_range = str(response_headers.get('content-range', '') or '')
            effective_offset = offset
            if offset > 0 and status_code != 206 and not content_range:
                logger.info(
                    f"DOWNLOAD [{job_label}]: Server ignored the Range header - restarting from 0"
                )
                effective_offset = 0

            expected_total = DownloadService._expected_total_size(
                status_code=status_code,
                response_headers=response_headers,
                effective_offset=effective_offset,
            )

            mode = 'ab' if effective_offset > 0 else 'wb'
            chunk_size = DownloadService.CHUNK_SIZE_BYTES
            min_interval = max(0.0, float(getattr(config, 'DOWNLOAD_PROGRESS_MIN_INTERVAL_S', 1.0)))
            last_emit = 0.0
            written_this_attempt = 0

            if progress_callback:
                start_pct = int((effective_offset / expected_total) * 100) if expected_total else 0
                progress_callback('downloading', start_pct, f'Starting download of {display_name}')

            try:
                with open(part_path, mode) as handle:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if not chunk:
                            continue
                        handle.write(chunk)
                        written_this_attempt += len(chunk)

                        if progress_callback and expected_total:
                            now = time.monotonic()
                            if (now - last_emit) >= min_interval:
                                last_emit = now
                                done = effective_offset + written_this_attempt
                                percentage = min(100, int((done / max(expected_total, 1)) * 100))
                                size_msg = (
                                    f'{FilesystemService.format_bytes_human(done)} / '
                                    f'{FilesystemService.format_bytes_human(expected_total)}'
                                )
                                progress_callback('downloading', percentage, size_msg)
            finally:
                response.close()

            total_on_disk = effective_offset + written_this_attempt
            logger.info(
                f"DOWNLOAD [{job_label}]: Stream finished - "
                f"{FilesystemService.format_bytes_human(total_on_disk)} on disk"
                + (f" / {FilesystemService.format_bytes_human(expected_total)} expected" if expected_total else "")
            )

            if expected_total is not None and total_on_disk != expected_total:
                return StreamResult(
                    ok=False,
                    status_code=status_code,
                    error_kind=ERROR_INCOMPLETE,
                    error_message=(
                        f"Incomplete download: {total_on_disk} bytes received, "
                        f"{expected_total} expected"
                    ),
                    total_on_disk=total_on_disk,
                    expected_total=expected_total,
                    content_type=content_type,
                    restart_required=total_on_disk > expected_total,
                )

            return StreamResult(
                ok=True,
                status_code=status_code,
                total_on_disk=total_on_disk,
                expected_total=expected_total,
                content_type=content_type,
            )

        except requests.exceptions.RequestException as e:
            # Interrupted mid-stream: keep what was written, the next attempt resumes
            error_kind = DownloadService._classify_request_exception(e)
            try:
                partial = part_path.stat().st_size if part_path.exists() else offset
            except OSError:
                partial = offset
            return StreamResult(
                ok=False,
                status_code=status_code,
                error_kind=error_kind,
                error_message=DownloadService._format_transport_error(error_kind, e, job_label),
                total_on_disk=partial,
                content_type=content_type,
            )

    @staticmethod
    def _expected_total_size(
        status_code: Optional[int],
        response_headers: Any,
        effective_offset: int,
    ) -> Optional[int]:
        """Total object size derived from Content-Range / Content-Length."""
        content_range = str(response_headers.get('content-range', '') or '').strip()
        if content_range:
            match = re.search(r'/(\d+)\s*$', content_range)
            if match:
                return _safe_int(match.group(1))

        content_length = _safe_int(response_headers.get('content-length'))
        if content_length is None:
            return None
        if status_code == 206:
            return effective_offset + content_length
        return content_length

    @staticmethod
    def _finalize_download(
        part_path: Path,
        target_path: Path,
        content_type: str,
        url: str,
        expected_size: Optional[int],
    ) -> Tuple[bool, Optional[str], str]:
        """Validate the .part payload and atomically promote it to the target name."""
        if not part_path.exists():
            return False, ERROR_INCOMPLETE, f"Downloaded data missing for {target_path.name}"

        final_bytes = part_path.stat().st_size
        if expected_size is not None and final_bytes != expected_size:
            return False, ERROR_INCOMPLETE, (
                f"Incomplete download: {final_bytes} bytes received, {expected_size} expected"
            )

        expected_zip = (
            target_path.suffix.lower() == '.zip'
            or 'zip' in (content_type or '').lower()
            or '.zip' in (url or '').lower()
        )
        if not DownloadService._validate_download(
            part_path, content_type, url, final_bytes, expected_zip=expected_zip
        ):
            return False, ERROR_INVALID_PAYLOAD, (
                f"Invalid ZIP response (Content-Type='{content_type}', Size={final_bytes} bytes)"
            )

        try:
            os.replace(part_path, target_path)
        except OSError as e:
            return False, ERROR_LOCAL_IO, f"Unable to finalize {target_path.name}: {e}"

        return True, None, ''

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
    def _is_valid_zip_payload(filepath: Path) -> bool:
        """Validate the ZIP central directory (fast: reads the end of the file)."""
        try:
            if not filepath.exists() or filepath.stat().st_size < 22:
                return False
            with open(filepath, 'rb') as handle:
                header = handle.read(4)
            if header[:2] != b'PK':
                return False
            return zipfile.is_zipfile(filepath)
        except (OSError, zipfile.BadZipFile) as e:
            logger.warning(f"ZIP payload check failed for {filepath.name}: {e}")
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
        size_bytes: int,
        expected_zip: Optional[bool] = None,
    ) -> bool:
        """Validate that a downloaded payload is usable.

        Applies to every download (not only Dropbox folder links): a 200 answer
        carrying an HTML/JSON error page must never be treated as an archive,
        otherwise it lands on disk and the URL is blacklisted in the history.

        Args:
            filepath: Path to the downloaded data
            content_type: Content-Type from response
            url: Original download URL
            size_bytes: Size of downloaded data
            expected_zip: Force the archive check (defaults to the file extension)

        Returns:
            True if the payload appears valid
        """
        if not filepath.exists():
            return False

        ct_lower = (content_type or '').lower()
        is_folder_link = '/scl/fo/' in (url or '').lower()
        if expected_zip is None:
            expected_zip = filepath.suffix.lower() == '.zip'

        if size_bytes <= 0:
            logger.warning(f"Empty download for {filepath.name}")
            return False

        if 'text/html' in ct_lower or 'application/json' in ct_lower \
                or 'text/xml' in ct_lower or 'application/xml' in ct_lower:
            logger.warning(f"Payload served with non-archive Content-Type '{content_type}' for {filepath.name}")
            return False

        looks_like_zip = 'zip' in ct_lower or 'octet-stream' in ct_lower

        if is_folder_link:
            # Size check: folder ZIPs should be at least 1MB
            # Smaller responses are likely HTML interstitials
            if size_bytes < DownloadService.MIN_ZIP_SIZE_BYTES:
                logger.warning(f"Downloaded file too small for folder ZIP: {size_bytes} bytes")
                return False

            if not looks_like_zip:
                logger.warning(f"Content-Type doesn't indicate ZIP: {content_type}")
                return False

        if expected_zip and getattr(config, 'DOWNLOAD_VALIDATE_ZIP', True):
            if not DownloadService._is_valid_zip_payload(filepath):
                logger.warning(f"Payload is not a readable ZIP archive: {filepath.name}")
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
