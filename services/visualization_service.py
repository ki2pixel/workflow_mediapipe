"""
Visualization Service
Aggregates and processes data from workflow steps for timeline visualization.
Handles scene detection (Step 3), audio analysis (Step 4), and video tracking (Step 5).
"""

import logging
import json
import csv
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from config.settings import config
from services.results_archiver import ResultsArchiver, SCENES_SUFFIX, AUDIO_SUFFIX, TRACKING_SUFFIX

logger = logging.getLogger(__name__)

class VisualizationService:
    """
    Service for aggregating and processing workflow results for visualization.
    Combines data from multiple steps to create unified timeline data.
    """
    
    @staticmethod
    def get_available_projects() -> Dict[str, Any]:
        """
        Scan for completed projects with visualization data.
        
        Returns:
            Dictionary with available projects:
            {
                "projects": [
                    {
                        "name": str,
                        "path": str,
                        "videos": [str],
                        "has_scenes": bool,
                        "has_audio": bool,
                        "has_tracking": bool
                    }
                ],
                "count": int
            }
        """
        try:
            # Use centralized configuration to resolve project root and archives
            base_path = getattr(config, 'PROJECTS_DIR', None) or (config.BASE_PATH_SCRIPTS / "projets_extraits")
            archives_root = getattr(config, 'ARCHIVES_DIR', None) or (config.BASE_PATH_SCRIPTS / "archives")
            projects_index: Dict[str, Dict[str, Any]] = {}

            def _parse_archive_name(name: str) -> Tuple[str, Optional[str]]:
                """Return (base_name, archive_timestamp) if name matches '<base> YYYY-MM-DD_HH-MM-SS'.
                archive_timestamp is in 'YYYY-MM-DD HH:MM:SS' human-readable format.
                """
                try:
                    m = re.match(r"^(.*) (\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})$", name)
                    if not m:
                        return name, None
                    base = m.group(1)
                    date_part = m.group(2)
                    time_part = m.group(3).replace('-', ':')
                    return base, f"{date_part} {time_part}"
                except Exception:
                    return name, None
            
            # Scan current projects directory (may be empty after Step 7)
            if base_path.exists():
                for project_dir in base_path.iterdir():
                    if not project_dir.is_dir():
                        continue
                    base_name, ts = _parse_archive_name(project_dir.name)
                    projects_index[project_dir.name] = {
                        "name": project_dir.name,
                        "path": str(project_dir),
                        "videos": [],
                        "has_scenes": False,
                        "has_audio": False,
                        "has_tracking": False,
                        "video_count": 0,
                        "source": "projects",
                        "display_base": base_name,
                        "archive_timestamp": ts,
                    }

            # Populate details for projects directory
            for name, proj in list(projects_index.items()):
                project_dir = Path(proj["path"])
                # Find videos in project
                videos: List[str] = []
                video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.webm')
                for ext in video_extensions:
                    videos.extend([str(v.relative_to(project_dir)) for v in project_dir.rglob(f'*{ext}')])
                has_scenes = any(project_dir.rglob('*_scenes.csv'))
                has_audio = any(project_dir.rglob('*_audio.json'))
                has_tracking = any(project_dir.rglob('*_tracking.json'))
                arch_s, arch_a, arch_t = ResultsArchiver.project_has_analysis(name)
                proj.update({
                    "videos": videos,
                    "has_scenes": has_scenes or arch_s,
                    "has_audio": has_audio or arch_a,
                    "has_tracking": has_tracking or arch_t,
                    "video_count": len(videos)
                })

            # Also include archived-only projects (no current dir present)
            if archives_root.exists():
                for arch_proj_dir in archives_root.iterdir():
                    if not arch_proj_dir.is_dir():
                        continue
                    name = arch_proj_dir.name
                    base_name, ts = _parse_archive_name(name)
                    if name not in projects_index:
                        # Derive original filenames (with extensions when possible) from archived metadata
                        stems: set[str] = set()
                        videos_map: dict[str, str] = {}
                        # Prefer metadata.json inside each video hash directory (contains original video_path)
                        for meta_path in arch_proj_dir.rglob('metadata.json'):
                            try:
                                with open(meta_path, 'r', encoding='utf-8') as mf:
                                    meta = json.load(mf)
                                stem = str(meta.get('video_stem') or '').strip()
                                video_path_str = meta.get('video_path')
                                if not stem:
                                    # Fallback: infer stem from sibling analysis files
                                    sibling_files = list(meta_path.parent.glob('*'))
                                    for q in sibling_files:
                                        qn = q.name
                                        if qn.endswith(SCENES_SUFFIX):
                                            stem = q.stem.replace('_scenes', '')
                                            break
                                        if qn.endswith(AUDIO_SUFFIX):
                                            stem = q.stem.replace('_audio', '')
                                            break
                                        if qn.endswith(TRACKING_SUFFIX):
                                            stem = q.stem.replace('_tracking', '')
                                            break
                                if stem:
                                    if isinstance(video_path_str, str) and video_path_str:
                                        try:
                                            videos_map[stem] = Path(video_path_str).name
                                        except Exception:
                                            videos_map[stem] = stem
                                    else:
                                        videos_map[stem] = stem
                            except Exception:
                                continue
                        # Also scan artifacts in case some entries miss metadata; fill gaps with stems
                        for p in arch_proj_dir.rglob(f'*{SCENES_SUFFIX}'):
                            stems.add(p.stem.replace('_scenes', ''))
                        for p in arch_proj_dir.rglob(f'*{AUDIO_SUFFIX}'):
                            stems.add(p.stem.replace('_audio', ''))
                        for p in arch_proj_dir.rglob(f'*{TRACKING_SUFFIX}'):
                            stems.add(p.stem.replace('_tracking', ''))
                        for s in stems:
                            videos_map.setdefault(s, s)
                        projects_index[name] = {
                            "name": name,
                            "path": str(base_path / name),  # expected original path
                            # Use best-known filename (with extension) when available
                            "videos": sorted(list(videos_map.values())),
                            "has_scenes": any(arch_proj_dir.rglob('*_scenes.csv')),
                            "has_audio": any(arch_proj_dir.rglob('*_audio.json')),
                            "has_tracking": any(arch_proj_dir.rglob('*_tracking.json')),
                            "video_count": len(videos_map),
                            "source": "archives",
                            "display_base": base_name,
                            "archive_timestamp": ts,
                        }
                    else:
                        # If same name was present from projects/, enrich with timestamp if any
                        proj = projects_index[name]
                        proj.setdefault("display_base", base_name)
                        proj.setdefault("archive_timestamp", ts)

            projects = list(projects_index.values())
            # Sort by name
            projects.sort(key=lambda p: p["name"])
            
            return {
                "projects": projects,
                "count": len(projects),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error scanning projects: {e}")
            return {
                "projects": [],
                "count": 0,
                "error": str(e)
            }
    
    @staticmethod
    def get_project_timeline(project_name: str, video_name: str) -> Dict[str, Any]:
        """
        Get aggregated timeline data for a specific video in a project.
        
        Args:
            project_name: Name of the project directory
            video_name: Name of the video file
            
        Returns:
            Timeline data with scenes, audio, and tracking information
        """
        try:
            # Use centralized configuration to resolve project root
            base_path = getattr(config, 'PROJECTS_DIR', None) or (config.BASE_PATH_SCRIPTS / "projets_extraits")
            project_path = base_path / project_name
            project_exists = project_path.exists()
            
            # video_name may be a relative path or an archive stem when the project no longer exists
            video_path = project_path / video_name
            video_exists = video_path.exists()
            
            # If project/video do not exist (post Step 7), infer stem and continue with archives only
            video_stem = (video_path.stem if video_exists else Path(video_name).stem)
            
            # Load data (project dir first, then archives fallback)
            scenes_data = VisualizationService._load_scenes_data(project_name, project_path, video_path, video_stem)
            audio_data = VisualizationService._load_audio_data(project_name, project_path, video_path, video_stem)
            tracking_data = VisualizationService._load_tracking_data(project_name, project_path, video_path, video_stem)

            # Persist any fresh analysis files found in the project into archives
            try:
                scenes_src = scenes_data.get("source_path") if scenes_data.get("available") else None
                audio_src = audio_data.get("source_path") if audio_data.get("available") else None
                tracking_src = tracking_data.get("source_path") if tracking_data.get("available") else None
                # Only archive from project-origin sources
                def _is_project_src(p: Optional[str]) -> Optional[Path]:
                    if not p:
                        return None
                    pp = Path(p)
                    try:
                        if project_exists:
                            pp.relative_to(project_path)
                        return pp
                    except Exception:
                        return None
                ResultsArchiver.archive_analysis_files(
                    project_name,
                    video_path,
                    scenes_file=_is_project_src(scenes_src),
                    audio_file=_is_project_src(audio_src),
                    tracking_file=_is_project_src(tracking_src),
                )
            except Exception:
                pass
            
            # Get video metadata
            metadata = VisualizationService._get_video_metadata(
                video_path, scenes_data, audio_data, tracking_data
            )

            # Save video metadata to archives when we can compute it from an existing video
            try:
                if video_exists and metadata:
                    ResultsArchiver.save_video_metadata(project_name, video_path, metadata)
            except Exception:
                pass

            # Try to load archived video metadata to extract created_at
            metadata_archive_created_at = None
            try:
                vm = ResultsArchiver.load_video_metadata(project_name, video_path)
                if vm and isinstance(vm, dict):
                    metadata_archive_created_at = vm.get('created_at')
            except Exception:
                pass
            
            return {
                "project_name": project_name,
                "video_name": video_name,
                "metadata": metadata,
                "scenes": scenes_data,
                "audio": audio_data,
                "tracking": tracking_data,
                "archive_probe_source": {
                    "metadata": {
                        "provenance": "project" if video_exists else "archives",
                        "created_at": metadata_archive_created_at
                    },
                    "scenes": {
                        "provenance": scenes_data.get("provenance", "unknown"),
                        "created_at": scenes_data.get("archive_created_at")
                    },
                    "audio": {
                        "provenance": audio_data.get("provenance", "unknown"),
                        "created_at": audio_data.get("archive_created_at")
                    },
                    "tracking": {
                        "provenance": tracking_data.get("provenance", "unknown"),
                        "created_at": tracking_data.get("archive_created_at")
                    }
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error loading timeline for {project_name}/{video_name}: {e}")
            return {"error": str(e)}

    @staticmethod
    def get_project_diagnostics(project_name: str) -> Dict[str, Any]:
        """Return per-video diagnostics for a project: availability and provenance of analysis data.

        Args:
            project_name: Project name

        Returns:
            Dict with list of videos and their data availability/provenance and key metrics.
        """
        try:
            projects = VisualizationService.get_available_projects()
            proj = next((p for p in projects.get("projects", []) if p.get("name") == project_name), None)
            if not proj:
                return {"error": f"Project '{project_name}' not found"}

            results = []
            for video in proj.get("videos", []):
                tl = VisualizationService.get_project_timeline(project_name, video)
                if "error" in tl:
                    results.append({
                        "video_name": video,
                        "error": tl.get("error"),
                    })
                    continue
                md = tl.get("metadata", {})
                sc = tl.get("scenes", {})
                au = tl.get("audio", {})
                tr = tl.get("tracking", {})
                ap = tl.get("archive_probe_source", {})
                results.append({
                    "video_name": video,
                    "availability": {
                        "metadata": bool(md),
                        "scenes": sc.get("available", False),
                        "audio": au.get("available", False),
                        "tracking": tr.get("available", False),
                    },
                    "provenance": {
                        "scenes": sc.get("provenance"),
                        "audio": au.get("provenance"),
                        "tracking": tr.get("provenance"),
                        "metadata": (ap.get("metadata") or {}).get("provenance"),
                    },
                    "metrics": {
                        "fps": md.get("fps"),
                        "total_frames": md.get("total_frames"),
                        "duration_seconds": md.get("duration_seconds"),
                        "scene_count": md.get("scene_count"),
                        "speech_segment_count": md.get("speech_segment_count"),
                        "face_coverage": md.get("face_coverage"),
                    }
                })

            return {
                "project_name": project_name,
                "count": len(results),
                "videos": results,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error(f"Diagnostics error for project {project_name}: {e}")
            return {"error": str(e)}
    
    @staticmethod
    def _load_scenes_data(project_name: str, project_path: Path, video_path: Path, video_stem: str) -> Dict[str, Any]:
        """Load scene detection data from CSV."""
        # Search recursively to support nested outputs
        scenes_file = next(project_path.rglob(f"{video_stem}{SCENES_SUFFIX}"), None)
        # Fallback: some pipelines save scenes as plain '<stem>.csv'
        if scenes_file is None:
            scenes_file = next(project_path.rglob(f"{video_stem}.csv"), None)
        
        provenance = "project"
        archive_created_at = None
        # Fallback to archives
        if scenes_file is None or not scenes_file.exists():
            scenes_file = ResultsArchiver.find_analysis_file(project_name, video_path, SCENES_SUFFIX)
            if scenes_file is None:
                return {"available": False, "scenes": []}
            provenance, archive_created_at = VisualizationService._provenance_info(Path(scenes_file))
        else:
            provenance = "project"
        
        try:
            scenes = []
            with open(scenes_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    scenes.append({
                        "scene_number": int(row.get("Scene Number", 0)),
                        "start_frame": int(row.get("Start Frame", 0)),
                        "end_frame": int(row.get("End Frame", 0)),
                        "start_timecode": row.get("Start Timecode", "00:00:00.000"),
                        "end_timecode": row.get("End Timecode", "00:00:00.000"),
                        "start_time_seconds": VisualizationService._timecode_to_seconds(
                            row.get("Start Timecode", "00:00:00.000")
                        ),
                        "end_time_seconds": VisualizationService._timecode_to_seconds(
                            row.get("End Timecode", "00:00:00.000")
                        )
                    })
            
            return {
                "available": True,
                "count": len(scenes),
                "scenes": scenes,
                "source_path": str(scenes_file),
                "provenance": provenance,
                "archive_created_at": archive_created_at
            }
            
        except Exception as e:
            logger.error(f"Error loading scenes data: {e}")
            return {"available": False, "error": str(e), "scenes": []}
    
    @staticmethod
    def _load_audio_data(project_name: str, project_path: Path, video_path: Path, video_stem: str) -> Dict[str, Any]:
        """Load audio analysis data from JSON."""
        # Search recursively to support nested outputs
        audio_file = next(project_path.rglob(f"{video_stem}{AUDIO_SUFFIX}"), None)
        
        provenance = "project"
        archive_created_at = None
        # Fallback to archives
        if audio_file is None or not audio_file.exists():
            audio_file = ResultsArchiver.find_analysis_file(project_name, video_path, AUDIO_SUFFIX)
            if audio_file is None:
                return {"available": False, "segments": []}
            provenance, archive_created_at = VisualizationService._provenance_info(Path(audio_file))
        else:
            provenance = "project"
        
        try:
            with open(audio_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract speech segments
            segments = []
            fps = data.get("fps", 25.0)
            max_frame_seen = 0
            
            # Group consecutive speech frames
            current_segment = None
            
            for frame_data in data.get("frames_analysis", []):
                frame = frame_data.get("frame", 0)
                audio_info = frame_data.get("audio_info", {})
                is_speech = audio_info.get("is_speech_present", False)
                speakers = audio_info.get("active_speaker_labels", [])
                time_sec = audio_info.get("timecode_sec", (frame - 1) / fps)
                if isinstance(frame, (int, float)):
                    try:
                        max_frame_seen = max(max_frame_seen, int(frame))
                    except Exception:
                        pass
                
                if is_speech:
                    if current_segment is None:
                        current_segment = {
                            "start_frame": frame,
                            "start_time": time_sec,
                            "speakers": set(speakers)
                        }
                    else:
                        current_segment["speakers"].update(speakers)
                else:
                    if current_segment is not None:
                        # End current segment
                        segments.append({
                            "start_frame": current_segment["start_frame"],
                            "end_frame": frame - 1,
                            "start_time": current_segment["start_time"],
                            "end_time": time_sec,
                            "speakers": sorted(list(current_segment["speakers"])),
                            "speaker_count": len(current_segment["speakers"])
                        })
                        current_segment = None
            
            # Close last segment if open
            if current_segment is not None:
                last_frame = data.get("total_frames") or max_frame_seen
                segments.append({
                    "start_frame": current_segment["start_frame"],
                    "end_frame": last_frame,
                    "start_time": current_segment["start_time"],
                    "end_time": last_frame / fps,
                    "speakers": sorted(list(current_segment["speakers"])),
                    "speaker_count": len(current_segment["speakers"])
                })
            
            # Get unique speakers
            all_speakers = set()
            for seg in segments:
                all_speakers.update(seg["speakers"])
            
            total_frames = data.get("total_frames") or max_frame_seen
            if not total_frames and segments:
                try:
                    total_frames = max(int(s.get("end_frame", 0)) for s in segments)
                except Exception:
                    total_frames = 0

            return {
                "available": True,
                "fps": fps,
                "total_frames": int(total_frames or 0),
                "segments": segments,
                "segment_count": len(segments),
                "unique_speakers": sorted(list(all_speakers)),
                "speaker_count": len(all_speakers),
                "source_path": str(audio_file),
                "provenance": provenance,
                "archive_created_at": archive_created_at
            }
            
        except Exception as e:
            logger.error(f"Error loading audio data: {e}")
            return {"available": False, "error": str(e), "segments": []}
    
    @staticmethod
    def _load_tracking_data(project_name: str, project_path: Path, video_path: Path, video_stem: str) -> Dict[str, Any]:
        """Load video tracking data from JSON."""
        # Search recursively to support nested outputs
        tracking_file = next(project_path.rglob(f"{video_stem}{TRACKING_SUFFIX}"), None)
        # Fallback: some pipelines save tracking as plain '<stem>.json'
        if tracking_file is None:
            tracking_file = next(project_path.rglob(f"{video_stem}.json"), None)
        
        provenance = "project"
        archive_created_at = None
        # Fallback to archives
        if tracking_file is None or not tracking_file.exists():
            tracking_file = ResultsArchiver.find_analysis_file(project_name, video_path, TRACKING_SUFFIX)
            if tracking_file is None:
                return {"available": False, "summary": {}}
            provenance, archive_created_at = VisualizationService._provenance_info(Path(tracking_file))
        else:
            provenance = "project"
        
        try:
            with open(tracking_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Calculate summary statistics
            total_frames = data.get("total_frames", 0)
            fps = data.get("fps", 25.0)
            frames_with_faces = 0
            frames_with_speaking = 0
            max_faces = 0
            max_frame_seen = 0
            
            for frame_data in data.get("frames_analysis", []):
                frame = frame_data.get("frame")
                if isinstance(frame, (int, float)):
                    try:
                        max_frame_seen = max(max_frame_seen, int(frame))
                    except Exception:
                        pass

                # Support two schemas:
                # 1) faces_data: [{ is_speaking: bool, ... }]
                # 2) tracked_objects: [{ label: "face", active_speakers: [...], ... }]
                faces_list = frame_data.get("faces_data")
                if faces_list is None:
                    tracked = frame_data.get("tracked_objects", []) or []
                    faces_list = [o for o in tracked if str(o.get("label", "")).lower() == "face"]

                face_count = len(faces_list)
                if face_count > 0:
                    frames_with_faces += 1
                    max_faces = max(max_faces, face_count)

                    # Speaking detection across schemas
                    speaking = any(
                        (
                            # legacy schema
                            (isinstance(f, dict) and f.get("is_speaking", False)) or
                            # tracked_objects schema: any active_speakers present
                            (isinstance(f, dict) and bool(f.get("active_speakers")))
                        )
                        for f in faces_list
                    )
                    if speaking:
                        frames_with_speaking += 1
            
            if (not total_frames or total_frames == 0) and max_frame_seen:
                total_frames = max_frame_seen
            coverage_percent = (frames_with_faces / total_frames * 100) if total_frames > 0 else 0
            
            return {
                "available": True,
                "fps": fps,
                "total_frames": total_frames,
                "summary": {
                    "frames_with_faces": frames_with_faces,
                    "frames_with_speaking": frames_with_speaking,
                    "max_faces_detected": max_faces,
                    "face_coverage_percent": round(coverage_percent, 2)
                },
                "source_path": str(tracking_file),
                "provenance": provenance,
                "archive_created_at": archive_created_at
            }
            
        except Exception as e:
            logger.error(f"Error loading tracking data: {e}")
            return {"available": False, "error": str(e), "summary": {}}

    @staticmethod
    def _provenance_info(file_path: Path) -> (str, Optional[str]):
        """Return (provenance, created_at) for a given analysis file.
        If file is under ARCHIVES_DIR, provenance='archives' and created_at read from sibling metadata.json.
        Otherwise provenance='project', created_at=None.
        """
        try:
            arch_root = config.ARCHIVES_DIR.resolve()
            fp = file_path.resolve()
            try:
                fp.relative_to(arch_root)
                # archived
                meta_path = fp.parent / 'metadata.json'
                if meta_path.exists():
                    with open(meta_path, 'r', encoding='utf-8') as mf:
                        meta = json.load(mf)
                        return 'archives', meta.get('created_at')
                return 'archives', None
            except Exception:
                return 'project', None
        except Exception as e:
            logger.error(f"Error getting provenance info: {e}")
            return 'unknown', None
    
    @staticmethod
    def _get_video_metadata(
        video_path: Path, 
        scenes_data: Dict, 
        audio_data: Dict, 
        tracking_data: Dict
    ) -> Dict[str, Any]:
        """Extract video metadata and combine with analysis data."""
        try:
            # Prefer FPS/frames from analysis data when present
            fps = audio_data.get("fps") or tracking_data.get("fps")
            total_frames = audio_data.get("total_frames") or tracking_data.get("total_frames")

            duration_seconds = 0.0

            # Derive duration from scenes if available
            if scenes_data.get("available") and scenes_data.get("scenes"):
                try:
                    duration_seconds = max(s.get("end_time_seconds", 0) for s in scenes_data["scenes"]) or 0.0
                except Exception:
                    pass

            # If duration or fps/frames still missing, probe the video file directly (if it exists)
            if (not fps or not total_frames or duration_seconds == 0.0) and video_path.exists():
                probed = VisualizationService._probe_video_file(video_path)
                if probed:
                    probed_fps = probed.get("fps")
                    probed_duration = probed.get("duration")
                    if not fps and probed_fps:
                        fps = probed_fps
                    if duration_seconds == 0.0 and probed_duration:
                        duration_seconds = probed_duration
                    if not total_frames and fps and duration_seconds:
                        total_frames = int(round(fps * duration_seconds))

            # Final fallbacks
            if not fps:
                fps = 25.0
            if not total_frames and duration_seconds and fps:
                total_frames = int(round(fps * duration_seconds))
            if not duration_seconds and total_frames and fps:
                duration_seconds = total_frames / fps
            
            return {
                "filename": video_path.name if video_path.name else "(archive)",
                "fps": fps,
                "total_frames": total_frames,
                "duration_seconds": round(duration_seconds, 2),
                "duration_formatted": VisualizationService._seconds_to_timecode(duration_seconds),
                "has_scenes": scenes_data.get("available", False),
                "has_audio": audio_data.get("available", False),
                "has_tracking": tracking_data.get("available", False),
                "scene_count": scenes_data.get("count", 0),
                "speech_segment_count": audio_data.get("segment_count", 0),
                "face_coverage": tracking_data.get("summary", {}).get("face_coverage_percent", 0)
            }
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {}

    @staticmethod
    def _probe_video_file(video_path: Path) -> Optional[Dict[str, float]]:
        """Probe a video file using ffprobe (fallback to OpenCV) to get fps and duration.
        Returns a dict like {"fps": float|None, "duration": float|None} or None on failure.
        """
        try:
            # Try ffprobe first
            cmd = [
                'ffprobe', '-v', 'error',
                '-select_streams', 'v:0',
                '-show_entries', 'stream=avg_frame_rate,duration',
                '-of', 'json', str(video_path)
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
            if result.returncode == 0 and result.stdout:
                data = json.loads(result.stdout)
                streams = data.get('streams') or []
                if streams:
                    stream = streams[0]
                    fps = None
                    afr = stream.get('avg_frame_rate')
                    if afr and afr != '0/0':
                        try:
                            num, den = afr.split('/')
                            num, den = float(num), float(den)
                            if den != 0:
                                fps = num / den
                        except Exception:
                            pass
                    duration = None
                    try:
                        duration_val = stream.get('duration')
                        if duration_val is not None:
                            duration = float(duration_val)
                    except Exception:
                        pass
                    return {"fps": fps, "duration": duration}
        except Exception:
            pass
        # Fallback to OpenCV if available
        try:
            import cv2  # type: ignore
            cap = cv2.VideoCapture(str(video_path))
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS) or None
                frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or None
                cap.release()
                duration = None
                if fps and frame_count:
                    duration = float(frame_count) / float(fps)
                return {"fps": float(fps) if fps else None, "duration": duration}
        except Exception:
            pass
        return None
    
    @staticmethod
    def _timecode_to_seconds(timecode: str) -> float:
        """Convert timecode (HH:MM:SS.mmm) to seconds."""
        try:
            parts = timecode.split(':')
            if len(parts) != 3:
                return 0.0
            
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            
            return hours * 3600 + minutes * 60 + seconds
            
        except Exception:
            return 0.0
    
    @staticmethod
    def _seconds_to_timecode(seconds: float) -> str:
        """Convert seconds to timecode (HH:MM:SS.mmm)."""
        try:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
            
        except Exception:
            return "00:00:00.000"
