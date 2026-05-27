#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CleanupService

Service layer responsible for continuous cleanup of orphaned temporary projects.
Identifies and safely removes directories in PROJECTS_DIR that have not been
modified for a specified threshold time, ensuring critical folders (like archives)
are strictly protected.
"""
from __future__ import annotations

import logging
import os
import shutil
import time
from pathlib import Path
from typing import Dict, List, Any

from config.settings import config
from services.filesystem_service import FilesystemService

logger = logging.getLogger(__name__)


class CleanupService:
    """Service providing safe, continuous cleanup capabilities for orphaned projects."""

    # Explicitly protected directory names that should never be cleaned up
    PROTECTED_DIR_NAMES = {"archives", "logs", "docs", "static", "templates", ".git", "_finalized_output", "venv", "env"}

    @staticmethod
    def _safe_rmtree(path: Path) -> None:
        """Removes a directory tree, properly logging permission errors.
        Copied pattern from finalized_and_copy.py.
        """
        def _onerror(func, p, exc_info):
            logger.error(f"Suppression échouée sur '{p}' par {func.__name__}: {exc_info[1]}")

        shutil.rmtree(path, onerror=_onerror)

    @staticmethod
    def is_path_protected(path: Path) -> bool:
        """Determines if a given path is protected and should be excluded from cleanup.

        Ensures we never accidentally delete config.ARCHIVES_DIR, config.LOCAL_DOWNLOADS_DIR,
        config.LOGS_DIR or directories with protected names.
        """
        try:
            abs_path = path.resolve()
            
            # Check against globally protected directories defined in config
            protected_global_paths = [
                config.ARCHIVES_DIR.resolve() if config.ARCHIVES_DIR else None,
                config.LOGS_DIR.resolve() if config.LOGS_DIR else None,
                config.LOCAL_DOWNLOADS_DIR.resolve() if config.LOCAL_DOWNLOADS_DIR else None,
                config.BASE_PATH_SCRIPTS.resolve() if config.BASE_PATH_SCRIPTS else None
            ]

            for p_path in protected_global_paths:
                if not p_path:
                    continue
                # If path is exactly the protected path or a parent of it
                if abs_path == p_path or p_path in abs_path.parents:
                    return True
                # If the protected path is inside the current path (e.g., path is 'projets_extraits' and p_path is 'projets_extraits/archives')
                if abs_path in p_path.parents:
                    # We might not want to delete projects_extraits itself, but we are only given subdirectories of it.
                    # However, if a protected path is inside this path, deleting this path would delete the protected one!
                    return True

            # Check local naming
            if abs_path.name.lower() in CleanupService.PROTECTED_DIR_NAMES:
                return True

            # Check for _temp_ directories which might be actively used by extraction processes
            if abs_path.name.startswith("_temp_") or abs_path.name.startswith("."):
                return True

            return False
        except Exception as e:
            logger.error(f"Error checking if path is protected '{path}': {e}")
            # When in doubt, protect it
            return True

    @staticmethod
    def get_last_modified_time(path: Path) -> float:
        """Calculates the most recent modification time of a directory and all its contents.
        
        Args:
            path: Directory path to scan
            
        Returns:
            Highest mtime timestamp (float)
        """
        try:
            last_mtime = path.stat().st_mtime
        except Exception:
            last_mtime = 0.0

        try:
            for entry in path.rglob("*"):
                try:
                    mtime = entry.stat().st_mtime
                    if mtime > last_mtime:
                        last_mtime = mtime
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Error scanning '{path}' for mtime: {e}")
            
        return last_mtime

    @staticmethod
    def get_directory_size(path: Path) -> int:
        """Calculates total size of a directory in bytes."""
        total_size = 0
        try:
            for entry in path.rglob("*"):
                if entry.is_file():
                    try:
                        total_size += entry.stat().st_size
                    except Exception:
                        continue
        except Exception:
            pass
        return total_size

    @staticmethod
    def get_orphan_projects(threshold_hours: int = 48) -> List[Dict[str, Any]]:
        """Scans PROJECTS_DIR for directories that haven't been modified in `threshold_hours`.
        
        Args:
            threshold_hours: Minimum hours of inactivity to consider a project orphaned.
            
        Returns:
            List of dictionaries containing orphan details.
        """
        orphans = []
        
        if not config.PROJECTS_DIR or not config.PROJECTS_DIR.exists():
            logger.warning(f"PROJECTS_DIR '{config.PROJECTS_DIR}' does not exist. Cleanup skipped.")
            return orphans

        current_time = time.time()
        threshold_seconds = threshold_hours * 3600

        try:
            for entry in config.PROJECTS_DIR.iterdir():
                if not entry.is_dir():
                    continue

                if CleanupService.is_path_protected(entry):
                    logger.debug(f"Path '{entry}' is protected. Skipping cleanup check.")
                    continue

                last_mtime = CleanupService.get_last_modified_time(entry)
                age_seconds = current_time - last_mtime

                if age_seconds > threshold_seconds:
                    size_bytes = CleanupService.get_directory_size(entry)
                    age_hours = age_seconds / 3600.0
                    
                    orphans.append({
                        "name": entry.name,
                        "path": entry.resolve(),
                        "size_bytes": size_bytes,
                        "size_human": FilesystemService.format_bytes_human(size_bytes),
                        "last_modified_ts": last_mtime,
                        "age_hours": round(age_hours, 2)
                    })
                    
        except Exception as e:
            logger.error(f"Error scanning PROJECTS_DIR for orphans: {e}")

        # Sort by age (oldest first)
        orphans.sort(key=lambda x: x["age_hours"], reverse=True)
        return orphans

    @staticmethod
    def cleanup_orphan_projects(threshold_hours: int = 48, dry_run: bool = False) -> Dict[str, Any]:
        """Identifies and safely removes orphaned projects.
        
        Args:
            threshold_hours: Minimum hours of inactivity.
            dry_run: If True, identifies orphans but does not delete them.
            
        Returns:
            Dictionary with results summary.
        """
        logger.info(f"Starting continuous cleanup. Threshold: {threshold_hours}h. Dry run: {dry_run}")
        
        orphans = CleanupService.get_orphan_projects(threshold_hours)
        
        result = {
            "cleaned_projects": [],
            "total_space_saved_bytes": 0,
            "total_space_saved_human": "0B",
            "errors": [],
            "dry_run": dry_run
        }
        
        if not orphans:
            logger.info("No orphan projects found.")
            return result
            
        for orphan in orphans:
            path_obj = orphan["path"]
            name = orphan["name"]
            size = orphan["size_bytes"]
            
            logger.info(f"Identified orphan project: '{name}' ({orphan['size_human']}, inactive for {orphan['age_hours']}h)")
            
            if not dry_run:
                try:
                    # Final safety check before deletion
                    if CleanupService.is_path_protected(path_obj):
                        msg = f"Safety abort: '{name}' is protected right before deletion."
                        logger.error(msg)
                        result["errors"].append(msg)
                        continue
                        
                    CleanupService._safe_rmtree(path_obj)
                    
                    if not path_obj.exists():
                        result["cleaned_projects"].append(name)
                        result["total_space_saved_bytes"] += size
                        logger.info(f"Successfully removed orphan: '{name}'")
                    else:
                        msg = f"Failed to completely remove '{name}'"
                        logger.warning(msg)
                        result["errors"].append(msg)
                except Exception as e:
                    msg = f"Exception while removing '{name}': {e}"
                    logger.error(msg)
                    result["errors"].append(msg)
            else:
                result["cleaned_projects"].append(name)
                result["total_space_saved_bytes"] += size
                
        result["total_space_saved_human"] = FilesystemService.format_bytes_human(result["total_space_saved_bytes"])
        
        logger.info(f"Cleanup finished. Removed {len(result['cleaned_projects'])} projects. Space saved: {result['total_space_saved_human']}.")
        return result
