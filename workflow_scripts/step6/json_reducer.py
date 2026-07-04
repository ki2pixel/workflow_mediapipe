import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import ijson

# Constants (Magic Strings)
KEY_FRAMES_ANALYSIS = "frames_analysis"
KEY_TRACKED_OBJECTS = "tracked_objects"
KEY_ACTIVE_SPEAKERS = "active_speakers"
KEY_CONFIDENCE = "confidence"
KEY_SOURCE = "source"
KEY_LABEL = "label"
KEY_BBOX_WIDTH = "bbox_width"
KEY_BBOX_HEIGHT = "bbox_height"
KEY_CENTROID_X = "centroid_x"
KEY_TOTAL_FRAMES = "total_frames"
KEY_FPS = "fps"


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv", ".webm")
AUDIO_SUFFIX = "_audio.json"
TRACKING_SUFFIX = "_tracking.json"

_ENRICHMENT_SAMPLE_MAX_FRAMES = 50
_ENRICHMENT_SAMPLE_MAX_OBJECTS_PER_FRAME = 20
_TRACKING_ENRICH_FIELDS = (
    KEY_CONFIDENCE,
    KEY_BBOX_WIDTH,
    KEY_BBOX_HEIGHT,
    KEY_SOURCE,
    KEY_LABEL,
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

    raw_fps = data.get(KEY_FPS)
    raw_total = data.get(KEY_TOTAL_FRAMES)
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
        if fps is None and meta.get(KEY_FPS) is not None:
            try:
                fps = float(meta.get(KEY_FPS))
            except Exception:
                fps = None
        if total_frames is None and meta.get(KEY_TOTAL_FRAMES) is not None:
            try:
                total_frames = int(meta.get(KEY_TOTAL_FRAMES))
            except Exception:
                total_frames = None

    return fps, total_frames

def _extract_metadata_streaming(file_path: Path) -> Tuple[Optional[float], Optional[int], Optional[str]]:
    fps = None
    total_frames = None
    array_key = None
    
    try:
        with open(file_path, 'rb') as f:
            parser = ijson.parse(f, use_float=True)
            for prefix, event, value in parser:
                if event == 'start_array' and prefix in ('frames', KEY_FRAMES_ANALYSIS):
                    array_key = prefix
                    break
                
                if prefix == KEY_FPS and event in ('number', 'integer'):
                    fps = float(value)
                elif prefix == KEY_TOTAL_FRAMES and event == 'integer':
                    total_frames = int(value)
                elif prefix == 'metadata.fps' and event in ('number', 'integer'):
                    fps = float(value)
                elif prefix == 'metadata.total_frames' and event == 'integer':
                    total_frames = int(value)
    except ijson.JSONError as e:
        logger.error(f"Format JSON invalide lors de l'extraction de métadonnées pour {file_path.name}: {e}")
    except StopIteration:
        logger.error(f"Fichier JSON tronqué ou structure vide pour {file_path.name}")
    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'extraction de métadonnées pour {file_path.name}: {e}")
        
    return fps, total_frames, array_key


def _write_json_atomically(path: Path, payload: Dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def _is_reduced_tracking_schema(data: Dict[str, Any]) -> bool:
    frames = data.get(KEY_FRAMES_ANALYSIS)
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


class TrackingAnalyticsBuilder:
    def __init__(self):
        self.frames_with_objects = 0
        self.objects_per_frame_sum = 0
        self.confidence_histogram: Dict[str, int] = {
            f"{b_min:.2f}-{min(b_max, 1.0):.2f}": 0 for b_min, b_max in _CONFIDENCE_HISTOGRAM_BUCKETS
        }
        self.objects_stats: Dict[str, Dict[str, Any]] = {}

    def add_frame(self, frame: Dict[str, Any]):
        tracked = frame.get(KEY_TRACKED_OBJECTS)
        if not isinstance(tracked, list) or not tracked:
            return
            
        self.frames_with_objects += 1
        self.objects_per_frame_sum += len(tracked)
        
        for obj in tracked:
            if not isinstance(obj, dict): continue
            obj_id = obj.get("id")
            if not isinstance(obj_id, str) or not obj_id: continue
            
            stats = self.objects_stats.get(obj_id)
            if stats is None:
                stats = {
                    "presence_frames": 0, "confidence_sum": 0.0, "confidence_count": 0,
                    "bbox_surface_sum": 0.0, "bbox_surface_count": 0,
                    "centroid_x_min": None, "centroid_x_max": None,
                    KEY_SOURCE: obj.get(KEY_SOURCE), KEY_LABEL: obj.get(KEY_LABEL)
                }
                self.objects_stats[obj_id] = stats
                
            stats["presence_frames"] += 1
            
            conf = obj.get(KEY_CONFIDENCE)
            if conf is not None:
                try:
                    conf_f = float(conf)
                    conf_f = max(0.0, min(1.0, conf_f))
                    stats["confidence_sum"] += conf_f
                    stats["confidence_count"] += 1
                    for b_min, b_max in _CONFIDENCE_HISTOGRAM_BUCKETS:
                        if b_min <= conf_f < b_max:
                            label = f"{b_min:.2f}-{min(b_max, 1.0):.2f}"
                            self.confidence_histogram[label] += 1
                            break
                except Exception: pass
                
            bbox_w = obj.get(KEY_BBOX_WIDTH)
            bbox_h = obj.get(KEY_BBOX_HEIGHT)
            if bbox_w is not None and bbox_h is not None:
                try:
                    surface = max(0.0, float(bbox_w)) * max(0.0, float(bbox_h))
                    stats["bbox_surface_sum"] += surface
                    stats["bbox_surface_count"] += 1
                except Exception: pass
                
            cx = obj.get(KEY_CENTROID_X)
            if cx is not None:
                try:
                    cx_f = float(cx)
                    if stats["centroid_x_min"] is None or cx_f < stats["centroid_x_min"]:
                        stats["centroid_x_min"] = cx_f
                    if stats["centroid_x_max"] is None or cx_f > stats["centroid_x_max"]:
                        stats["centroid_x_max"] = cx_f
                except Exception: pass

    def build(self, total_frames: Optional[int], frames_count: int) -> Dict[str, Any]:
        objects_out = {}
        frames_total_count = total_frames if total_frames is not None else frames_count
        
        for obj_id, stats in self.objects_stats.items():
            presence_frames = stats["presence_frames"]
            avg_conf = (stats["confidence_sum"] / stats["confidence_count"]) if stats["confidence_count"] > 0 else None
            avg_bbox = (stats["bbox_surface_sum"] / stats["bbox_surface_count"]) if stats["bbox_surface_count"] > 0 else None
            
            cx_spread = None
            if stats["centroid_x_min"] is not None and stats["centroid_x_max"] is not None:
                cx_spread = stats["centroid_x_max"] - stats["centroid_x_min"]
                
            presence_ratio = (presence_frames / float(frames_total_count)) if frames_total_count and frames_total_count > 0 else None
            
            obj_out = {
                "presence_frames": presence_frames,
                KEY_SOURCE: stats.get(KEY_SOURCE),
                KEY_LABEL: stats.get(KEY_LABEL),
            }
            if presence_ratio is not None: obj_out["presence_ratio"] = round(presence_ratio, 4)
            if avg_conf is not None: obj_out["avg_confidence"] = round(avg_conf, 4)
            if avg_bbox is not None: obj_out["avg_bbox_surface"] = round(avg_bbox, 2)
            if cx_spread is not None: obj_out["centroid_x_spread"] = round(cx_spread, 2)
            
            objects_out[obj_id] = obj_out
            
        avg_objects = (self.objects_per_frame_sum / float(self.frames_with_objects)) if self.frames_with_objects > 0 else None
        
        global_out = {
            "frames_total": frames_total_count,
            "frames_with_objects": self.frames_with_objects,
            "objects_total": len(self.objects_stats),
            "confidence_histogram": self.confidence_histogram,
        }
        if avg_objects is not None:
            global_out["avg_objects_per_frame"] = round(avg_objects, 4)
            
        return {
            "schema_version": 1,
            "global": global_out,
            "objects": objects_out
        }


def _process_tracked_object(obj, legacy_frame, expression_summary_enabled, expression_keys, expression_stats):
    obj_id = obj.get("id")
    legacy_obj = legacy_frame.get(obj_id) if legacy_frame else None
    
    new_obj = {
        "id": obj_id,
        KEY_CENTROID_X: obj.get(KEY_CENTROID_X),
        KEY_SOURCE: obj.get(KEY_SOURCE),
        KEY_LABEL: obj.get(KEY_LABEL),
        KEY_CONFIDENCE: obj.get(KEY_CONFIDENCE),
        KEY_ACTIVE_SPEAKERS: []
    }
    
    bbox_w = obj.get(KEY_BBOX_WIDTH)
    bbox_h = obj.get(KEY_BBOX_HEIGHT)
    if bbox_w is not None and bbox_h is not None:
        new_obj[KEY_BBOX_WIDTH] = bbox_w
        new_obj[KEY_BBOX_HEIGHT] = bbox_h
        
    if isinstance(obj.get(KEY_ACTIVE_SPEAKERS), list):
        new_obj[KEY_ACTIVE_SPEAKERS] = obj.get(KEY_ACTIVE_SPEAKERS) or []
    if (obj.get("speaking_sources") and isinstance(obj["speaking_sources"], dict) and 
        obj["speaking_sources"].get("audio") and isinstance(obj["speaking_sources"]["audio"], dict)):
        new_obj[KEY_ACTIVE_SPEAKERS] = obj["speaking_sources"]["audio"].get(KEY_ACTIVE_SPEAKERS, [])
        
    if legacy_obj:
        for k in _TRACKING_ENRICH_FIELDS:
            if new_obj.get(k) is None and legacy_obj.get(k) is not None:
                new_obj[k] = legacy_obj[k]
        if not new_obj[KEY_ACTIVE_SPEAKERS] and legacy_obj.get(KEY_ACTIVE_SPEAKERS):
            new_obj[KEY_ACTIVE_SPEAKERS] = legacy_obj[KEY_ACTIVE_SPEAKERS]
            
    if expression_summary_enabled:
        blend = obj.get("blendshapes")
        if isinstance(obj_id, str) and obj_id and isinstance(blend, dict) and blend:
            stats = expression_stats.get(obj_id)
            if stats is None:
                stats = {"count": 0, "sum": {}, "max": {}}
                expression_stats[obj_id] = stats
            stats["count"] += 1
            
            for key in expression_keys:
                if key in blend:
                    try:
                        val = float(blend[key])
                        stats["sum"][key] = stats["sum"].get(key, 0.0) + val
                        stats["max"][key] = max(stats["max"].get(key, val), val)
                    except Exception: pass
                    
    return new_obj

def stream_reduce_video_json(
    input_path: Path, 
    output_path: Path,
    legacy_tracking_path: Optional[Path] = None,
    audio_metadata: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    fps, total_frames, array_key = _extract_metadata_streaming(input_path)
    if not array_key:
        logger.warning(f"Aucun tableau 'frames' trouvé en streaming pour {input_path}")
        return None
        
    tracking_analytics_enabled = os.environ.get("STEP6_INCLUDE_TRACKING_ANALYTICS", "1").strip().lower() in {"1", "true", "yes", "on"}
    expression_summary_enabled = os.environ.get("STEP6_INCLUDE_EXPRESSION_SUMMARY", "0").strip().lower() in {"1", "true", "yes", "on"}
    expression_keys_raw = os.environ.get("STEP6_EXPRESSION_KEYS", "jawOpen").strip()
    expression_keys = [k.strip() for k in expression_keys_raw.split(",") if k.strip()]
    
    expression_stats: Dict[str, Dict[str, Any]] = {}
    analytics_builder = TrackingAnalyticsBuilder() if tracking_analytics_enabled else None
    
    # Preload legacy tracking if provided (fallback logic, usually small)
    legacy_index = {}
    if legacy_tracking_path and legacy_tracking_path.exists():
        try:
            with open(legacy_tracking_path, 'r', encoding='utf-8') as lf:
                legacy_data = json.load(lf)
                lf_frames = legacy_data.get(KEY_FRAMES_ANALYSIS) or legacy_data.get("frames") or []
                for f in lf_frames:
                    if isinstance(f, dict) and "frame" in f:
                        try:
                            f_i = int(f["frame"])
                            legacy_index[f_i] = {obj.get("id"): obj for obj in f.get(KEY_TRACKED_OBJECTS, []) if isinstance(obj, dict) and obj.get("id")}
                        except Exception: pass
        except Exception as e:
            logger.warning(f"Erreur de lecture legacy_tracking {legacy_tracking_path}: {e}")
            
    tmp_path = output_path.with_suffix(".tmp")
    max_frame_seen = 0
    frames_count = 0
    
    with open(input_path, 'rb') as f_in, open(tmp_path, 'w', encoding='utf-8') as f_out:
        f_out.write(f'{{\n  "{KEY_FRAMES_ANALYSIS}": [\n')
        
        items = ijson.items(f_in, f"{array_key}.item", use_float=True)
        first = True
        
        for frame in items:
            new_tracked_objects = []
            frame_num = frame.get("frame")
            
            try:
                frame_i = int(frame_num) if frame_num is not None else None
            except Exception:
                frame_i = None
                
            legacy_frame = legacy_index.get(frame_i) if frame_i is not None else None
            
            if KEY_TRACKED_OBJECTS in frame and frame[KEY_TRACKED_OBJECTS] is not None:
                for obj in frame[KEY_TRACKED_OBJECTS]:
                    new_obj = _process_tracked_object(obj, legacy_frame, expression_summary_enabled, expression_keys, expression_stats)
                    new_tracked_objects.append(new_obj)
                    
            if frame_i is not None:
                max_frame_seen = max(max_frame_seen, frame_i)
                
            reduced_frame = {
                "frame": frame_num,
                KEY_TRACKED_OBJECTS: new_tracked_objects
            }
            
            if analytics_builder:
                analytics_builder.add_frame(reduced_frame)
                
            if not first:
                f_out.write(',\n')
            first = False
            
            json.dump(reduced_frame, f_out, indent=4, ensure_ascii=False)
            frames_count += 1
            
        f_out.write('\n  ]')
        
        if total_frames is None and max_frame_seen > 0:
            total_frames = max_frame_seen
            
        if fps is not None:
            f_out.write(f',\n  "{KEY_FPS}": {fps}')
        if total_frames is not None:
            f_out.write(f',\n  "{KEY_TOTAL_FRAMES}": {total_frames}')
            
        if expression_summary_enabled and expression_stats:
            summary_objects = {}
            for obj_id, stats in expression_stats.items():
                count = stats.get("count", 0)
                if count <= 0: continue
                mean_map = {k: round(v / count, 4) for k, v in stats.get("sum", {}).items()}
                max_map = {k: round(v, 4) for k, v in stats.get("max", {}).items()}
                if mean_map or max_map:
                    summary_objects[obj_id] = {"count": count, "mean": mean_map, "max": max_map}
            if summary_objects:
                f_out.write(',\n  "expression_summary": ')
                json.dump({"keys": expression_keys, "objects": summary_objects}, f_out, indent=4, ensure_ascii=False)
                
        if analytics_builder:
            analytics = analytics_builder.build(total_frames, frames_count)
            f_out.write(',\n  "tracking_analytics": ')
            json.dump(analytics, f_out, indent=4, ensure_ascii=False)
            
        if audio_metadata:
            temporal = _compute_temporal_alignment({KEY_FPS: fps, KEY_TOTAL_FRAMES: total_frames}, audio_metadata)
            if temporal:
                f_out.write(',\n  "temporal_alignment": ')
                json.dump(temporal, f_out, indent=4, ensure_ascii=False)
                
        f_out.write('\n}\n')
        
    os.replace(tmp_path, output_path)
    return {KEY_FPS: fps, KEY_TOTAL_FRAMES: total_frames}


def reduce_video_json(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Maintained for unit tests / fallback compatibility
    fps, total_frames = _extract_top_level_metadata(data)
    frames_in = data.get("frames") if _is_raw_tracking_schema(data) else data.get(KEY_FRAMES_ANALYSIS)
    if frames_in is None: return None
    
    new_frames_data = []
    max_frame_seen = 0
    expression_summary_enabled = os.environ.get("STEP6_INCLUDE_EXPRESSION_SUMMARY", "0").strip().lower() in {"1", "true", "yes", "on"}
    expression_keys_raw = os.environ.get("STEP6_EXPRESSION_KEYS", "jawOpen").strip()
    expression_keys = [k.strip() for k in expression_keys_raw.split(",") if k.strip()]
    expression_stats = {}
    
    for frame in frames_in or []:
        new_tracked_objects = []
        if KEY_TRACKED_OBJECTS in frame and frame[KEY_TRACKED_OBJECTS] is not None:
            for obj in frame[KEY_TRACKED_OBJECTS]:
                new_obj = _process_tracked_object(obj, None, expression_summary_enabled, expression_keys, expression_stats)
                new_tracked_objects.append(new_obj)
        frame_num = frame.get("frame")
        try:
            if frame_num is not None: max_frame_seen = max(max_frame_seen, int(frame_num))
        except Exception: pass
        new_frames_data.append({"frame": frame_num, KEY_TRACKED_OBJECTS: new_tracked_objects})
        
    if total_frames is None and max_frame_seen > 0: total_frames = max_frame_seen
    out = {KEY_FRAMES_ANALYSIS: new_frames_data}
    if fps is not None: out[KEY_FPS] = fps
    if total_frames is not None: out[KEY_TOTAL_FRAMES] = total_frames
    
    if expression_summary_enabled and expression_stats:
        summary_objects = {}
        for obj_id, stats in expression_stats.items():
            count = stats.get("count", 0)
            if count <= 0: continue
            mean_map = {k: round(v / count, 4) for k, v in stats.get("sum", {}).items()}
            max_map = {k: round(v, 4) for k, v in stats.get("max", {}).items()}
            if mean_map or max_map:
                summary_objects[obj_id] = {"count": count, "mean": mean_map, "max": max_map}
        if summary_objects:
            out["expression_summary"] = {"keys": expression_keys, "objects": summary_objects}
    return out


def _compute_tracking_analytics(reduced_tracking: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Maintained for unit tests / fallback compatibility
    frames = reduced_tracking.get(KEY_FRAMES_ANALYSIS)
    if not isinstance(frames, list) or not frames: return None
    
    total_frames_raw = reduced_tracking.get(KEY_TOTAL_FRAMES)
    try:
        total_frames = int(total_frames_raw) if total_frames_raw is not None else None
    except Exception: total_frames = None
    
    if total_frames is None:
        max_frame_seen = 0
        for f in frames:
            if isinstance(f, dict) and f.get("frame") is not None:
                try: max_frame_seen = max(max_frame_seen, int(f["frame"]))
                except Exception: pass
        total_frames = max_frame_seen if max_frame_seen > 0 else None
        
    builder = TrackingAnalyticsBuilder()
    for f in frames:
        if isinstance(f, dict): builder.add_frame(f)
    return builder.build(total_frames, len(frames))

def reduce_audio_json(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if KEY_FRAMES_ANALYSIS not in data: return None
    fps, total_frames = _extract_top_level_metadata(data)
    new_frames_analysis = []
    speaker_frame_counts = {}
    max_frame_seen = 0
    
    for frame_data in data[KEY_FRAMES_ANALYSIS]:
        if "audio_info" in frame_data and frame_data["audio_info"] is not None:
            new_audio_info = {
                "is_speech_present": frame_data["audio_info"].get("is_speech_present", False),
                "active_speaker_labels": frame_data["audio_info"].get("active_speaker_labels", [])
            }
            if frame_data["audio_info"].get("timecode_sec") is not None:
                new_audio_info["timecode_sec"] = frame_data["audio_info"].get("timecode_sec")
            frame_num = frame_data.get("frame")
            try:
                if frame_num is not None: max_frame_seen = max(max_frame_seen, int(frame_num))
            except Exception: pass
            new_frames_analysis.append({"frame": frame_num, "audio_info": new_audio_info})
            labels = new_audio_info.get("active_speaker_labels")
            if isinstance(labels, list):
                for label in labels:
                    if isinstance(label, str) and label:
                        speaker_frame_counts[label] = speaker_frame_counts.get(label, 0) + 1
                        
    if total_frames is None and max_frame_seen > 0: total_frames = max_frame_seen
    out = {KEY_FRAMES_ANALYSIS: new_frames_analysis}
    if fps is not None: out[KEY_FPS] = fps
    if total_frames is not None: out[KEY_TOTAL_FRAMES] = total_frames
    if speaker_frame_counts:
        out["speaker_stats"] = {
            "unique_speakers": sorted(list(speaker_frame_counts.keys())),
            "speaker_frame_counts": speaker_frame_counts
        }
    speaker_embeddings = data.get("speaker_embeddings")
    if isinstance(speaker_embeddings, dict) and speaker_embeddings:
        out["speaker_embeddings"] = speaker_embeddings
    return out


def stream_reduce_audio_json(input_path: Path, output_path: Path) -> Optional[Dict[str, Any]]:
    fps, total_frames, array_key = _extract_metadata_streaming(input_path)
    if not array_key:
        return None
        
    speaker_frame_counts = {}
    tmp_path = output_path.with_suffix(".tmp")
    max_frame_seen = 0
    speaker_embeddings = None
    
    # Try to extract speaker_embeddings from input file with a quick search
    try:
        with open(input_path, 'rb') as f:
            for prefix, event, value in ijson.parse(f, use_float=True):
                if prefix == 'speaker_embeddings' and event == 'start_map':
                    # Parse the whole embeddings dict
                    f.seek(0)
                    for k, v in ijson.kvitems(f, ''):
                        if k == 'speaker_embeddings':
                            speaker_embeddings = v
                            break
                    break
    except ijson.JSONError as e:
        logger.error(f"Format JSON invalide lors de l'extraction des embeddings de locuteurs : {e}")
    except StopIteration:
        logger.error("Fichier JSON tronqué lors de l'extraction des embeddings de locuteurs")
    except Exception as e:
        logger.error(f"Erreur inattendue lors de l'extraction des embeddings de locuteurs : {e}")

    
    with open(input_path, 'rb') as f_in, open(tmp_path, 'w', encoding='utf-8') as f_out:
        f_out.write(f'{{\n  "{KEY_FRAMES_ANALYSIS}": [\n')
        
        items = ijson.items(f_in, f"{array_key}.item", use_float=True)
        first = True
        
        for frame_data in items:
            if "audio_info" in frame_data and frame_data["audio_info"] is not None:
                new_audio_info = {
                    "is_speech_present": frame_data["audio_info"].get("is_speech_present", False),
                    "active_speaker_labels": frame_data["audio_info"].get("active_speaker_labels", [])
                }
                if frame_data["audio_info"].get("timecode_sec") is not None:
                    new_audio_info["timecode_sec"] = frame_data["audio_info"].get("timecode_sec")
                    
                frame_num = frame_data.get("frame")
                try:
                    if frame_num is not None: max_frame_seen = max(max_frame_seen, int(frame_num))
                except Exception: pass
                
                reduced_frame = {"frame": frame_num, "audio_info": new_audio_info}
                
                labels = new_audio_info.get("active_speaker_labels")
                if isinstance(labels, list):
                    for label in labels:
                        if isinstance(label, str) and label:
                            speaker_frame_counts[label] = speaker_frame_counts.get(label, 0) + 1
                            
                if not first: f_out.write(',\n')
                first = False
                json.dump(reduced_frame, f_out, indent=4, ensure_ascii=False)
                
        f_out.write('\n  ]')
        
        if total_frames is None and max_frame_seen > 0:
            total_frames = max_frame_seen
            
        if fps is not None:
            f_out.write(f',\n  "{KEY_FPS}": {fps}')
        if total_frames is not None:
            f_out.write(f',\n  "{KEY_TOTAL_FRAMES}": {total_frames}')
            
        if speaker_frame_counts:
            f_out.write(',\n  "speaker_stats": ')
            json.dump({
                "unique_speakers": sorted(list(speaker_frame_counts.keys())),
                "speaker_frame_counts": speaker_frame_counts
            }, f_out, indent=4, ensure_ascii=False)
            
        if isinstance(speaker_embeddings, dict) and speaker_embeddings:
            f_out.write(',\n  "speaker_embeddings": ')
            json.dump(speaker_embeddings, f_out, indent=4, ensure_ascii=False)
            
        f_out.write('\n}\n')
        
    os.replace(tmp_path, output_path)
    return {KEY_FPS: fps, KEY_TOTAL_FRAMES: total_frames}


def _compute_temporal_alignment(
    reduced_tracking: Dict[str, Any],
    reduced_audio: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not reduced_audio:
        return None

    v_total = reduced_tracking.get(KEY_TOTAL_FRAMES)
    a_total = reduced_audio.get(KEY_TOTAL_FRAMES)
    v_fps = reduced_tracking.get(KEY_FPS)
    a_fps = reduced_audio.get(KEY_FPS)

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

def _reduced_tracking_needs_enrichment_streaming(input_path: Path) -> bool:
    fps, total_frames, array_key = _extract_metadata_streaming(input_path)
    if not array_key:
        return False
        
    try:
        with open(input_path, 'rb') as f:
            items = ijson.items(f, f"{array_key}.item", use_float=True)
            for i, frame in enumerate(items):
                if i >= _ENRICHMENT_SAMPLE_MAX_FRAMES:
                    break
                if isinstance(frame, dict):
                    tracked = frame.get(KEY_TRACKED_OBJECTS)
                    if isinstance(tracked, list):
                        for obj in tracked[:_ENRICHMENT_SAMPLE_MAX_OBJECTS_PER_FRAME]:
                            if isinstance(obj, dict):
                                for key in _TRACKING_ENRICH_FIELDS:
                                    if obj.get(key) is None:
                                        return True
    except ijson.JSONError as e:
        logger.error(f"Format JSON invalide lors du test d'enrichissement pour {input_path.name}: {e}")
    except StopIteration:
        logger.error(f"Fichier JSON tronqué lors du test d'enrichissement pour {input_path.name}")
    except Exception as e:
        logger.error(f"Erreur inattendue lors du test d'enrichissement pour {input_path.name}: {e}")
    return False

def _reduced_tracking_needs_enrichment(reduced_tracking: Dict[str, Any]) -> bool:
    frames = reduced_tracking.get(KEY_FRAMES_ANALYSIS)
    if not isinstance(frames, list) or not frames:
        return False

    sampled_frames = frames[:_ENRICHMENT_SAMPLE_MAX_FRAMES]
    for frame in sampled_frames:
        if not isinstance(frame, dict): continue
        tracked = frame.get(KEY_TRACKED_OBJECTS)
        if not isinstance(tracked, list) or not tracked: continue
        sampled_objs = tracked[:_ENRICHMENT_SAMPLE_MAX_OBJECTS_PER_FRAME]
        for obj in sampled_objs:
            if not isinstance(obj, dict): continue
            for key in _TRACKING_ENRICH_FIELDS:
                if key not in obj or obj.get(key) is None:
                    return True
    return False

def _index_reduced_tracking_by_frame_and_id(reduced_tracking: Dict[str, Any]) -> Dict[int, Dict[str, Dict[str, Any]]]:
    frames = reduced_tracking.get(KEY_FRAMES_ANALYSIS)
    if not isinstance(frames, list):
        return {}
    index: Dict[int, Dict[str, Dict[str, Any]]] = {}
    for frame in frames:
        if not isinstance(frame, dict): continue
        frame_num = frame.get("frame")
        try: frame_i = int(frame_num)
        except Exception: continue
        tracked = frame.get(KEY_TRACKED_OBJECTS)
        if not isinstance(tracked, list): continue
        frame_map: Dict[str, Dict[str, Any]] = {}
        for obj in tracked:
            if not isinstance(obj, dict): continue
            obj_id = obj.get("id")
            if not isinstance(obj_id, str) or not obj_id: continue
            frame_map[obj_id] = obj
        if frame_map:
            index[frame_i] = frame_map
    return index

def _merge_reduced_tracking(
    base_tracking: Dict[str, Any],
    supplemental_tracking: Dict[str, Any],
) -> Dict[str, Any]:
    supplemental_index = _index_reduced_tracking_by_frame_and_id(supplemental_tracking)
    frames = base_tracking.get(KEY_FRAMES_ANALYSIS)
    if not isinstance(frames, list) or not supplemental_index:
        return base_tracking

    for frame in frames:
        if not isinstance(frame, dict): continue
        frame_num = frame.get("frame")
        try: frame_i = int(frame_num)
        except Exception: continue
        supp_frame = supplemental_index.get(frame_i)
        if not supp_frame: continue
        tracked = frame.get(KEY_TRACKED_OBJECTS)
        if not isinstance(tracked, list): continue

        for obj in tracked:
            if not isinstance(obj, dict): continue
            obj_id = obj.get("id")
            if not isinstance(obj_id, str) or not obj_id: continue
            supp_obj = supp_frame.get(obj_id)
            if not supp_obj: continue

            for key in _TRACKING_ENRICH_FIELDS:
                if (key not in obj) or (obj.get(key) is None):
                    if supp_obj.get(key) is not None:
                        obj[key] = supp_obj.get(key)

            base_speakers = obj.get(KEY_ACTIVE_SPEAKERS)
            supp_speakers = supp_obj.get(KEY_ACTIVE_SPEAKERS)
            if (base_speakers is None or base_speakers == []) and isinstance(supp_speakers, list) and supp_speakers:
                obj[KEY_ACTIVE_SPEAKERS] = supp_speakers

    base_total = base_tracking.get(KEY_TOTAL_FRAMES)
    supp_total = supplemental_tracking.get(KEY_TOTAL_FRAMES)
    try: base_total_i = int(base_total) if base_total is not None else None
    except Exception: base_total_i = None
    try: supp_total_i = int(supp_total) if supp_total is not None else None
    except Exception: supp_total_i = None

    if base_total_i is None and supp_total_i is not None:
        base_tracking[KEY_TOTAL_FRAMES] = supp_total_i
    elif base_total_i is not None and supp_total_i is not None:
        base_tracking[KEY_TOTAL_FRAMES] = max(base_total_i, supp_total_i)

    if base_tracking.get(KEY_FPS) is None and supplemental_tracking.get(KEY_FPS) is not None:
        base_tracking[KEY_FPS] = supplemental_tracking.get(KEY_FPS)

    return base_tracking

def process_directory(base_path: str, keyword: str = "Camille"):
    base = Path(base_path)
    logger.info(f"Démarrage du scan dans : {base}")
    if not base.is_dir():
        logger.error(f"Erreur : Le répertoire de base '{base_path}' n'existe pas.")
        return

    project_folders = [d.name for d in base.iterdir() if d.is_dir() and keyword in d.name]
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

        video_files = [p for p in docs_path.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS]
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

            logger.info("  - Cible: %s | tracking_in=%s | tracking_out=%s | audio=%s",
                        video_path.name, tracking_in.name, tracking_out.name if tracking_out else "(none)", audio_path.name)
            print(f"INTERNAL_PROGRESS: {v_idx}/{len(video_files)} items ({int(round((v_idx / float(len(video_files))) * 100))}%) - {video_path.name}")

            try:
                # 1. Stream reduce audio
                audio_meta = None
                if audio_path.exists():
                    audio_meta = stream_reduce_audio_json(audio_path, audio_path)
                    if audio_meta:
                        logger.info("    - Audio réduit avec succès (en streaming): %s", audio_path.name)
                    else:
                        logger.warning(f"    - Audio JSON ignoré (schéma inattendu): {audio_path}")
                        
                # 2. Check enrichment need
                needs_enrichment = False
                if tracking_fallback and tracking_fallback.exists() and tracking_in.resolve() != tracking_fallback.resolve():
                    needs_enrichment = _reduced_tracking_needs_enrichment_streaming(tracking_in)
                    
                legacy_path = tracking_fallback if needs_enrichment else None
                
                # 3. Stream reduce video
                tracking_meta = stream_reduce_video_json(tracking_in, tracking_out, legacy_path, audio_meta)
                if tracking_meta:
                    logger.info("    - Tracking réduit avec succès (en streaming): %s", tracking_out.name)
                else:
                    logger.warning(f"    - Tracking JSON ignoré (schéma inattendu en streaming): {tracking_in}")

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

    if args.work_dir:
        work_dir = args.work_dir
    else:
        base_dir = args.base_dir if args.base_dir else os.getcwd()
        work_dir = os.path.join(base_dir, 'projets_extraits')

    setup_logging(args.log_dir)

    try:
        if not os.path.isdir(work_dir):
            logger.warning(f"Répertoire de travail introuvable: {work_dir}")
            print(f"TOTAL_JSON_TO_REDUCE: 0")
            sys.exit(0)
        projects = [d for d in os.listdir(work_dir) if os.path.isdir(os.path.join(work_dir, d)) and args.keyword in d]
        print(f"TOTAL_JSON_TO_REDUCE: {len(projects)}")
    except Exception:
        print("TOTAL_JSON_TO_REDUCE: 0")

    process_directory(work_dir, keyword=args.keyword)

if __name__ == "__main__":
    main()
