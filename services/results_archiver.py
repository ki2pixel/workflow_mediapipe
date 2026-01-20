"""
Results Archiver Service
Ensures persistence of analysis artifacts (scenes CSV, audio JSON, tracking JSON)
across workflow executions (e.g., when step 7 cleans/rebuilds project dirs).

Architecture:
- Service-layer only. No routes. Import and use from other services (e.g., VisualizationService).
- Archives structure: {ARCHIVES_DIR}/{project_name}/{video_hash}/
  - {video_stem}_scenes.csv
  - {video_stem}_audio.json
  - {video_stem}_tracking.json
  - metadata.json (source path, created_at)

Key design choices:
- Index by strong content hash of the video file to avoid false positives on same names.
- Preserve original filenames (with video_stem prefix) for readability.
- Provide resilient lookup: prefer exact-hash directory, fallback to any existing artifacts by stem.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timezone

from config.settings import config
import logging

logger = logging.getLogger(__name__)

SCENES_SUFFIX = "_scenes.csv"
AUDIO_SUFFIX = "_audio.json"
TRACKING_SUFFIX = "_tracking.json"
VIDEO_METADATA_NAME = "video_metadata.json"


@dataclass
class ArchivePaths:
    project_dir: Path
    video_hash_dir: Path


class ResultsArchiver:
    """Service that persists and retrieves analysis artifacts for videos."""

    # In-process cache that maps base project names to the timestamped archive dir created
    _PROJECT_ARCHIVE_DIRS: dict[str, Path] = {}

    @staticmethod
    def _format_timestamp(now: Optional[datetime] = None) -> str:
        """Return a safe timestamp string for directory names: YYYY-MM-DD_HH-MM-SS."""
        dt = now or datetime.now(timezone.utc)
        # Use local-like format without timezone symbols for fs safety
        return dt.strftime("%Y-%m-%d_%H-%M-%S")

    @staticmethod
    def _list_matching_project_dirs(base_name: str) -> list[Path]:
        """List archive project directories matching a base project name.

        Matches directories named exactly `base_name` or starting with `base_name + ' '`. Sorted descending by name.
        """
        root = config.ARCHIVES_DIR
        if not root.exists():
            return []
        candidates: list[Path] = []
        prefix = f"{base_name} "
        try:
            for d in root.iterdir():
                if not d.is_dir():
                    continue
                n = d.name
                if n == base_name or n.startswith(prefix):
                    candidates.append(d)
        except Exception:
            return []
        # Sort newest-first by name (timestamp suffix sorts lexicographically correctly)
        candidates.sort(key=lambda p: p.name, reverse=True)
        return candidates

    @classmethod
    def _get_or_create_archive_project_dir(cls, base_name: str) -> Path:
        """Get or create (once per process) the timestamp-suffixed archive project directory.

        Ensures subsequent writes in this process for the same base project go to the same directory.
        """
        if base_name in cls._PROJECT_ARCHIVE_DIRS:
            return cls._PROJECT_ARCHIVE_DIRS[base_name]
        ts = ResultsArchiver._format_timestamp()
        proj_dir = config.ARCHIVES_DIR / f"{base_name} {ts}"
        proj_dir.mkdir(parents=True, exist_ok=True)
        cls._PROJECT_ARCHIVE_DIRS[base_name] = proj_dir
        return proj_dir

    @staticmethod
    def compute_video_hash(video_path: Path, chunk_size: int = 1024 * 1024) -> Optional[str]:
        """Compute SHA256 hash of a video file.
        Args:
            video_path: Absolute path to video file.
            chunk_size: Read chunk size.
        Returns:
            Hex digest string or None on failure.
        """
        try:
            h = hashlib.sha256()
            with open(video_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to compute hash for {video_path}: {e}")
            return None

    @staticmethod
    def archive_project_analysis(project_name: str) -> dict:
        """Scan the project directory for analysis artifacts and persist them to archives.

        For each video found under PROJECTS_DIR/<project_name>, attempts to copy
        any matching *_scenes.csv, *_audio.json, *_tracking.json into the archives
        hashed directory.

        Returns:
            dict summary: {"project_name": str, "processed": int, "copied": int, "details": [...]}
        """
        details = []
        copied_count = 0
        processed = 0
        try:
            base_path = getattr(config, 'PROJECTS_DIR', None) or (config.BASE_PATH_SCRIPTS / "projets_extraits")
            project_path = base_path / project_name
            if not project_path.exists():
                return {"error": f"Project folder not found: {project_path}"}

            # Enumerate candidate video files (stems) and search artifacts alongside
            video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.webm')
            video_files = []
            for ext in video_extensions:
                video_files.extend(project_path.rglob(f"*{ext}"))

            for v in video_files:
                processed += 1
                stem = v.stem
                scenes = next(project_path.rglob(f"{stem}{SCENES_SUFFIX}"), None)
                if scenes is None:
                    # Fallback: plain CSV (e.g., '<stem>.csv')
                    scenes = next(project_path.rglob(f"{stem}.csv"), None)
                audio = next(project_path.rglob(f"{stem}{AUDIO_SUFFIX}"), None)
                tracking = next(project_path.rglob(f"{stem}{TRACKING_SUFFIX}"), None)
                if tracking is None:
                    # Fallback: plain JSON (e.g., '<stem>.json')
                    tracking = next(project_path.rglob(f"{stem}.json"), None)

                archived_dir = ResultsArchiver.archive_analysis_files(
                    project_name, v, scenes_file=scenes, audio_file=audio, tracking_file=tracking
                )
                copied = {
                    "scenes": bool(scenes),
                    "audio": bool(audio),
                    "tracking": bool(tracking),
                    "archived": bool(archived_dir),
                }
                if archived_dir and any([scenes, audio, tracking]):
                    copied_count += 1
                details.append({
                    "video": str(v.relative_to(project_path)),
                    "copied": copied,
                    "archive_dir": str(archived_dir) if archived_dir else None,
                })

            return {
                "project_name": project_name,
                "processed": processed,
                "copied": copied_count,
                "details": details,
            }
        except Exception as e:
            logger.error(f"Error archiving project analysis for {project_name}: {e}")
            return {"error": str(e)}

    @staticmethod
    def save_video_metadata(project_name: str, video_path: Path, metadata: dict) -> Optional[Path]:
        """Persist computed video metadata into the archive folder.
        Writes video_metadata.json alongside metadata.json with a created_at.
        """
        try:
            video_hash = ResultsArchiver.compute_video_hash(video_path)
            if not video_hash:
                return None
            # Write into the unique (timestamped) archive project directory
            ap = ResultsArchiver.get_archive_paths(project_name, video_hash, create=True)
            ap.video_hash_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata,
            }
            out_path = ap.video_hash_dir / VIDEO_METADATA_NAME
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            return out_path
        except Exception as e:
            logger.warning(f"Failed to save video metadata archive: {e}")
            return None

    @staticmethod
    def load_video_metadata(project_name: str, video_path: Path) -> Optional[dict]:
        """Load archived video metadata if present. Returns dict with keys
        {created_at: str, metadata: {...}} or None.
        """
        try:
            video_hash = ResultsArchiver.compute_video_hash(video_path)
            # If hash not computable (video missing), try any matching stem folder
            if video_hash:
                ap = ResultsArchiver.get_archive_paths(project_name, video_hash, create=False)
                p = ap.video_hash_dir / VIDEO_METADATA_NAME
                if p.exists():
                    with open(p, "r", encoding="utf-8") as f:
                        return json.load(f)
            # Fallback by stem across matching suffixed project dirs
            matches = ResultsArchiver._list_matching_project_dirs(project_name)
            if not matches:
                return None
            stem = video_path.stem
            for arch_proj in matches:
                for meta_path in arch_proj.rglob(VIDEO_METADATA_NAME):
                    try:
                        # ensure sibling files match stem
                        sibling = meta_path.parent
                        any_match = any(
                            q.stem.startswith(stem) and (
                                q.name.endswith(SCENES_SUFFIX) or q.name.endswith(AUDIO_SUFFIX) or q.name.endswith(TRACKING_SUFFIX)
                            ) for q in sibling.iterdir()
                        )
                        if any_match:
                            with open(meta_path, "r", encoding="utf-8") as f:
                                return json.load(f)
                    except Exception:
                        continue
        except Exception:
            pass
        return None

    @staticmethod
    def get_archive_paths(project_name: str, video_hash: str, create: bool = False) -> ArchivePaths:
        """Resolve archive paths for a project/video hash.

        - When create=True, use or create the timestamp-suffixed archive dir for this process.
        - When create=False, resolve the most recent matching archive dir (exact or suffixed), fallback to base name.
        """
        if create:
            project_dir = ResultsArchiver._get_or_create_archive_project_dir(project_name)
        else:
            matches = ResultsArchiver._list_matching_project_dirs(project_name)
            project_dir = matches[0] if matches else (config.ARCHIVES_DIR / project_name)
        video_hash_dir = project_dir / video_hash
        return ArchivePaths(project_dir=project_dir, video_hash_dir=video_hash_dir)

    @staticmethod
    def archive_analysis_files(
        project_name: str,
        video_path: Path,
        scenes_file: Optional[Path] = None,
        audio_file: Optional[Path] = None,
        tracking_file: Optional[Path] = None,
    ) -> Optional[Path]:
        """Copy available analysis files into the archive, keyed by video hash.
        Returns the archive directory on success or None if unsupported.
        """
        try:
            video_hash = ResultsArchiver.compute_video_hash(video_path)
            if not video_hash:
                return None
            ap = ResultsArchiver.get_archive_paths(project_name, video_hash, create=True)
            ap.video_hash_dir.mkdir(parents=True, exist_ok=True)
            video_stem = video_path.stem

            def _copy(src: Optional[Path], suffix: str):
                if src and src.exists():
                    dst = ap.video_hash_dir / f"{video_stem}{suffix}"
                    try:
                        shutil.copy2(src, dst)
                        return str(dst)
                    except Exception as e:
                        logger.warning(f"Failed to archive {src} -> {dst}: {e}")
                return None

            copied = {
                "scenes": _copy(scenes_file, SCENES_SUFFIX),
                "audio": _copy(audio_file, AUDIO_SUFFIX),
                "tracking": _copy(tracking_file, TRACKING_SUFFIX),
            }

            # metadata
            meta = {
                "video_path": str(video_path),
                "video_stem": video_stem,
                "video_hash": video_hash,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "copied": copied,
            }
            with open(ap.video_hash_dir / "metadata.json", "w", encoding="utf-8") as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)

            return ap.video_hash_dir
        except Exception as e:
            logger.error(f"Error archiving analysis files: {e}")
            return None

    @staticmethod
    def find_analysis_file(
        project_name: str,
        video_path: Path,
        suffix: str,
    ) -> Optional[Path]:
        """Resolve an analysis file from archives for this video.
        Prefers exact hash dir; falls back to any file matching the stem in project archives.
        """
        try:
            video_hash = ResultsArchiver.compute_video_hash(video_path)
            video_stem = video_path.stem

            # Try exact-hash directory
            if video_hash:
                ap = ResultsArchiver.get_archive_paths(project_name, video_hash)
                candidate = ap.video_hash_dir / f"{video_stem}{suffix}"
                if candidate.exists():
                    return candidate

            # Fallback: search by stem within project archive
            matches = ResultsArchiver._list_matching_project_dirs(project_name)
            for project_arch in matches:
                for p in project_arch.rglob(f"{video_stem}{suffix}"):
                    return p
        except Exception:
            pass
        return None

    @staticmethod
    def project_has_analysis(project_name: str) -> Tuple[bool, bool, bool]:
        """Check if archives contain any analysis for this project.
        Returns tuple (has_scenes, has_audio, has_tracking).
        """
        matches = ResultsArchiver._list_matching_project_dirs(project_name)
        if not matches:
            return (False, False, False)
        has_scenes = False
        has_audio = False
        has_tracking = False
        for base in matches:
            if not has_scenes:
                has_scenes = any(base.rglob(f"*{SCENES_SUFFIX}"))
            if not has_audio:
                has_audio = any(base.rglob(f"*{AUDIO_SUFFIX}"))
            if not has_tracking:
                has_tracking = any(base.rglob(f"*{TRACKING_SUFFIX}"))
            if has_scenes and has_audio and has_tracking:
                break
        return (has_scenes, has_audio, has_tracking)
