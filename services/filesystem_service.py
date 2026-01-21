#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FilesystemService

Service layer responsible for safe filesystem-related operations required by the
frontend (searching cache folders and opening them locally on the host).

All business logic is centralized here per project standards.
"""
from __future__ import annotations

import logging
import os
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from datetime import datetime, date

from config.settings import config

logger = logging.getLogger(__name__)

CACHE_ROOT = Path(config.CACHE_ROOT_DIR)


@dataclass
class CacheSearchResult:
    """Result for a cache folder search.

    Attributes:
        number: The numeric identifier searched (as string to preserve formatting)
        matches: List of absolute paths to matching folders
        best_match: The best match path if determinable, else None
    """
    number: str
    matches: List[str]
    best_match: Optional[str]


class FilesystemService:
    """Service providing safe filesystem utilities for the app.

    This class intentionally restricts operations to known safe directories and
    validates inputs to prevent path traversal or unintended access.
    """

    @staticmethod
    def _ensure_cache_root() -> None:
        """Ensure the cache root exists, log a warning if not."""
        if not CACHE_ROOT.exists():
            logger.warning("CACHE_ROOT does not exist: %s", CACHE_ROOT)

    @staticmethod
    def find_cache_folder_by_number(number: str) -> CacheSearchResult:
        """Search for folders inside /mnt/cache that start with the given number.

        The expected folder format is for example: "115 Camille". We will match
        case-insensitively any directory whose basename starts with "{number}" and
        is followed by optional separators/spaces and text.

        Args:
            number: Numeric string provided by the user (e.g., "115"). Non-digits are ignored.

        Returns:
            CacheSearchResult with all matches and the best_match if exactly one clear match exists.
        """
        FilesystemService._ensure_cache_root()

        sanitized = re.sub(r"\D+", "", number or "")
        if not sanitized:
            logger.debug("Invalid number provided for cache search: %r", number)
            return CacheSearchResult(number=number or "", matches=[], best_match=None)

        if not CACHE_ROOT.exists() or not CACHE_ROOT.is_dir():
            return CacheSearchResult(number=sanitized, matches=[], best_match=None)

        regex = re.compile(rf"^{re.escape(sanitized)}[\s_-]?.*", re.IGNORECASE)

        matches: List[str] = []
        try:
            for entry in CACHE_ROOT.iterdir():
                try:
                    if entry.is_dir() and regex.match(entry.name):
                        matches.append(str(entry.resolve()))
                except PermissionError:
                    continue
        except Exception as e:
            logger.error("Error while scanning cache root: %s", e)
            return CacheSearchResult(number=sanitized, matches=[], best_match=None)

        best: Optional[str] = None
        if len(matches) == 1:
            best = matches[0]
        else:
            exact_regex = re.compile(rf"^{re.escape(sanitized)}\b.*", re.IGNORECASE)
            exact_matches = [m for m in matches if exact_regex.search(Path(m).name)]
            if len(exact_matches) >= 1:
                exact_matches.sort(key=lambda p: (len(Path(p).name), Path(p).name.lower()))
                best = exact_matches[0]

        return CacheSearchResult(number=sanitized, matches=matches, best_match=best)

    @staticmethod
    def open_path_in_explorer(abs_path: str, select_parent: bool = False) -> Tuple[bool, str]:
        """Open a given absolute path in the system's file explorer (server-side).

        IMPORTANT: This runs on the server where Flask is hosted. It assumes a desktop
        environment is available (e.g., the app is used locally). On headless servers,
        this will likely fail; we handle and return a clear error message.

        Args:
            abs_path: Absolute path to open.
            select_parent: If True, open the parent directory and try to preselect the target
                folder in the file manager when supported (nautilus/dolphin/thunar/nemo). If not
                supported, fall back to opening the parent directory.

        Returns:
            (success, message) tuple.
        """
        if config.DISABLE_EXPLORER_OPEN:
            logger.info("Explorer opening is disabled by configuration")
            return False, "Ouverture explorateur désactivée par configuration."
        if not config.DEBUG and not config.ENABLE_EXPLORER_OPEN:
            logger.info("Explorer opening is disabled in production/headless mode")
            return False, "Ouverture explorateur désactivée en production/headless."

        is_headless = not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        if is_headless and not config.ENABLE_EXPLORER_OPEN:
            logger.info("Explorer opening is disabled in headless mode")
            return False, "Ouverture explorateur désactivée en mode headless."
        try:
            path = Path(abs_path).resolve()
        except Exception:
            return False, "Chemin invalide."

        try:
            path.relative_to(CACHE_ROOT)
        except ValueError:
            return False, f"Chemin en dehors de {str(CACHE_ROOT)} non autorisé."

        if not path.exists():
            return False, "Le dossier n'existe pas."
        if not path.is_dir():
            return False, "Le chemin n'est pas un dossier."

        candidates: List[List[str]] = []

        if select_parent:
            parent = path.parent if path.parent.exists() else CACHE_ROOT
            candidates.extend([
                ["nautilus", "--no-desktop", "--browser", "--select", str(path)],
                ["nemo", "--no-desktop", "--browser", "--select", str(path)],
                ["dolphin", "--select", str(path)],
                ["thunar", "--select", str(path)],
                ["xdg-open", str(parent)],
                ["gio", "open", str(parent)],
                ["nautilus", str(parent)],
                ["nemo", str(parent)],
                ["thunar", str(parent)],
                ["dolphin", str(parent)],
            ])
        else:
            candidates.extend([
                ["xdg-open", str(path)],
                ["gio", "open", str(path)],
                ["nautilus", str(path)],
                ["nemo", str(path)],
                ["thunar", str(path)],
                ["dolphin", str(path)],
            ])

        last_error: Optional[str] = None
        for cmd in candidates:
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info(
                    "Opened path in explorer using %s (select_parent=%s): %s",
                    cmd[0], select_parent, str(path)
                )
                return True, "Dossier ouvert dans l'explorateur."
            except FileNotFoundError:
                last_error = f"Commande introuvable: {cmd[0]}"
                continue
            except Exception as e:
                last_error = str(e)
                continue

        return False, last_error or "Impossible d'ouvrir l'explorateur sur ce système."

    @staticmethod
    def list_today_cache_folders() -> List[Dict[str, Optional[str]]]:
        """List folders created/modified today under CACHE_ROOT with extracted numeric prefix.

        We use the folder's modification time (mtime) to approximate creation date across platforms,
        and filter only directories whose mtime date equals today's local date. For each folder, we
        extract a leading numeric sequence if present (e.g., "115 Camille" -> "115").

        Returns:
            A list of dicts with keys: {"path": str, "name": str, "number": Optional[str], "mtime": str}
            where mtime is ISO 8601 string for display/logging purposes.
        """
        FilesystemService._ensure_cache_root()

        results: List[Dict[str, Optional[str]]] = []
        if not CACHE_ROOT.exists() or not CACHE_ROOT.is_dir():
            return results

        today = date.today()
        number_regex = re.compile(r"^(\d+)")

        try:
            for entry in CACHE_ROOT.iterdir():
                try:
                    if not entry.is_dir():
                        continue
                    stat = entry.stat()
                    mtime_dt = datetime.fromtimestamp(stat.st_mtime)
                    if mtime_dt.date() != today:
                        continue
                    name = entry.name
                    m = number_regex.match(name)
                    number = m.group(1) if m else None
                    if number:
                        results.append({
                            "path": str(entry.resolve()),
                            "name": name,
                            "number": number,
                            "mtime": mtime_dt.isoformat()
                        })
                except PermissionError:
                    continue
                except Exception as e:
                    logger.warning("Skipping entry due to error: %s", e)
                    continue
        except Exception as e:
            logger.error("Error while listing today's cache folders: %s", e)
            return []

        results.sort(key=lambda x: x.get("mtime", ""), reverse=True)
        return results

    @staticmethod
    def sanitize_filename(filename_str: Optional[str], max_length: int = 230) -> str:
        """Sanitize filename for safe filesystem use.

        Args:
            filename_str: Original filename string (can be None)
            max_length: Maximum filename length (default: 230)

        Returns:
            Sanitized filename string
        """
        if filename_str is None:
            logger.warning("sanitize_filename: filename_str was None, using default 'fichier_nom_absent'.")
            filename_str = "fichier_nom_absent"
        
        s = str(filename_str).strip().replace(' ', '_')
        s = re.sub(r'(?u)[^-\w.]', '', s)
        
        if not s:
            s = "fichier_sans_nom_valide"
            logger.warning(f"sanitize_filename: Sanitized filename was empty for input '{filename_str}', using '{s}'.")
        
        if len(s) > max_length:
            original_full_name_for_log = s
            name_part, ext_part = os.path.splitext(s)
            max_name_len = max_length - len(ext_part) - (1 if ext_part else 0)
            if max_name_len < 1:
                s = s[:max_length]
            else:
                s = name_part[:max_name_len] + ext_part
            logger.info(f"sanitize_filename: Filename '{original_full_name_for_log}' truncated to '{s}' (max_length: {max_length}).")
        
        return s

    @staticmethod
    def format_bytes_human(n_bytes: int) -> str:
        """Return a human readable size string for bytes.

        Args:
            n_bytes: Number of bytes

        Returns:
            Formatted size string (e.g., '213.0KB', '151.5MB')
        """
        try:
            if n_bytes is None or n_bytes < 0:
                return "0B"
            if n_bytes < 1024:
                return f"{n_bytes}B"
            kb = n_bytes / 1024.0
            if kb < 1024.0:
                return f"{kb:.1f}KB"
            mb = kb / 1024.0
            return f"{mb:.1f}MB"
        except Exception:
            return f"{n_bytes}B"

    @staticmethod
    def find_videos_for_tracking(base_path: Path, keyword: str = None, subdir: str = None) -> List[str]:
        """Find video files that don't have corresponding JSON tracking results.

        Robust scan under 'projets_extraits/' for common video extensions.
        A video is considered already processed ONLY if an exact sibling JSON
        with the same stem exists (e.g., 'video.mp4' -> 'video.json').
        Files like '*_audio.json' are ignored for this check.

        Args:
            base_path: Base path to search under (typically BASE_PATH_SCRIPTS / 'projets_extraits')
            keyword: Optional keyword filter (informational, not enforced)
            subdir: Optional subdirectory filter (informational, not enforced)

        Returns:
            List of absolute paths to video files needing tracking
        """
        search_base = Path(base_path) / "projets_extraits" if "projets_extraits" not in str(base_path) else Path(base_path)
        logger.info(
            f"Searching for videos for tracking in {search_base} (filter info: keyword='{keyword}', subdir='{subdir}')"
        )
        
        videos_to_process = []
        video_extensions = (".mp4", ".avi", ".mov", ".mkv", ".webm")

        found_videos = 0
        already_processed = 0
        
        try:
            for video_file in search_base.rglob("*"):
                if not video_file.is_file():
                    continue
                if video_file.suffix.lower() not in video_extensions:
                    continue
                
                found_videos += 1
                json_file = video_file.with_suffix('.json')
                
                if json_file.exists():
                    already_processed += 1
                    continue
                
                videos_to_process.append(str(video_file.resolve()))
                logger.debug(f"Video to process found: {video_file}")

            logger.info(
                f"Videos detected: {found_videos}, already processed (exact JSON sibling): {already_processed}, to process: {len(videos_to_process)}"
            )
            
            if len(videos_to_process) == 0 and found_videos > 0 and already_processed == 0:
                logger.warning(
                    "No <stem>.json found but videos exist. Check write permissions and Step5 output paths."
                )
        except Exception as e:
            logger.error(f"Error scanning for videos: {e}")
        
        return videos_to_process
