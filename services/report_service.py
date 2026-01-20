"""
Report Service
Generates visual reports (HTML) with statistics and infographics for analyzed videos.
Uses Jinja2 templates and aggregates data from VisualizationService.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import hashlib
import unicodedata
import re
from datetime import datetime, timezone
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.settings import config
from services.visualization_service import VisualizationService

logger = logging.getLogger(__name__)


class ReportService:
    """Service for generating visual analysis reports."""
    
    _EXCLUDED_ARCHIVE_FILENAMES = {
        "m6+.mov".lower(),
        "BOUCLE BUG 9-16.mov".lower(),
    }
    
    @staticmethod
    def analyze_monthly_report_html(html: str) -> Dict[str, Any]:
        """Analyze an uploaded monthly report HTML and compute counts from the
        'Répartition des Durées par Projet' section only.

        Args:
            html: The HTML content of a monthly report.

        Returns:
            Dict with computed counts strictly from listed filenames in the
            duration section (what is visually present in the report):
            {
              "total_listed": int,            # total entries across all spans.video-names
              "by_extension": {".mp4": int, "other": int, "noext": int},
              "projects": int|null,           # number of distinct project blocks found
              "build_id": str|null,           # parsed from header if present
              "month": str|null               # parsed from title if present
            }
        """
        try:
            text = html or ""
            section_text = text
            try:
                h2m = re.search(r"<h2>\s*R[ée]partition des Dur[ée]es par Projet\s*</h2>", text, flags=re.IGNORECASE)
                if h2m:
                    section_text = text[h2m.end():]
            except Exception:
                section_text = text
            month_match = re.search(r"Rapport\s+Mensuel\s+Archives\s+[-—]\s+([0-9]{4}-[0-9]{2})", text)
            build_match = re.search(r"Build\s+([a-f0-9]{6,16})", text, re.IGNORECASE)
            month_val = month_match.group(1) if month_match else None
            build_val = build_match.group(1) if build_match else None

            blocks = re.findall(r"<div\s+class=\"video-names\"[^>]*>(.*?)</div>", section_text, flags=re.DOTALL | re.IGNORECASE)

            total_listed = 0
            mp4 = 0
            other = 0
            noext = 0

            def _classify(name: str):
                nonlocal total_listed, mp4, other, noext
                clean = re.sub(r"<[^>]+>", "", name)
                clean = unicodedata.normalize("NFKC", clean).strip()
                if not clean:
                    return
                total_listed += 1
                l = clean.lower()
                if l.endswith('.mp4'):
                    mp4 += 1
                else:
                    if '.' in l:
                        other += 1
                    else:
                        noext += 1

            for raw in blocks:
                items = re.findall(r"<div\s+class=\"video-name\"[^>]*>(.*?)</div>", raw, flags=re.DOTALL | re.IGNORECASE)
                if items:
                    for it in items:
                        _classify(it)
                else:
                    parts = re.split(r"<br\s*/?>", raw, flags=re.IGNORECASE)
                    buffer = ""
                    for part in parts:
                        txt = re.sub(r"<[^>]+>", "", part)
                        txt = unicodedata.normalize("NFKC", txt).strip()
                        if not txt:
                            continue
                        if not buffer:
                            if txt.lower().endswith('.mp4') or re.search(r"\.[a-z0-9]{2,4}$", txt.lower()):
                                _classify(txt)
                            else:
                                buffer = txt
                        else:
                            combined = (buffer + " " + txt).strip()
                            if txt.lower().endswith('.mp4') or combined.lower().endswith('.mp4') or re.search(r"\.[a-z0-9]{2,4}$", txt.lower()) or re.search(r"\.[a-z0-9]{2,4}$", combined.lower()):
                                _classify(combined)
                                buffer = ""
                            else:
                                buffer = combined

            if total_listed == 0:
                spans = re.findall(r"<span\s+class=\"video-names\">(.*?)</span>", section_text, flags=re.DOTALL | re.IGNORECASE)
                for raw in spans:
                    parts = re.split(r"<br\s*/?>", raw, flags=re.IGNORECASE)
                    buffer = ""
                    for part in parts:
                        txt = re.sub(r"<[^>]+>", "", part)
                        txt = unicodedata.normalize("NFKC", txt).strip()
                        if not txt:
                            continue
                        if not buffer:
                            if txt.lower().endswith('.mp4') or re.search(r"\.[a-z0-9]{2,4}$", txt.lower()):
                                _classify(txt)
                            else:
                                buffer = txt
                        else:
                            combined = (buffer + " " + txt).strip()
                            if txt.lower().endswith('.mp4') or combined.lower().endswith('.mp4') or re.search(r"\.[a-z0-9]{2,4}$", txt.lower()) or re.search(r"\.[a-z0-9]{2,4}$", combined.lower()):
                                _classify(combined)
                                buffer = ""
                            else:
                                buffer = combined

            if total_listed == 0:
                items = re.findall(r"<div\s+class=\"video-name\"[^>]*>(.*?)</div>", section_text, flags=re.DOTALL | re.IGNORECASE)
                for it in items:
                    _classify(it)

            proj_blocks = re.findall(r"<strong>\s*([^<]+?)\s*</strong>\s*:", section_text)
            
            counters = re.findall(r"(?:moins\s+de\s+2\s+minutes\s*:\s*(\d+))|(?:entre\s+2\s+et\s*5\s+minutes\s*:\s*(\d+))|(?:plus\s+de\s*5\s+minutes\s*:\s*(\d+))", text, flags=re.IGNORECASE)
            total_from_counters = 0
            for a, b, c in counters:
                for v in (a, b, c):
                    if v:
                        try:
                            total_from_counters += int(v)
                        except ValueError:
                            pass
            return {
                "total_listed": total_listed,
                "by_extension": {".mp4": mp4, "other": other, "noext": noext},
                "lines_mp4": mp4,
                "list_items_total": total_listed,
                "projects": len(proj_blocks) if proj_blocks else 0,
                "build_id": build_val,
                "month": month_val,
                "total_from_counters": total_from_counters,
            }
        except Exception as e:
            logger.error("analyze_monthly_report_html error", exc_info=True)
            return {"error": str(e)}

    @staticmethod
    def _get_jinja_env() -> Environment:
        """Get Jinja2 environment for report templates."""
        template_dir = config.BASE_PATH_SCRIPTS / "templates" / "reports"
        template_dir.mkdir(parents=True, exist_ok=True)
        
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        env.filters['format_duration'] = ReportService._format_duration
        env.filters['format_percentage'] = ReportService._format_percentage
        
        return env
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in seconds to HH:MM:SS."""
        if not seconds:
            return "00:00:00"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def _format_percentage(value: float, decimals: int = 1) -> str:
        """Format percentage value."""
        return f"{value:.{decimals}f}%"
    
    @staticmethod
    def generate_report(
        project_name: str,
        video_name: str,
        format: str = "html"
    ) -> Dict[str, Any]:
        """
        Generate a visual report for a video.
        
        Args:
            project_name: Name of the project
            video_name: Name of the video file
            format: Output format ('html' or 'pdf')
            
        Returns:
            Dictionary with report data and rendered content
        """
        try:
            timeline_data = VisualizationService.get_project_timeline(project_name, video_name)
            
            if "error" in timeline_data:
                return {"error": timeline_data["error"]}
            
            stats = ReportService._compute_statistics(timeline_data)
            
            context = {
                "project_name": project_name,
                "video_name": video_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "metadata": timeline_data.get("metadata", {}),
                "scenes": timeline_data.get("scenes", {}),
                "audio": timeline_data.get("audio", {}),
                "tracking": timeline_data.get("tracking", {}),
                "archive_probe_source": timeline_data.get("archive_probe_source", {}),
                "statistics": stats,
            }
            
            env = ReportService._get_jinja_env()
            
            try:
                template = env.get_template("analysis_report.html")
            except Exception as e:
                logger.warning(f"Template not found, using fallback: {e}")
                ReportService._create_default_template()
                template = env.get_template("analysis_report.html")
            
            html_content = template.render(**context)
            
            result = {
                "project_name": project_name,
                "video_name": video_name,
                "format": "html",
                "html": html_content,
                "statistics": stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating report: {e}", exc_info=True)
            return {"error": str(e)}

    @staticmethod
    def generate_monthly_archive_report(month: str, format: str = "html") -> Dict[str, Any]:
        """Generate a consolidated report for all archived projects in a given month.

        Args:
            month: Target month in 'YYYY-MM' format.
            format: Output format (currently 'html').

        Returns:
            Dict with rendered HTML and aggregated statistics, or an error.
        """
        try:
            month = (month or "").strip()
            if (not month) or (len(month) != 7) or (month[4] != '-'):
                return {"error": f"Invalid month format: '{month}'. Expected YYYY-MM."}

            avail = VisualizationService.get_available_projects()
            if avail.get("error"):
                return {"error": avail["error"]}

            projects = avail.get("projects", [])
            selected = [
                p for p in projects
                if p.get("source") == "archives" and isinstance(p.get("archive_timestamp"), str)
                and p["archive_timestamp"].startswith(month)
            ]

            if not selected:
                return {"error": f"No archived projects found for month '{month}'"}

            monthly_projects: List[Dict[str, Any]] = []
            totals = {
                "projects": 0,
                "videos": 0,
                "video": {"duration_seconds": 0.0, "total_frames": 0, "fps_weighted_sum": 0.0, "fps_weight": 0.0},
                "scenes": {"total_count": 0},
                "audio": {"total_segments": 0, "unique_speakers": set(), "total_speech_duration": 0.0},
                "tracking": {
                    "frames_with_faces": 0,
                    "frames_with_speaking": 0,
                    "max_faces_detected": 0,
                    "face_coverage_percent_sum": 0.0,
                    "face_coverage_entries": 0
                }
            }

            for proj in selected:
                pname = proj.get("name")
                videos_all = proj.get("videos", [])
                filtered_videos = [
                    v for v in videos_all
                    if isinstance(v, str) and v.lower() not in ReportService._EXCLUDED_ARCHIVE_FILENAMES
                ]
                totals["projects"] += 1
                per_video: List[Dict[str, Any]] = []
                duration_counts = {
                    "lt_2m": 0,            # < 120s
                    "between_2_5m": 0,     # 120s .. 300s (inclusive)
                    "gt_5m": 0,            # > 300s
                }
                duration_names = {
                    "lt_2m": [],
                    "between_2_5m": [],
                    "gt_5m": [],
                }
                for video in filtered_videos:
                    tl = VisualizationService.get_project_timeline(pname, video)
                    if "error" in tl:
                        per_video.append({"video_name": video, "error": tl["error"]})
                        continue
                    stats = ReportService._compute_statistics(tl)
                    per_video.append({
                        "video_name": video,
                        "metadata": tl.get("metadata", {}),
                        "statistics": stats,
                        "archive_probe_source": tl.get("archive_probe_source", {})
                    })

                    md = stats.get("video", {})
                    totals["video"]["duration_seconds"] += float(md.get("duration_seconds", 0) or 0)
                    totals["video"]["total_frames"] += int(md.get("total_frames", 0) or 0)
                    fps = float(md.get("fps", 0) or 0)
                    if fps > 0 and md.get("duration_seconds", 0):
                        w = float(md.get("duration_seconds", 0) or 0)
                        totals["video"]["fps_weighted_sum"] += fps * w
                        totals["video"]["fps_weight"] += w

                    sc = stats.get("scenes", {})
                    totals["scenes"]["total_count"] += int(sc.get("total_count", 0) or 0)

                    au = stats.get("audio", {})
                    totals["audio"]["total_segments"] += int(au.get("total_segments", 0) or 0)
                    totals["audio"]["total_speech_duration"] += float(au.get("total_speech_duration", 0) or 0)
                    audio_raw = tl.get("audio", {})
                    for sp in audio_raw.get("unique_speakers", []):
                        totals["audio"]["unique_speakers"].add(sp)

                    tr = stats.get("tracking", {})
                    totals["tracking"]["frames_with_faces"] += int(tr.get("frames_with_faces", 0) or 0)
                    totals["tracking"]["frames_with_speaking"] += int(tr.get("frames_with_speaking", 0) or 0)
                    totals["tracking"]["max_faces_detected"] = max(
                        totals["tracking"]["max_faces_detected"], int(tr.get("max_faces_detected", 0) or 0)
                    )
                    if tr.get("face_coverage_percent") is not None:
                        totals["tracking"]["face_coverage_percent_sum"] += float(tr.get("face_coverage_percent", 0) or 0)
                        totals["tracking"]["face_coverage_entries"] += 1

                    try:
                        dur = float(md.get("duration_seconds", 0) or 0)
                    except Exception:
                        dur = 0.0
                    if dur < 120.0:
                        duration_counts["lt_2m"] += 1
                        duration_names["lt_2m"].append(video)
                    elif dur <= 300.0:
                        duration_counts["between_2_5m"] += 1
                        duration_names["between_2_5m"].append(video)
                    else:
                        duration_counts["gt_5m"] += 1
                        duration_names["gt_5m"].append(video)

                def _norm_for_merge(s: str) -> str:
                    if not isinstance(s, str):
                        return ""
                    x = unicodedata.normalize("NFKC", s)
                    x = re.sub(r"\s+", " ", x).strip().lower()
                    return x

                def _merge_split_names(names: List[str]) -> List[str]:
                    out: List[str] = []
                    i = 0
                    while i < len(names):
                        cur_raw = names[i]
                        cur = _norm_for_merge(cur_raw)
                        if i + 1 < len(names):
                            nxt_raw = names[i + 1]
                            nxt = _norm_for_merge(nxt_raw)
                            if not cur.endswith('.mp4') and nxt.endswith('.mp4') and nxt.startswith(cur):
                                out.append(nxt_raw.strip())
                                i += 2
                                continue
                        out.append(cur_raw.strip())
                        i += 1
                    seen = set()
                    dedup: List[str] = []
                    for item in out:
                        key = _norm_for_merge(item)
                        if key in seen:
                            continue
                        seen.add(key)
                        dedup.append(item)
                    return dedup

                for k in ("lt_2m", "between_2_5m", "gt_5m"):
                    duration_names[k] = _merge_split_names(duration_names.get(k, []) or [])

                duration_counts["lt_2m"] = len(duration_names.get("lt_2m", []) or [])
                duration_counts["between_2_5m"] = len(duration_names.get("between_2_5m", []) or [])
                duration_counts["gt_5m"] = len(duration_names.get("gt_5m", []) or [])

                bucket_sum = (
                    int(duration_counts["lt_2m"]) +
                    int(duration_counts["between_2_5m"]) +
                    int(duration_counts["gt_5m"])
                )
                totals["videos"] += bucket_sum

                monthly_projects.append({
                    "name": pname,
                    "display_base": proj.get("display_base", pname),
                    "archive_timestamp": proj.get("archive_timestamp"),
                    "videos": per_video,
                    "video_count": bucket_sum,
                    "duration_counts": duration_counts,
                    "duration_names": duration_names,
                })

            consolidated = {
                "projects": totals["projects"],
                "videos": totals["videos"],
                "video": {
                    "duration_seconds": totals["video"]["duration_seconds"],
                    "total_frames": totals["video"]["total_frames"],
                    "fps": (
                        totals["video"]["fps_weighted_sum"] / totals["video"]["fps_weight"]
                        if totals["video"]["fps_weight"] > 0 else 0
                    ),
                },
                "scenes": {"total_count": totals["scenes"]["total_count"]},
                "audio": {
                    "total_segments": totals["audio"]["total_segments"],
                    "unique_speakers": len(totals["audio"]["unique_speakers"]),
                    "total_speech_duration": totals["audio"]["total_speech_duration"],
                    "speech_coverage_percent": (
                        (totals["audio"]["total_speech_duration"] / totals["video"]["duration_seconds"]) * 100.0
                        if totals["video"]["duration_seconds"] > 0 else 0
                    ),
                },
                "tracking": {
                    "frames_with_faces": totals["tracking"]["frames_with_faces"],
                    "frames_with_speaking": totals["tracking"]["frames_with_speaking"],
                    "max_faces_detected": totals["tracking"]["max_faces_detected"],
                    "face_coverage_percent": (
                        totals["tracking"]["face_coverage_percent_sum"] / totals["tracking"]["face_coverage_entries"]
                        if totals["tracking"]["face_coverage_entries"] > 0 else 0
                    ),
                }
            }

            def _norm_filename(name: str) -> str:
                if not isinstance(name, str):
                    return ""
                s = unicodedata.normalize("NFKC", name)
                s = s.strip().lower()
                s = re.sub(r"\s+", " ", s)
                return s

            total_listed = 0
            mp4_listed = 0
            mp4_distinct: set[str] = set()
            mp4_distinct_stems: set[str] = set()
            for p in monthly_projects:
                dc = p.get("duration_counts", {}) or {}
                total_listed += int(dc.get("lt_2m", 0)) + int(dc.get("between_2_5m", 0)) + int(dc.get("gt_5m", 0))
                dn = p.get("duration_names", {}) or {}
                for key in ("lt_2m", "between_2_5m", "gt_5m"):
                    for raw in dn.get(key, []) or []:
                        nn = _norm_filename(raw)
                        if nn.endswith(".mp4"):
                            mp4_listed += 1
                            mp4_distinct.add(nn)
                            stem = nn[:-4].strip()
                            mp4_distinct_stems.add(stem)

            section_summary = {
                "total_listed": total_listed,
                "mp4_listed": mp4_listed,
                "mp4_distinct": len(mp4_distinct),
                "mp4_distinct_stems": len(mp4_distinct_stems),
            }

            generated_at = datetime.now(timezone.utc).isoformat()
            build_id_source = f"{month}|{generated_at}|{totals['projects']}|{totals['videos']}|{len(monthly_projects)}"
            build_id = hashlib.sha256(build_id_source.encode("utf-8")).hexdigest()[:12]

            context = {
                "month": month,
                "generated_at": generated_at,
                "projects": monthly_projects,
                "consolidated": consolidated,
                "build_id": build_id,
                "section_summary": section_summary,
            }

            env = ReportService._get_jinja_env()
            try:
                template = env.get_template("monthly_archive_report.html")
            except Exception:
                ReportService._create_default_monthly_template()
                template = env.get_template("monthly_archive_report.html")

            html_content = template.render(**context)
            return {
                "format": "html",
                "html": html_content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "month": month,
                "project_count": consolidated["projects"],
                "video_count": consolidated["videos"],
            }

        except Exception as e:
            logger.error(f"Error generating monthly archive report: {e}", exc_info=True)
            return {"error": str(e)}

    @staticmethod
    def _create_default_monthly_template() -> None:
        """Create a minimal monthly report template if not present."""
        try:
            template_dir = config.BASE_PATH_SCRIPTS / "templates" / "reports"
            template_dir.mkdir(parents=True, exist_ok=True)
            target = template_dir / "monthly_archive_report.html"
            if not target.exists():
                target.write_text(
                    """<!doctype html>
<html lang=\"fr\">
<head>
  <meta charset=\"utf-8\" />
  <title>Rapport Mensuel Archives - {{ month }}</title>
  <style>
    body { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; padding: 16px; color: #1a1a1a; }
    h1 { margin: 0 0 12px; font-size: 20px; }
    .meta { color: #666; font-size: 12px; margin-bottom: 16px; }
    .summary { background: #f7f7f7; padding: 12px; border-radius: 8px; margin-bottom: 16px; }
    table { width: 100%; border-collapse: collapse; margin-top: 8px; }
    th, td { border: 1px solid #ddd; padding: 8px; font-size: 13px; }
    th { background: #fafafa; text-align: left; }
    .section { margin-top: 20px; }
    ul { margin: 6px 0 12px 18px; }
    li { margin: 2px 0; }
  </style>
  </head>
<body>
  <h1>Rapport Mensuel Archives — {{ month }}</h1>
  <div class=\"meta\">Généré le {{ generated_at }}</div>
  <div class=\"summary\">
    <div><strong>Projets:</strong> {{ consolidated.projects }}</div>
    <div><strong>Vidéos:</strong> {{ consolidated.videos }}</div>
    <div><strong>Durée totale:</strong> {{ consolidated.video.duration_seconds|format_duration }}</div>
    <div><strong>FPS moyen (pondéré):</strong> {{ consolidated.video.fps|format_percentage(1) }}</div>
  </div>
  <h2>Détails par projet</h2>
  <table>
    <thead>
      <tr><th>Projet</th><th>Horodatage</th><th>Vidéos</th><th>Scènes</th><th>Parole (s)</th><th>Faces (frames)</th></tr>
    </thead>
    <tbody>
      {% for p in projects %}
      <tr>
        <td>{{ p.display_base }}</td>
        <td>{{ p.archive_timestamp or '-' }}</td>
        <td style=\"text-align:right\">{{ p.video_count }}</td>
        <td style=\"text-align:right\">{{ p.videos | sum(attribute='statistics.scenes.total_count') }}</td>
        <td style=\"text-align:right\">{{ p.videos | sum(attribute='statistics.audio.total_speech_duration') | round(1) }}</td>
        <td style=\"text-align:right\">{{ p.videos | sum(attribute='statistics.tracking.frames_with_faces') }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <div class=\"section\">
    <h2>Répartition des Durées par Projet</h2>
    {% for p in projects %}
      <div>
        <strong>{{ p.display_base }}</strong> :
        <ul>
          <li>moins de 2 minutes : {{ p.duration_counts.lt_2m }}</li>
          <li>entre 2 et 5 minutes : {{ p.duration_counts.between_2_5m }}</li>
          <li>plus de 5 minutes : {{ p.duration_counts.gt_5m }}</li>
        </ul>
      </div>
    {% endfor %}
  </div>
</body>
</html>
""",
                    encoding="utf-8",
                )
        except Exception:
            pass

    @staticmethod
    def generate_project_report(
        project_name: str,
        format: str = "html"
    ) -> Dict[str, Any]:
        """Generate a consolidated report for all videos in a project.

        Args:
            project_name: Name of the project
            format: Output format ('html' or 'pdf')

        Returns:
            Dictionary with consolidated report data and rendered content
        """
        try:
            projects_info = VisualizationService.get_available_projects()
            if projects_info.get("error"):
                return {"error": projects_info["error"]}

            project_entry = None
            for p in projects_info.get("projects", []):
                if p.get("name") == project_name:
                    project_entry = p
                    break
            if not project_entry:
                return {"error": f"Project '{project_name}' not found"}

            videos = project_entry.get("videos", [])
            if not videos:
                return {"error": f"No videos found for project '{project_name}'"}

            per_video: List[Dict[str, Any]] = []
            totals = {
                "video": {"duration_seconds": 0.0, "total_frames": 0, "fps_weighted_sum": 0.0, "fps_weight": 0.0},
                "scenes": {"total_count": 0},
                "audio": {"total_segments": 0, "unique_speakers": set(), "total_speech_duration": 0.0},
                "tracking": {
                    "frames_with_faces": 0,
                    "frames_with_speaking": 0,
                    "max_faces_detected": 0,
                    "face_coverage_percent_sum": 0.0,
                    "face_coverage_entries": 0
                }
            }

            for video in videos:
                timeline = VisualizationService.get_project_timeline(project_name, video)
                if "error" in timeline:
                    per_video.append({"video_name": video, "error": timeline["error"]})
                    continue

                stats = ReportService._compute_statistics(timeline)
                per_video.append({
                    "video_name": video,
                    "metadata": timeline.get("metadata", {}),
                    "statistics": stats,
                    "archive_probe_source": timeline.get("archive_probe_source", {})
                })

                md = stats.get("video", {})
                totals["video"]["duration_seconds"] += float(md.get("duration_seconds", 0) or 0)
                totals["video"]["total_frames"] += int(md.get("total_frames", 0) or 0)
                fps = float(md.get("fps", 0) or 0)
                if fps > 0 and md.get("duration_seconds", 0):
                    w = float(md.get("duration_seconds", 0) or 0)
                    totals["video"]["fps_weighted_sum"] += fps * w
                    totals["video"]["fps_weight"] += w

                sc = stats.get("scenes", {})
                totals["scenes"]["total_count"] += int(sc.get("total_count", 0) or 0)

                au = stats.get("audio", {})
                totals["audio"]["total_segments"] += int(au.get("total_segments", 0) or 0)
                totals["audio"]["total_speech_duration"] += float(au.get("total_speech_duration", 0) or 0)
                audio_raw = timeline.get("audio", {})
                for sp in audio_raw.get("unique_speakers", []):
                    totals["audio"]["unique_speakers"].add(sp)

                tr = stats.get("tracking", {})
                totals["tracking"]["frames_with_faces"] += int(tr.get("frames_with_faces", 0) or 0)
                totals["tracking"]["frames_with_speaking"] += int(tr.get("frames_with_speaking", 0) or 0)
                totals["tracking"]["max_faces_detected"] = max(
                    totals["tracking"]["max_faces_detected"], int(tr.get("max_faces_detected", 0) or 0)
                )
                if tr.get("face_coverage_percent") is not None:
                    totals["tracking"]["face_coverage_percent_sum"] += float(tr.get("face_coverage_percent", 0) or 0)
                    totals["tracking"]["face_coverage_entries"] += 1

            consolidated = {
                "video": {
                    "duration_seconds": totals["video"]["duration_seconds"],
                    "total_frames": totals["video"]["total_frames"],
                    "fps": (
                        totals["video"]["fps_weighted_sum"] / totals["video"]["fps_weight"]
                        if totals["video"]["fps_weight"] > 0 else 0
                    ),
                },
                "scenes": {
                    "total_count": totals["scenes"]["total_count"],
                },
                "audio": {
                    "total_segments": totals["audio"]["total_segments"],
                    "unique_speakers": len(totals["audio"]["unique_speakers"]),
                    "total_speech_duration": totals["audio"]["total_speech_duration"],
                    "speech_coverage_percent": (
                        (totals["audio"]["total_speech_duration"] / totals["video"]["duration_seconds"]) * 100.0
                        if totals["video"]["duration_seconds"] > 0 else 0
                    ),
                },
                "tracking": {
                    "frames_with_faces": totals["tracking"]["frames_with_faces"],
                    "frames_with_speaking": totals["tracking"]["frames_with_speaking"],
                    "max_faces_detected": totals["tracking"]["max_faces_detected"],
                    "face_coverage_percent": (
                        totals["tracking"]["face_coverage_percent_sum"] / totals["tracking"]["face_coverage_entries"]
                        if totals["tracking"]["face_coverage_entries"] > 0 else 0
                    ),
                }
            }

            context = {
                "project_name": project_name,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "videos": per_video,
                "consolidated": consolidated,
            }

            env = ReportService._get_jinja_env()
            try:
                template = env.get_template("project_report.html")
            except Exception as e:
                logger.warning(f"Project template not found, using fallback: {e}")
                ReportService._create_default_project_template()
                template = env.get_template("project_report.html")

            html_content = template.render(**context)

            result = {
                "project_name": project_name,
                "format": "html",
                "html": html_content,
                "consolidated": consolidated,
                "video_reports": per_video,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            return result

        except Exception as e:
            logger.error(f"Error generating project report: {e}", exc_info=True)
            return {"error": str(e)}
    
    @staticmethod
    def _compute_statistics(timeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute statistics from timeline data."""
        metadata = timeline_data.get("metadata", {})
        scenes = timeline_data.get("scenes", {})
        audio = timeline_data.get("audio", {})
        tracking = timeline_data.get("tracking", {})
        
        stats = {
            "video": {
                "duration_seconds": metadata.get("duration_seconds", 0),
                "total_frames": metadata.get("total_frames", 0),
                "fps": metadata.get("fps", 0),
            },
            "scenes": {
                "total_count": scenes.get("count", 0),
                "average_duration": 0,
                "shortest_duration": 0,
                "longest_duration": 0,
            },
            "audio": {
                "total_segments": audio.get("segment_count", 0),
                "unique_speakers": audio.get("speaker_count", 0),
                "total_speech_duration": 0,
                "speech_coverage_percent": 0,
            },
            "tracking": {
                "frames_with_faces": tracking.get("summary", {}).get("frames_with_faces", 0),
                "frames_with_speaking": tracking.get("summary", {}).get("frames_with_speaking", 0),
                "max_faces_detected": tracking.get("summary", {}).get("max_faces_detected", 0),
                "face_coverage_percent": tracking.get("summary", {}).get("face_coverage_percent", 0),
            }
        }
        
        if scenes.get("available") and scenes.get("scenes"):
            scene_list = scenes["scenes"]
            durations = [
                s.get("end_time_seconds", 0) - s.get("start_time_seconds", 0)
                for s in scene_list
            ]
            if durations:
                stats["scenes"]["average_duration"] = sum(durations) / len(durations)
                stats["scenes"]["shortest_duration"] = min(durations)
                stats["scenes"]["longest_duration"] = max(durations)
        
        if audio.get("available") and audio.get("segments"):
            segments = audio["segments"]
            speech_durations = [
                seg.get("end_time", 0) - seg.get("start_time", 0)
                for seg in segments
            ]
            if speech_durations:
                total_speech = sum(speech_durations)
                stats["audio"]["total_speech_duration"] = total_speech
                video_duration = metadata.get("duration_seconds", 1)
                if video_duration > 0:
                    stats["audio"]["speech_coverage_percent"] = (total_speech / video_duration) * 100
        
        return stats
    
    @staticmethod
    def _create_default_template():
        """Create a default report template if none exists."""
        template_dir = config.BASE_PATH_SCRIPTS / "templates" / "reports"
        template_dir.mkdir(parents=True, exist_ok=True)
        
        template_path = template_dir / "analysis_report.html"
        
        if template_path.exists():
            return
        
        default_template = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport d'Analyse - {{ video_name }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .header {
            border-bottom: 3px solid #007bff;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }
        
        .header h1 {
            color: #007bff;
            margin-bottom: 10px;
        }
        
        .meta-info {
            color: #666;
            font-size: 14px;
        }
        
        .section {
            margin-bottom: 40px;
        }
        
        .section-title {
            color: #007bff;
            border-left: 4px solid #007bff;
            padding-left: 15px;
            margin-bottom: 20px;
            font-size: 24px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }
        
        .stat-label {
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }
        
        .stat-value {
            font-size: 28px;
            font-weight: bold;
            color: #007bff;
        }
        
        .stat-unit {
            font-size: 14px;
            color: #666;
            font-weight: normal;
        }
        
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            margin-right: 10px;
        }
        
        .badge-success {
            background: #28a745;
            color: white;
        }
        
        .badge-warning {
            background: #ffc107;
            color: #333;
        }
        
        .badge-info {
            background: #17a2b8;
            color: white;
        }
        
        .badge-archive {
            background: #6c757d;
            color: white;
        }
        
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e9ecef;
            border-radius: 15px;
            overflow: hidden;
            margin-top: 10px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #007bff, #0056b3);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 14px;
        }
        
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #dee2e6;
            text-align: center;
            color: #666;
            font-size: 14px;
        }
        
        @media print {
            body {
                background: white;
                padding: 0;
            }
            .container {
                box-shadow: none;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Rapport d'Analyse Vidéo</h1>
            <div class="meta-info">
                <strong>Projet:</strong> {{ project_name }} | 
                <strong>Vidéo:</strong> {{ video_name }}<br>
                <strong>Généré le:</strong> {{ generated_at }}
                {% if archive_probe_source.metadata.provenance == 'archives' %}
                <br><span class="badge badge-archive">📦 Données archivées</span>
                {% endif %}
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📹 Métadonnées Vidéo</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-label">Durée</div>
                    <div class="stat-value">{{ statistics.video.duration_seconds|format_duration }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Frames Totales</div>
                    <div class="stat-value">{{ statistics.video.total_frames|int }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">FPS</div>
                    <div class="stat-value">{{ statistics.video.fps|round(2) }} <span class="stat-unit">fps</span></div>
                </div>
            </div>
        </div>
        
        {% if scenes.available %}
        <div class="section">
            <h2 class="section-title">✂️ Analyse des Scènes</h2>
            <span class="badge badge-success">{{ statistics.scenes.total_count }} scènes détectées</span>
            {% if archive_probe_source.scenes.provenance == 'archives' %}
            <span class="badge badge-archive">📦 Données archivées</span>
            {% endif %}
            
            <div class="stats-grid" style="margin-top: 20px;">
                <div class="stat-card">
                    <div class="stat-label">Durée Moyenne</div>
                    <div class="stat-value">{{ statistics.scenes.average_duration|round(1) }} <span class="stat-unit">s</span></div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Scène la Plus Courte</div>
                    <div class="stat-value">{{ statistics.scenes.shortest_duration|round(1) }} <span class="stat-unit">s</span></div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Scène la Plus Longue</div>
                    <div class="stat-value">{{ statistics.scenes.longest_duration|round(1) }} <span class="stat-unit">s</span></div>
                </div>
            </div>
        </div>
        {% endif %}
        
        {% if audio.available %}
        <div class="section">
            <h2 class="section-title">🔊 Analyse Audio</h2>
            <span class="badge badge-info">{{ statistics.audio.total_segments }} segments de parole</span>
            <span class="badge badge-info">{{ statistics.audio.unique_speakers }} locuteurs</span>
            {% if archive_probe_source.audio.provenance == 'archives' %}
            <span class="badge badge-archive">📦 Données archivées</span>
            {% endif %}
            
            <div class="stats-grid" style="margin-top: 20px;">
                <div class="stat-card">
                    <div class="stat-label">Durée Totale de Parole</div>
                    <div class="stat-value">{{ statistics.audio.total_speech_duration|format_duration }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Couverture Audio</div>
                    <div class="stat-value">{{ statistics.audio.speech_coverage_percent|format_percentage }}</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ statistics.audio.speech_coverage_percent }}%">
                            {{ statistics.audio.speech_coverage_percent|format_percentage }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}
        
        {% if tracking.available %}
        <div class="section">
            <h2 class="section-title">👤 Suivi des Visages</h2>
            <span class="badge badge-warning">{{ statistics.tracking.max_faces_detected }} visages max détectés</span>
            {% if archive_probe_source.tracking.provenance == 'archives' %}
            <span class="badge badge-archive">📦 Données archivées</span>
            {% endif %}
            
            <div class="stats-grid" style="margin-top: 20px;">
                <div class="stat-card">
                    <div class="stat-label">Frames avec Visages</div>
                    <div class="stat-value">{{ statistics.tracking.frames_with_faces|int }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Frames avec Parole Détectée</div>
                    <div class="stat-value">{{ statistics.tracking.frames_with_speaking|int }}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Couverture Visages</div>
                    <div class="stat-value">{{ statistics.tracking.face_coverage_percent|format_percentage }}</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ statistics.tracking.face_coverage_percent }}%">
                            {{ statistics.tracking.face_coverage_percent|format_percentage }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}
        
        <div class="footer">
            <p>Rapport généré par MediaPipe Workflow Analysis System</p>
            <p>{{ generated_at }}</p>
        </div>
    </div>
</body>
</html>"""
        
        with open(template_path, 'w', encoding='utf-8') as f:
            f.write(default_template)
        
        logger.info(f"Created default report template at {template_path}")

    @staticmethod
    def _create_default_project_template():
        """Create a default consolidated project report template if none exists."""
        template_dir = config.BASE_PATH_SCRIPTS / "templates" / "reports"
        template_dir.mkdir(parents=True, exist_ok=True)

        template_path = template_dir / "project_report.html"
        if template_path.exists():
            return

        default_template = """<!DOCTYPE html>
<html lang=\"fr\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Rapport de Projet - {{ project_name }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; background:#f5f5f5; color:#333; padding:20px; }
        .container { max-width: 1200px; margin:0 auto; background:#fff; border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,0.1); padding:40px; }
        .header { border-bottom:3px solid #007bff; padding-bottom:16px; margin-bottom:24px; }
        .header h1 { color:#007bff; margin:0 0 6px; }
        .section { margin:28px 0; }
        .section-title { color:#007bff; border-left:4px solid #007bff; padding-left:12px; font-size:22px; margin-bottom:12px; }
        .grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(260px,1fr)); gap:16px; }
        .card { background:#f8f9fa; border-left:4px solid #007bff; border-radius:8px; padding:16px; }
        .badge { display:inline-block; padding:4px 10px; border-radius:12px; font-size:12px; font-weight:600; margin-right:8px; }
        .badge-info { background:#17a2b8; color:#fff; }
        .table { width:100%; border-collapse:collapse; }
        .table th, .table td { border-bottom:1px solid #e9ecef; padding:10px; text-align:left; }
        .table th { background:#f1f3f5; }
        .muted { color:#666; font-size:13px; }
    </style>
</head>
<body>
<div class=\"container\">
  <div class=\"header\">
    <h1>📁 Rapport Consolidé du Projet</h1>
    <div class=\"muted\">Projet: <strong>{{ project_name }}</strong> · Généré le {{ generated_at }}</div>
  </div>

  <div class=\"section\">
    <h2 class=\"section-title\">📊 Statistiques Globales</h2>
    <div class=\"grid\">
      <div class=\"card\"><div class=\"muted\">Durée Totale</div><div style=\"font-size:28px;color:#007bff;\">{{ consolidated.video.duration_seconds|format_duration }}</div></div>
      <div class=\"card\"><div class=\"muted\">Frames Totales</div><div style=\"font-size:28px;color:#007bff;\">{{ consolidated.video.total_frames|int }}</div></div>
      <div class=\"card\"><div class=\"muted\">FPS Moyen</div><div style=\"font-size:28px;color:#007bff;\">{{ consolidated.video.fps|round(2) }}</div></div>
      <div class=\"card\"><div class=\"muted\">Scènes Totales</div><div style=\"font-size:28px;color:#007bff;\">{{ consolidated.scenes.total_count|int }}</div></div>
      <div class=\"card\"><div class=\"muted\">Segments de Parole</div><div style=\"font-size:28px;color:#007bff;\">{{ consolidated.audio.total_segments|int }}</div></div>
      <div class=\"card\"><div class=\"muted\">Locuteurs Uniques</div><div style=\"font-size:28px;color:#007bff;\">{{ consolidated.audio.unique_speakers|int }}</div></div>
      <div class=\"card\"><div class=\"muted\">Couverture Parole</div><div style=\"font-size:28px;color:#007bff;\">{{ consolidated.audio.speech_coverage_percent|format_percentage }}</div></div>
      <div class=\"card\"><div class=\"muted\">Frames avec Visages</div><div style=\"font-size:28px;color:#007bff;\">{{ consolidated.tracking.frames_with_faces|int }}</div></div>
    </div>
  </div>

  <div class=\"section\">
    <h2 class=\"section-title\">🎬 Détails par Vidéo</h2>
    <table class=\"table\">
      <thead>
        <tr>
          <th>Vidéo</th>
          <th>Durée</th>
          <th>Scènes</th>
          <th>Locuteurs</th>
          <th>Segments</th>
          <th>Faces (max)</th>
          <th>Couverture Visages</th>
          <th>Statut</th>
        </tr>
      </thead>
      <tbody>
        {% for v in videos %}
        <tr>
          <td>{{ v.video_name }}</td>
          {% if v.error %}
            <td colspan=\"6\" class=\"muted\">—</td>
            <td><span class=\"badge badge-info\">Erreur</span> {{ v.error }}</td>
          {% else %}
            <td>{{ v.statistics.video.duration_seconds|format_duration }}</td>
            <td>{{ v.statistics.scenes.total_count|int }}</td>
            <td>{{ v.metadata.get('speaker_count', 0) or v.statistics.audio.unique_speakers|int }}</td>
            <td>{{ v.statistics.audio.total_segments|int }}</td>
            <td>{{ v.statistics.tracking.max_faces_detected|int }}</td>
            <td>{{ v.statistics.tracking.face_coverage_percent|format_percentage }}</td>
            <td><span class=\"badge badge-info\">OK</span></td>
          {% endif %}
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>

  <div class=\"section\" style=\"text-align:center;color:#666;font-size:13px;\">
    Rapport généré par MediaPipe Workflow Analysis System · {{ generated_at }}
  </div>
</div>
</body>
</html>"""

        with open(template_path, "w", encoding="utf-8") as f:
            f.write(default_template)
        logger.info(f"Created default project report template at {template_path}")
