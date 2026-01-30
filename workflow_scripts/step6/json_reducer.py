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
    return out


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
