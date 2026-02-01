import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv", ".webm")
AUDIO_SUFFIX = "_audio.json"
TRACKING_SUFFIX = "_tracking.json"

_ENRICHMENT_SAMPLE_MAX_FRAMES = 50
_ENRICHMENT_SAMPLE_MAX_OBJECTS_PER_FRAME = 20
_TRACKING_ENRICH_FIELDS = (
    "confidence",
    "bbox_width",
    "bbox_height",
    "source",
    "label",
)

_CONFIDENCE_HISTOGRAM_BUCKETS = (
    (0.0, 0.25),
    (0.25, 0.5),
    (0.5, 0.75),
    (0.75, 0.9),
    (0.9, 1.0000001),
)


def _extract_top_level_metadata(data: Dict[str, Any]) -> Tuple[Optional[float], Optional[int]]:
    fps = None
    total_frames = None

    raw_fps = data.get("fps")
    raw_total = data.get("total_frames")
    if raw_fps is not None:
        try:
            fps = float(raw_fps)
        except Exception:
            fps = None
    if raw_total is not None:
        try:
            total_frames = int(raw_total)
        except Exception:
            total_frames = None

    meta = data.get("metadata")
    if isinstance(meta, dict):
        if fps is None and meta.get("fps") is not None:
            try:
                fps = float(meta.get("fps"))
            except Exception:
                fps = None
        if total_frames is None and meta.get("total_frames") is not None:
            try:
                total_frames = int(meta.get("total_frames"))
            except Exception:
                total_frames = None

    return fps, total_frames


def _write_json_atomically(path: Path, payload: Dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def _is_reduced_tracking_schema(data: Dict[str, Any]) -> bool:
    frames = data.get("frames_analysis")
    return isinstance(frames, list)


def _is_raw_tracking_schema(data: Dict[str, Any]) -> bool:
    frames = data.get("frames")
    return isinstance(frames, list)


def setup_logging(log_dir: str):
    os.makedirs(log_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_path = os.path.join(log_dir, f"json_reducer_{timestamp}.log")

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    fh = logging.FileHandler(log_path, encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)

    logger.handlers.clear()
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.propagate = False

    logger.info(f"Log file initialized: {log_path}")
    return log_path


def reduce_video_json(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Réduit un objet JSON de données vidéo pour ne conserver que les clés
    utiles au script After Effects.
    """
    fps, total_frames = _extract_top_level_metadata(data)

    frames_in: Optional[List[Dict[str, Any]]] = None
    if _is_raw_tracking_schema(data):
        frames_in = data.get("frames")
    elif _is_reduced_tracking_schema(data):
        frames_in = data.get("frames_analysis")
    else:
        return None

    new_frames_data: List[Dict[str, Any]] = []
    max_frame_seen: int = 0

    expression_summary_enabled = (
        os.environ.get("STEP6_INCLUDE_EXPRESSION_SUMMARY", "0").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    expression_keys_raw = os.environ.get("STEP6_EXPRESSION_KEYS", "jawOpen").strip()
    expression_keys = [k.strip() for k in expression_keys_raw.split(",") if k.strip()]
    expression_stats: Dict[str, Dict[str, Any]] = {}

    for frame in frames_in or []:
        new_tracked_objects = []
        if "tracked_objects" in frame and frame["tracked_objects"] is not None:
            for obj in frame["tracked_objects"]:
                # Initialisation de l'objet simplifié
                new_obj = {
                    "id": obj.get("id"),
                    "centroid_x": obj.get("centroid_x"),
                    "source": obj.get("source"),
                    "label": obj.get("label"),
                    "confidence": obj.get("confidence"),
                    "active_speakers": []  # Valeur par défaut
                }

                # Inclure la taille du bbox si disponible (ajout depuis l'étape 5)
                bbox_w = obj.get("bbox_width")
                bbox_h = obj.get("bbox_height")
                if bbox_w is not None and bbox_h is not None:
                    new_obj["bbox_width"] = bbox_w
                    new_obj["bbox_height"] = bbox_h

                # Extraction sécurisée de active_speakers
                if isinstance(obj.get("active_speakers"), list):
                    new_obj["active_speakers"] = obj.get("active_speakers") or []
                if (obj.get("speaking_sources") and
                        isinstance(obj["speaking_sources"], dict) and
                        obj["speaking_sources"].get("audio") and
                        isinstance(obj["speaking_sources"]["audio"], dict)):
                    new_obj["active_speakers"] = obj["speaking_sources"]["audio"].get("active_speakers", [])

                if expression_summary_enabled:
                    obj_id = obj.get("id")
                    blend = obj.get("blendshapes")
                    if isinstance(obj_id, str) and obj_id and isinstance(blend, dict) and blend:
                        stats = expression_stats.get(obj_id)
                        if stats is None:
                            stats = {"count": 0, "sum": {}, "max": {}}
                            expression_stats[obj_id] = stats
                        stats["count"] = int(stats.get("count", 0) or 0) + 1

                        sum_map = stats.get("sum")
                        if not isinstance(sum_map, dict):
                            sum_map = {}
                            stats["sum"] = sum_map
                        max_map = stats.get("max")
                        if not isinstance(max_map, dict):
                            max_map = {}
                            stats["max"] = max_map

                        for key in expression_keys:
                            if key not in blend:
                                continue
                            try:
                                val = float(blend.get(key))
                            except Exception:
                                continue
                            sum_map[key] = float(sum_map.get(key, 0.0) or 0.0) + val
                            prev_max = max_map.get(key)
                            if prev_max is None:
                                max_map[key] = val
                            else:
                                try:
                                    max_map[key] = max(float(prev_max), val)
                                except Exception:
                                    max_map[key] = val

                new_tracked_objects.append(new_obj)

        frame_num = frame.get("frame")
        try:
            if frame_num is not None:
                max_frame_seen = max(max_frame_seen, int(frame_num))
        except Exception:
            pass

        new_frames_data.append({
            "frame": frame_num,
            "tracked_objects": new_tracked_objects
        })

    if total_frames is None and max_frame_seen > 0:
        total_frames = max_frame_seen

    out: Dict[str, Any] = {"frames_analysis": new_frames_data}
    if fps is not None:
        out["fps"] = fps
    if total_frames is not None:
        out["total_frames"] = total_frames

    if expression_summary_enabled and expression_stats:
        summary_objects: Dict[str, Any] = {}
        for obj_id, stats in expression_stats.items():
            try:
                count = int(stats.get("count") or 0)
            except Exception:
                count = 0
            if count <= 0:
                continue
            sum_map = stats.get("sum")
            max_map = stats.get("max")
            if not isinstance(sum_map, dict) or not isinstance(max_map, dict):
                continue

            mean_map: Dict[str, Any] = {}
            for key, raw_sum in sum_map.items():
                try:
                    mean_map[key] = round(float(raw_sum) / float(count), 4)
                except Exception:
                    continue

            rounded_max: Dict[str, Any] = {}
            for key, raw_max in max_map.items():
                try:
                    rounded_max[key] = round(float(raw_max), 4)
                except Exception:
                    continue

            if mean_map or rounded_max:
                summary_objects[obj_id] = {
                    "count": count,
                    "mean": mean_map,
                    "max": rounded_max,
                }

        if summary_objects:
            out["expression_summary"] = {
                "keys": expression_keys,
                "objects": summary_objects,
            }
    return out


def _compute_tracking_analytics(reduced_tracking: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    frames = reduced_tracking.get("frames_analysis")
    if not isinstance(frames, list) or not frames:
        return None

    total_frames_raw = reduced_tracking.get("total_frames")
    total_frames: Optional[int]
    try:
        total_frames = int(total_frames_raw) if total_frames_raw is not None else None
    except Exception:
        total_frames = None

    if total_frames is None:
        max_frame_seen = 0
        for frame in frames:
            if not isinstance(frame, dict):
                continue
            frame_num = frame.get("frame")
            try:
                if frame_num is not None:
                    max_frame_seen = max(max_frame_seen, int(frame_num))
            except Exception:
                continue
        total_frames = max_frame_seen if max_frame_seen > 0 else None

    frames_with_objects = 0
    objects_per_frame_sum = 0
    confidence_histogram: Dict[str, int] = {}
    objects_stats: Dict[str, Dict[str, Any]] = {}

    for bucket_min, bucket_max in _CONFIDENCE_HISTOGRAM_BUCKETS:
        label = f"{bucket_min:.2f}-{min(bucket_max, 1.0):.2f}"
        confidence_histogram[label] = 0

    for frame in frames:
        if not isinstance(frame, dict):
            continue
        tracked = frame.get("tracked_objects")
        if not isinstance(tracked, list) or not tracked:
            continue
        frames_with_objects += 1
        objects_per_frame_sum += len(tracked)

        for obj in tracked:
            if not isinstance(obj, dict):
                continue
            obj_id = obj.get("id")
            if not isinstance(obj_id, str) or not obj_id:
                continue

            stats = objects_stats.get(obj_id)
            if stats is None:
                stats = {
                    "presence_frames": 0,
                    "confidence_sum": 0.0,
                    "confidence_count": 0,
                    "bbox_surface_sum": 0.0,
                    "bbox_surface_count": 0,
                    "centroid_x_min": None,
                    "centroid_x_max": None,
                    "source": obj.get("source"),
                    "label": obj.get("label"),
                }
                objects_stats[obj_id] = stats

            stats["presence_frames"] = int(stats.get("presence_frames", 0) or 0) + 1

            conf = obj.get("confidence")
            conf_f: Optional[float]
            try:
                conf_f = float(conf) if conf is not None else None
            except Exception:
                conf_f = None
            if conf_f is not None:
                if conf_f < 0.0:
                    conf_f = 0.0
                if conf_f > 1.0:
                    conf_f = 1.0
                stats["confidence_sum"] = float(stats.get("confidence_sum", 0.0) or 0.0) + conf_f
                stats["confidence_count"] = int(stats.get("confidence_count", 0) or 0) + 1

                for bucket_min, bucket_max in _CONFIDENCE_HISTOGRAM_BUCKETS:
                    if bucket_min <= conf_f < bucket_max:
                        label = f"{bucket_min:.2f}-{min(bucket_max, 1.0):.2f}"
                        confidence_histogram[label] = int(confidence_histogram.get(label, 0) or 0) + 1
                        break

            bbox_w = obj.get("bbox_width")
            bbox_h = obj.get("bbox_height")
            try:
                bbox_w_f = float(bbox_w) if bbox_w is not None else None
                bbox_h_f = float(bbox_h) if bbox_h is not None else None
            except Exception:
                bbox_w_f = None
                bbox_h_f = None
            if bbox_w_f is not None and bbox_h_f is not None:
                surface = max(0.0, bbox_w_f) * max(0.0, bbox_h_f)
                stats["bbox_surface_sum"] = float(stats.get("bbox_surface_sum", 0.0) or 0.0) + surface
                stats["bbox_surface_count"] = int(stats.get("bbox_surface_count", 0) or 0) + 1

            cx = obj.get("centroid_x")
            try:
                cx_f = float(cx) if cx is not None else None
            except Exception:
                cx_f = None
            if cx_f is not None:
                cx_min = stats.get("centroid_x_min")
                cx_max = stats.get("centroid_x_max")
                try:
                    stats["centroid_x_min"] = cx_f if cx_min is None else min(float(cx_min), cx_f)
                except Exception:
                    stats["centroid_x_min"] = cx_f
                try:
                    stats["centroid_x_max"] = cx_f if cx_max is None else max(float(cx_max), cx_f)
                except Exception:
                    stats["centroid_x_max"] = cx_f

    objects_out: Dict[str, Any] = {}
    for obj_id, stats in objects_stats.items():
        try:
            presence_frames = int(stats.get("presence_frames") or 0)
        except Exception:
            presence_frames = 0

        conf_count = 0
        try:
            conf_count = int(stats.get("confidence_count") or 0)
        except Exception:
            conf_count = 0
        avg_conf: Optional[float] = None
        if conf_count > 0:
            try:
                avg_conf = float(stats.get("confidence_sum") or 0.0) / float(conf_count)
            except Exception:
                avg_conf = None

        bbox_count = 0
        try:
            bbox_count = int(stats.get("bbox_surface_count") or 0)
        except Exception:
            bbox_count = 0
        avg_bbox_surface: Optional[float] = None
        if bbox_count > 0:
            try:
                avg_bbox_surface = float(stats.get("bbox_surface_sum") or 0.0) / float(bbox_count)
            except Exception:
                avg_bbox_surface = None

        cx_spread: Optional[float] = None
        cx_min = stats.get("centroid_x_min")
        cx_max = stats.get("centroid_x_max")
        try:
            if cx_min is not None and cx_max is not None:
                cx_spread = float(cx_max) - float(cx_min)
        except Exception:
            cx_spread = None

        presence_ratio: Optional[float] = None
        if total_frames is not None and total_frames > 0:
            presence_ratio = presence_frames / float(total_frames)

        obj_out: Dict[str, Any] = {
            "presence_frames": presence_frames,
            "source": stats.get("source"),
            "label": stats.get("label"),
        }
        if presence_ratio is not None:
            obj_out["presence_ratio"] = round(float(presence_ratio), 4)
        if avg_conf is not None:
            obj_out["avg_confidence"] = round(float(avg_conf), 4)
        if avg_bbox_surface is not None:
            obj_out["avg_bbox_surface"] = round(float(avg_bbox_surface), 2)
        if cx_spread is not None:
            obj_out["centroid_x_spread"] = round(float(cx_spread), 2)

        objects_out[obj_id] = obj_out

    frames_total_count = total_frames if total_frames is not None else len(frames)
    avg_objects_per_frame: Optional[float] = None
    if frames_with_objects > 0:
        avg_objects_per_frame = objects_per_frame_sum / float(frames_with_objects)

    global_out: Dict[str, Any] = {
        "frames_total": frames_total_count,
        "frames_with_objects": frames_with_objects,
        "objects_total": len(objects_stats),
        "confidence_histogram": confidence_histogram,
    }
    if avg_objects_per_frame is not None:
        global_out["avg_objects_per_frame"] = round(float(avg_objects_per_frame), 4)

    return {
        "schema_version": 1,
        "global": global_out,
        "objects": objects_out,
    }


def reduce_audio_json(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Réduit un objet JSON de données audio pour ne conserver que les clés
    utiles au script After Effects.
    """
    if "frames_analysis" not in data:
        return None

    fps, total_frames = _extract_top_level_metadata(data)

    new_frames_analysis: List[Dict[str, Any]] = []
    speaker_frame_counts: Dict[str, int] = {}
    max_frame_seen: int = 0
    for frame_data in data["frames_analysis"]:
        if "audio_info" in frame_data and frame_data["audio_info"] is not None:
            new_audio_info = {
                "is_speech_present": frame_data["audio_info"].get("is_speech_present", False),
                "active_speaker_labels": frame_data["audio_info"].get("active_speaker_labels", [])
            }
            if frame_data["audio_info"].get("timecode_sec") is not None:
                new_audio_info["timecode_sec"] = frame_data["audio_info"].get("timecode_sec")

            frame_num = frame_data.get("frame")
            try:
                if frame_num is not None:
                    max_frame_seen = max(max_frame_seen, int(frame_num))
            except Exception:
                pass
            new_frames_analysis.append({
                "frame": frame_num,
                "audio_info": new_audio_info
            })

            labels = new_audio_info.get("active_speaker_labels")
            if isinstance(labels, list):
                for label in labels:
                    if not isinstance(label, str) or not label:
                        continue
                    speaker_frame_counts[label] = speaker_frame_counts.get(label, 0) + 1

    if total_frames is None and max_frame_seen > 0:
        total_frames = max_frame_seen

    out: Dict[str, Any] = {"frames_analysis": new_frames_analysis}
    if fps is not None:
        out["fps"] = fps
    if total_frames is not None:
        out["total_frames"] = total_frames
    if speaker_frame_counts:
        out["speaker_stats"] = {
            "unique_speakers": sorted(list(speaker_frame_counts.keys())),
            "speaker_frame_counts": speaker_frame_counts,
        }

    speaker_embeddings = data.get("speaker_embeddings")
    if isinstance(speaker_embeddings, dict) and speaker_embeddings:
        out["speaker_embeddings"] = speaker_embeddings
    return out


def _compute_temporal_alignment(
    reduced_tracking: Dict[str, Any],
    reduced_audio: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not reduced_audio:
        return None

    v_total = reduced_tracking.get("total_frames")
    a_total = reduced_audio.get("total_frames")
    v_fps = reduced_tracking.get("fps")
    a_fps = reduced_audio.get("fps")

    try:
        v_total_i = int(v_total) if v_total is not None else None
    except Exception:
        v_total_i = None
    try:
        a_total_i = int(a_total) if a_total is not None else None
    except Exception:
        a_total_i = None

    try:
        v_fps_f = float(v_fps) if v_fps is not None else None
    except Exception:
        v_fps_f = None
    try:
        a_fps_f = float(a_fps) if a_fps is not None else None
    except Exception:
        a_fps_f = None

    if v_total_i is None and a_total_i is None and v_fps_f is None and a_fps_f is None:
        return None

    warnings: list[str] = []
    if v_total_i is not None and a_total_i is not None:
        ratio = abs(v_total_i - a_total_i) / float(max(a_total_i, 1))
        if ratio > 0.05:
            warnings.append(f"frame_count_mismatch video={v_total_i} audio={a_total_i}")

    if v_fps_f is not None and a_fps_f is not None:
        if abs(v_fps_f - a_fps_f) > 0.5:
            warnings.append(f"fps_mismatch video={v_fps_f} audio={a_fps_f}")

    return {
        "video_total_frames": v_total_i,
        "audio_total_frames": a_total_i,
        "video_fps": v_fps_f,
        "audio_fps": a_fps_f,
        "warnings": warnings,
    }


def _resolve_tracking_paths(
    docs_path: Path,
    video_stem: str,
) -> Tuple[Optional[Path], Optional[Path], Optional[Path]]:
    preferred = docs_path / f"{video_stem}{TRACKING_SUFFIX}"
    legacy = docs_path / f"{video_stem}.json"
    if preferred.exists():
        fallback = legacy if legacy.exists() else None
        return preferred, preferred, fallback
    if legacy.exists():
        return legacy, preferred, None
    return None, None, None


def _reduced_tracking_needs_enrichment(reduced_tracking: Dict[str, Any]) -> bool:
    frames = reduced_tracking.get("frames_analysis")
    if not isinstance(frames, list) or not frames:
        return False

    sampled_frames = frames[:_ENRICHMENT_SAMPLE_MAX_FRAMES]
    for frame in sampled_frames:
        if not isinstance(frame, dict):
            continue
        tracked = frame.get("tracked_objects")
        if not isinstance(tracked, list) or not tracked:
            continue
        sampled_objs = tracked[:_ENRICHMENT_SAMPLE_MAX_OBJECTS_PER_FRAME]
        for obj in sampled_objs:
            if not isinstance(obj, dict):
                continue
            for key in _TRACKING_ENRICH_FIELDS:
                if key not in obj or obj.get(key) is None:
                    return True
    return False


def _index_reduced_tracking_by_frame_and_id(reduced_tracking: Dict[str, Any]) -> Dict[int, Dict[str, Dict[str, Any]]]:
    frames = reduced_tracking.get("frames_analysis")
    if not isinstance(frames, list):
        return {}

    index: Dict[int, Dict[str, Dict[str, Any]]] = {}
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        frame_num = frame.get("frame")
        try:
            frame_i = int(frame_num)
        except Exception:
            continue
        tracked = frame.get("tracked_objects")
        if not isinstance(tracked, list):
            continue
        frame_map: Dict[str, Dict[str, Any]] = {}
        for obj in tracked:
            if not isinstance(obj, dict):
                continue
            obj_id = obj.get("id")
            if not isinstance(obj_id, str) or not obj_id:
                continue
            frame_map[obj_id] = obj
        if frame_map:
            index[frame_i] = frame_map
    return index


def _merge_reduced_tracking(
    base_tracking: Dict[str, Any],
    supplemental_tracking: Dict[str, Any],
) -> Dict[str, Any]:
    supplemental_index = _index_reduced_tracking_by_frame_and_id(supplemental_tracking)
    frames = base_tracking.get("frames_analysis")
    if not isinstance(frames, list) or not supplemental_index:
        return base_tracking

    for frame in frames:
        if not isinstance(frame, dict):
            continue
        frame_num = frame.get("frame")
        try:
            frame_i = int(frame_num)
        except Exception:
            continue
        supp_frame = supplemental_index.get(frame_i)
        if not supp_frame:
            continue
        tracked = frame.get("tracked_objects")
        if not isinstance(tracked, list):
            continue

        for obj in tracked:
            if not isinstance(obj, dict):
                continue
            obj_id = obj.get("id")
            if not isinstance(obj_id, str) or not obj_id:
                continue
            supp_obj = supp_frame.get(obj_id)
            if not supp_obj:
                continue

            for key in _TRACKING_ENRICH_FIELDS:
                if (key not in obj) or (obj.get(key) is None):
                    if supp_obj.get(key) is not None:
                        obj[key] = supp_obj.get(key)

            base_speakers = obj.get("active_speakers")
            supp_speakers = supp_obj.get("active_speakers")
            if (
                (base_speakers is None or base_speakers == [])
                and isinstance(supp_speakers, list)
                and supp_speakers
            ):
                obj["active_speakers"] = supp_speakers

    base_total = base_tracking.get("total_frames")
    supp_total = supplemental_tracking.get("total_frames")
    try:
        base_total_i = int(base_total) if base_total is not None else None
    except Exception:
        base_total_i = None
    try:
        supp_total_i = int(supp_total) if supp_total is not None else None
    except Exception:
        supp_total_i = None

    if base_total_i is None and supp_total_i is not None:
        base_tracking["total_frames"] = supp_total_i
    elif base_total_i is not None and supp_total_i is not None:
        base_tracking["total_frames"] = max(base_total_i, supp_total_i)

    if base_tracking.get("fps") is None and supplemental_tracking.get("fps") is not None:
        base_tracking["fps"] = supplemental_tracking.get("fps")

    return base_tracking


def process_directory(base_path: str, keyword: str = "Camille"):
    """
    Analyse les dossiers dans le chemin de base, recherche le mot-clé,
    et traite les paires de fichiers JSON trouvées dans les sous-dossiers "docs".
    """
    base = Path(base_path)
    tracking_analytics_enabled = (
        os.environ.get("STEP6_INCLUDE_TRACKING_ANALYTICS", "1").strip().lower()
        in {"1", "true", "yes", "on"}
    )
    logger.info(f"Démarrage du scan dans : {base}")
    if not base.is_dir():
        logger.error(f"Erreur : Le répertoire de base '{base_path}' n'existe pas.")
        return

    # 1. Lister les dossiers de projet
    project_folders = [
        d.name
        for d in base.iterdir()
        if d.is_dir() and keyword in d.name
    ]

    if not project_folders:
        print(f"Aucun dossier contenant le mot-clé '{keyword}' n'a été trouvé.")
        return

    logger.info(f"Dossiers de projet trouvés : {len(project_folders)}")

    total_projects = len(project_folders)
    for idx, folder in enumerate(project_folders, start=1):
        print(f"REDUCING_JSON: {idx}/{total_projects}: {folder}")
        docs_path = base / folder / "docs"

        if not docs_path.is_dir():
            logger.warning(f"-> Avertissement : Le dossier 'docs' est manquant dans '{folder}'.")
            continue

        logger.info(f"\n--- Traitement du dossier : {docs_path} ---")

        video_files = [
            p for p in docs_path.iterdir()
            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
        ]
        if not video_files:
            logger.info("Aucune vidéo trouvée dans docs/.")
            continue

        for v_idx, video_path in enumerate(video_files, start=1):
            stem = video_path.stem
            audio_path = docs_path / f"{stem}{AUDIO_SUFFIX}"
            tracking_in, tracking_out, tracking_fallback = _resolve_tracking_paths(docs_path, stem)

            if tracking_in is None:
                logger.warning(f"  - Tracking JSON introuvable pour '{video_path.name}'.")
                continue
            if not audio_path.exists():
                logger.warning(f"  - Fichier audio '{audio_path.name}' manquant pour '{video_path.name}'.")

            logger.info(
                "  - Cible: %s | tracking_in=%s | tracking_out=%s | audio=%s",
                video_path.name,
                tracking_in.name,
                tracking_out.name if tracking_out else "(none)",
                audio_path.name,
            )
            print(f"INTERNAL_PROGRESS: {v_idx}/{len(video_files)} items ({int(round((v_idx / float(len(video_files))) * 100))}%) - {video_path.name}")

            try:
                with open(tracking_in, "r", encoding="utf-8") as f:
                    tracking_data = json.load(f)

                reduced_tracking = reduce_video_json(tracking_data)
                if reduced_tracking is None:
                    logger.warning(f"    - Tracking JSON ignoré (schéma inattendu): {tracking_in}")
                else:
                    assert tracking_out is not None

                    if (
                        tracking_fallback is not None
                        and tracking_fallback.exists()
                        and tracking_in.resolve() != tracking_fallback.resolve()
                        and _reduced_tracking_needs_enrichment(reduced_tracking)
                    ):
                        try:
                            with open(tracking_fallback, "r", encoding="utf-8") as f:
                                legacy_tracking_data = json.load(f)
                            legacy_reduced = reduce_video_json(legacy_tracking_data)
                            if legacy_reduced is not None:
                                reduced_tracking = _merge_reduced_tracking(reduced_tracking, legacy_reduced)
                                logger.info(
                                    "    - Tracking enrichi depuis legacy: %s -> %s",
                                    tracking_fallback.name,
                                    tracking_out.name,
                                )
                        except Exception as e:
                            logger.warning(
                                "    - Enrichissement legacy ignoré (erreur non bloquante) pour %s: %s",
                                tracking_fallback.name,
                                e,
                            )

                    reduced_audio = None
                    if audio_path.exists():
                        with open(audio_path, "r", encoding="utf-8") as f:
                            audio_data = json.load(f)
                        reduced_audio = reduce_audio_json(audio_data)
                        if reduced_audio is None:
                            logger.warning(f"    - Audio JSON ignoré (schéma inattendu): {audio_path}")
                        else:
                            _write_json_atomically(audio_path, reduced_audio)
                            logger.info("    - Audio réduit avec succès: %s", audio_path.name)

                    temporal = _compute_temporal_alignment(reduced_tracking, reduced_audio)
                    if temporal:
                        reduced_tracking["temporal_alignment"] = temporal

                    if tracking_analytics_enabled:
                        analytics = _compute_tracking_analytics(reduced_tracking)
                        if analytics:
                            reduced_tracking["tracking_analytics"] = analytics

                    _write_json_atomically(tracking_out, reduced_tracking)
                    logger.info("    - Tracking réduit avec succès: %s", tracking_out.name)

                    if temporal and temporal.get("warnings"):
                        logger.warning(
                            "    - Désalignement temporel détecté (%s): %s",
                            stem,
                            ", ".join([str(w) for w in temporal.get("warnings") or []]),
                        )

            except json.JSONDecodeError as e:
                logger.error(f"    - ERREUR : Impossible de lire un fichier JSON. Erreur : {e}")
            except Exception as e:
                logger.error(f"    - ERREUR : Une erreur inattendue est survenue. Erreur : {e}")

        print(f"Succès: réduction JSON terminée pour {folder}")

    logger.info("\n--- Traitement terminé ! ---")


def main():
    parser = argparse.ArgumentParser(description="Étape 6 - Réduction JSON (vidéo + audio)")
    parser.add_argument('--base_dir', type=str, default=os.environ.get('BASE_PATH_SCRIPTS', ''), help='Chemin base du projet (contenant projets_extraits)')
    parser.add_argument('--work_dir', type=str, default=None, help='Chemin explicite vers projets_extraits')
    parser.add_argument('--keyword', type=str, default=os.environ.get('FOLDER_KEYWORD', 'Camille'), help='Mot-clé pour filtrer les dossiers projet')
    parser.add_argument('--log_dir', type=str, default=str(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'logs', 'step6')),
                        help='Répertoire pour les logs (par défaut logs/step6)')

    args = parser.parse_args()

    # Resolve working directory
    if args.work_dir:
        work_dir = args.work_dir
    else:
        base_dir = args.base_dir if args.base_dir else os.getcwd()
        work_dir = os.path.join(base_dir, 'projets_extraits')

    # Setup logging
    setup_logging(args.log_dir)

    # Progress total: count candidate projects
    try:
        if not os.path.isdir(work_dir):
            logger.warning(f"Répertoire de travail introuvable: {work_dir}")
            print(f"TOTAL_JSON_TO_REDUCE: 0")
            sys.exit(0)
        projects = [d for d in os.listdir(work_dir) if os.path.isdir(os.path.join(work_dir, d)) and args.keyword in d]
        print(f"TOTAL_JSON_TO_REDUCE: {len(projects)}")
    except Exception:
        print("TOTAL_JSON_TO_REDUCE: 0")

    # Run processing
    process_directory(work_dir, keyword=args.keyword)


if __name__ == "__main__":
    main()
