#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit des pistes d'objets du pipeline STEP4 → STEP6 → recentrage EffectCraft.

Trois usages :

1. `--json-dir` : inventaire des libellés d'objets des JSON STEP4 (histogramme des
   indices de classe, taux de frames avec visage, intermittence du détecteur de
   visage — utile pour dimensionner l'hystérésis du détecteur d'objets).

2. `--ae` : comptage des pistes `object_detector` / `person` réellement présentes
   dans un `_ae.json` de STEP6 (0 avant le correctif de mapping, > 0 après), et
   vérification qu'aucun libellé `class_N` mort ou hors plage n'a survécu.

3. `--segments <_ae.json> --csv <csv>` : reproduction du cœur de la sélection du
   panneau EffectCraft (`pickBestObjectInRange`) pour chiffrer l'apport au
   recentrage : nombre de segments CSV disposant d'une piste candidate, et
   comparaison avant/après via `--compare`.

La sélection reproduite est celle du panneau : par segment CSV, agrégation par
`id`, score = `présence × (1 + clamp01(confiance) × 0.35)`, départage par surface
moyenne de bbox, puis `center_x` = moyenne des `centroid_x` de la piste retenue.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

CONFIDENCE_WEIGHT = 0.35
COCO_INDEX_HINT = re.compile(r"^class_(\d+)$")

# Indices morts de l'espace COCO du modèle EfficientDet (cf. utils/step4_tpu_detections.py).
DEAD_CLASS_INDICES = frozenset({11, 25, 28, 29, 44, 65, 67, 68, 70, 82})


def parse_timecode(value: str) -> Optional[float]:
    """Convertit `HH:MM:SS,mmm` (ou `MM:SS.mmm`, ou des secondes) en secondes."""
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        parts = text.split(":")
        if len(parts) == 1:
            return float(parts[0])
        seconds = 0.0
        for part in parts:
            seconds = seconds * 60.0 + float(part)
        return seconds
    except ValueError:
        return None


def split_csv_line(line: str) -> List[str]:
    """Découpe une ligne CSV en respectant les champs entre guillemets."""
    fields: List[str] = []
    current: List[str] = []
    in_quotes = False
    for char in line:
        if char == '"':
            in_quotes = not in_quotes
        elif char == "," and not in_quotes:
            fields.append("".join(current))
            current = []
        else:
            current.append(char)
    fields.append("".join(current))
    return fields


def parse_csv_segments(content: str) -> List[Dict[str, Any]]:
    """Segments du CSV : colonne 0 = numéro, 1 = début, 2 = fin (mêmes règles que le panneau)."""
    segments: List[Dict[str, Any]] = []
    lines = re.split(r"\r\n|\r|\n", content)
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        columns = split_csv_line(line)
        if len(columns) < 3:
            continue
        start = parse_timecode(columns[1])
        end = parse_timecode(columns[2])
        if start is not None and end is not None and start >= 0 and end > start:
            segments.append({"num": columns[0].strip(), "start": start, "end": end})
    return segments


def load_payload(path: Path) -> Dict[str, Any]:
    """Charge un JSON (STEP4 `{frames: [...]}` ou STEP6 `{dataByFrame: {...}}`)."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"JSON illisible ({path}): {exc}")


def index_ae_frames(payload: Dict[str, Any]) -> Dict[int, List[Dict[str, Any]]]:
    """Indexe `dataByFrame` (STEP6) en {numéro de frame: [objets]}."""
    data = payload.get("dataByFrame") or {}
    indexed: Dict[int, List[Dict[str, Any]]] = {}
    for key, objects in data.items():
        try:
            frame = int(key)
        except (TypeError, ValueError):
            continue
        indexed[frame] = list(objects or [])
    return indexed


def segment_frame_range(segment: Dict[str, Any], fps: float) -> Tuple[int, int]:
    """Plage de frames d'un segment (règles du panneau : floor(début×fps) .. ceil(fin×fps))."""
    import math

    return int(math.floor(segment["start"] * fps)), int(math.ceil(segment["end"] * fps))


def select_best_in_segment(
    indexed: Dict[int, List[Dict[str, Any]]],
    segment: Dict[str, Any],
    fps: float,
    confidence_weight: float = CONFIDENCE_WEIGHT,
) -> Optional[Dict[str, Any]]:
    """Piste retenue par le panneau pour un segment (None si aucune candidate)."""
    first, last = segment_frame_range(segment, fps)
    tracks: Dict[str, Dict[str, List[float]]] = {}
    for frame in range(first, last + 1):
        for obj in indexed.get(frame, []):
            obj_id = obj.get("id")
            if not obj_id:
                continue
            try:
                center = float(obj.get("centroid_x"))
            except (TypeError, ValueError):
                continue
            track = tracks.setdefault(str(obj_id), {
                "x": [], "conf": [], "surface": [], "source": obj.get("source"), "label": obj.get("label"),
            })
            track["x"].append(center)
            track["conf"].append(float(obj.get("confidence") or 0.0))
            surface = obj.get("bbox_surface")
            if surface is None:
                surface = float(obj.get("bbox_width") or 0.0) * float(obj.get("bbox_height") or 0.0)
            track["surface"].append(float(surface or 0.0))

    if not tracks:
        return None

    best: Optional[Dict[str, Any]] = None
    best_key: Optional[Tuple[float, float]] = None
    for obj_id, track in tracks.items():
        presence = float(len(track["x"]))
        average_conf = sum(track["conf"]) / len(track["conf"]) if track["conf"] else 0.0
        clamped = min(1.0, max(0.0, average_conf))
        score = presence * (1.0 + clamped * confidence_weight)
        average_surface = sum(track["surface"]) / len(track["surface"]) if track["surface"] else 0.0
        key = (score, average_surface)
        if best_key is None or key > best_key:
            best_key = key
            best = {
                "id": obj_id,
                "center_x": sum(track["x"]) / len(track["x"]),
                "presence": int(presence),
                "confidence": average_conf,
                "surface": average_surface,
                "source": track["source"],
                "label": track["label"],
            }
    return best


def audit_segments(ae_path: Path, csv_path: Path, fps: Optional[float] = None) -> Dict[str, Any]:
    """Sélection par segment + inventaire des pistes disponibles."""
    payload = load_payload(ae_path)
    indexed = index_ae_frames(payload)
    frame_rate = float(fps or payload.get("fps") or 25.0)
    segments = parse_csv_segments(Path(csv_path).read_text(encoding="utf-8"))

    selections: List[Dict[str, Any]] = []
    with_candidate = 0
    sources: Dict[str, int] = {}
    for segment in segments:
        best = select_best_in_segment(indexed, segment, frame_rate)
        if best is not None:
            with_candidate += 1
            sources[str(best["source"])] = sources.get(str(best["source"]), 0) + 1
        selections.append({"num": segment["num"], "start": segment["start"], "end": segment["end"], "best": best})

    object_frames = sum(
        1 for objects in indexed.values()
        if any(obj.get("source") == "object_detector" for obj in objects)
    )
    person_objects = sum(
        1 for objects in indexed.values()
        for obj in objects
        if obj.get("source") == "object_detector" and obj.get("label") == "person"
    )
    stale = sorted({
        int(match.group(1)) for objects in indexed.values() for obj in objects
        if (match := COCO_INDEX_HINT.match(str(obj.get("label") or "")))
    })

    return {
        "ae": str(ae_path),
        "frames_indexed": len(indexed),
        "segments": len(segments),
        "segments_with_candidate": with_candidate,
        "segments_without_candidate": len(segments) - with_candidate,
        "coverage_pct": (100.0 * with_candidate / len(segments)) if segments else 0.0,
        "winning_sources": sources,
        "frames_with_object_track": object_frames,
        "person_objects_total": person_objects,
        "stale_class_labels": stale,
        "selections": selections,
    }


def compare_selections(before: Dict[str, Any], after: Dict[str, Any], tolerance_px: float = 5.0) -> Dict[str, Any]:
    """Métriques V1/V2 entre deux audits de segments."""
    before_map = {sel["num"]: sel for sel in before.get("selections", [])}
    changed_center: List[Tuple[str, float]] = []
    gained_candidate = 0
    face_to_object = 0
    for selection in after.get("selections", []):
        previous = before_map.get(selection["num"], {})
        old_best = previous.get("best")
        new_best = selection.get("best")
        if not old_best and new_best:
            gained_candidate += 1
            continue
        if old_best and new_best:
            delta = abs(float(new_best["center_x"]) - float(old_best["center_x"]))
            if delta > tolerance_px or str(old_best["id"]) != str(new_best["id"]):
                changed_center.append((selection["num"], delta))
            if str(old_best.get("source")) == "face_landmarker" and str(new_best.get("source")) == "object_detector":
                face_to_object += 1

    deltas = sorted(delta for _, delta in changed_center)
    median = deltas[len(deltas) // 2] if deltas else 0.0
    return {
        "segments_before": before.get("segments", 0),
        "segments_after": after.get("segments", 0),
        "segments_with_candidate_before": before.get("segments_with_candidate", 0),
        "segments_with_candidate_after": after.get("segments_with_candidate", 0),
        "coverage_pct_before": before.get("coverage_pct", 0.0),
        "coverage_pct_after": after.get("coverage_pct", 0.0),
        "segments_gaining_a_candidate": gained_candidate,
        "segments_with_changed_center": len(changed_center),
        "median_center_shift_px": median,
        "segments_switching_face_to_object": face_to_object,
    }


def audit_step4_labels(json_path: Path) -> Dict[str, Any]:
    """Inventaire des libellés d'objets d'un JSON STEP4 + intermittence du visage."""
    payload = load_payload(json_path)
    frames = payload.get("frames") or []
    label_counts: Dict[str, int] = {}
    face_frames = 0
    object_frames = 0
    runs: List[int] = []
    current_run = 0
    for entry in frames:
        objects = entry.get("tracked_objects") or []
        has_face = any(obj.get("source") == "face_landmarker" for obj in objects)
        has_object = any(obj.get("source") == "object_detector" for obj in objects)
        if has_face:
            face_frames += 1
            if current_run:
                runs.append(current_run)
                current_run = 0
        else:
            current_run += 1
        if has_object:
            object_frames += 1
            for obj in objects:
                if obj.get("source") == "object_detector":
                    label = str(obj.get("label") or "")
                    label_counts[label] = label_counts.get(label, 0) + 1
    if current_run:
        runs.append(current_run)

    total = len(frames)
    short_runs = [length for length in runs if length < 25]
    return {
        "video": Path(json_path).name,
        "frames": total,
        "face_frames": face_frames,
        "face_rate_pct": (100.0 * face_frames / total) if total else 0.0,
        "object_frames": object_frames,
        "object_rate_pct": (100.0 * object_frames / total) if total else 0.0,
        "label_counts": dict(sorted(label_counts.items(), key=lambda item: -item[1])),
        "faceless_runs": len(runs),
        "faceless_run_max": max(runs) if runs else 0,
        # Plages sans visage trop courtes pour déclencher le détecteur d'objets
        # (STEP4_TPU_OBJECT_DETECTION_MIN_MISSING) : aucune piste d'objet n'y est produite.
        "faceless_runs_under_threshold": len(short_runs),
        "frames_in_short_runs": sum(short_runs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit des pistes d'objets STEP4 → recentrage EffectCraft")
    parser.add_argument("--json-dir", type=Path, default=None, help="Dossier de JSON STEP4 à inventorier")
    parser.add_argument("--ae", type=Path, default=None, help="JSON `_ae.json` de STEP6 à inspecter")
    parser.add_argument("--segments", type=Path, default=None, help="`_ae.json` pour l'analyse par segment CSV")
    parser.add_argument("--csv", type=Path, default=None, help="CSV des segments (colonnes 1/2 = début/fin)")
    parser.add_argument("--fps", type=float, default=None, help="Cadence si absente du JSON (défaut 25)")
    parser.add_argument("--compare", type=Path, default=None, help="Audit `--segments` antérieur à comparer")
    parser.add_argument("--tolerance-px", type=float, default=5.0, help="Seuil de variation retenue pour V2")
    parser.add_argument("--out", type=Path, default=None, help="Écrit le résultat JSON à ce chemin")
    args = parser.parse_args()

    if not any([args.json_dir, args.ae, args.segments]):
        parser.error("Préciser au moins --json-dir, --ae ou --segments")

    result: Dict[str, Any] = {}

    if args.json_dir:
        videos = []
        for path in sorted(Path(args.json_dir).rglob("*.json")):
            if path.name.endswith("_audio.json") or path.name.endswith("_tracking.json") or path.name.endswith("_ae.json"):
                continue
            try:
                videos.append(audit_step4_labels(path))
            except SystemExit:
                continue
        result["step4"] = videos
        print(f"{'vidéo':<50} {'frames':>7} {'visage%':>8} {'objet%':>7} {'plages<25':>10} {'frames sans piste':>18}  libellés")
        for video in videos:
            labels = ", ".join(f"{name}×{count}" for name, count in list(video["label_counts"].items())[:6])
            print(f"{video['video'][:48]:<50} {video['frames']:>7} {video['face_rate_pct']:>7.1f}% "
                  f"{video['object_rate_pct']:>6.1f}% {video['faceless_runs_under_threshold']:>10} "
                  f"{video['frames_in_short_runs']:>18}  {labels}")
        if videos:
            total_frames = sum(video["frames"] for video in videos)
            lost = sum(video["frames_in_short_runs"] for video in videos)
            print(f"{'TOTAL':<50} {total_frames:>7} "
                  f"{sum(video['face_frames'] for video in videos) / total_frames * 100:>7.1f}% "
                  f"{sum(video['object_frames'] for video in videos) / total_frames * 100:>6.1f}% "
                  f"{sum(video['faceless_runs_under_threshold'] for video in videos):>10} {lost:>18}")
            print(f"Frames sans visage trop courtes pour le détecteur d'objets (< 25) : "
                  f"{lost}/{total_frames} ({100.0 * lost / total_frames:.1f} %)")

    if args.ae:
        payload = load_payload(args.ae)
        indexed = index_ae_frames(payload)
        persons = sum(
            1 for objects in indexed.values() for obj in objects
            if obj.get("source") == "object_detector" and obj.get("label") == "person"
        )
        frames_with_person = sum(
            1 for objects in indexed.values()
            if any(obj.get("source") == "object_detector" and obj.get("label") == "person" for obj in objects)
        )
        stale = sorted({
            int(match.group(1)) for objects in indexed.values() for obj in objects
            if (match := COCO_INDEX_HINT.match(str(obj.get("label") or "")))
        })
        result["ae"] = {
            "path": str(args.ae),
            "frames": len(indexed),
            "person_objects": persons,
            "frames_with_person": frames_with_person,
            "stale_class_labels": stale,
        }
        print(f"\n{args.ae.name} : {len(indexed)} frames indexées, "
              f"{frames_with_person} frames avec une piste personne, {persons} objets personne")
        print(f"libellés `class_N` résiduels : {stale if stale else 'aucun'}")

    if args.segments:
        if args.csv is None:
            parser.error("--csv requis avec --segments")
        audit = audit_segments(args.segments, args.csv, args.fps)
        result["segments"] = audit
        print(f"\nSegments CSV            : {audit['segments']}")
        print(f"Segments avec candidat  : {audit['segments_with_candidate']} ({audit['coverage_pct']:.1f} %)")
        print(f"Sources gagnantes       : {audit['winning_sources']}")
        print(f"Frames avec piste objet : {audit['frames_with_object_track']}")
        print(f"Objets personne         : {audit['person_objects_total']}")
        print(f"Libellés `class_N`      : {audit['stale_class_labels'] if audit['stale_class_labels'] else 'aucun'}")
        if args.compare:
            previous = load_payload(args.compare).get("segments") or {}
            metrics = compare_selections(previous, audit, args.tolerance_px)
            result["compare"] = metrics
            print("\n--- Métriques de valeur (avant → après) ---")
            print(f"Couverture des segments : {metrics['coverage_pct_before']:.1f} % → {metrics['coverage_pct_after']:.1f} %")
            print(f"Segments gagnant un candidat   : {metrics['segments_gaining_a_candidate']}")
            print(f"Segments au centre modifié     : {metrics['segments_with_changed_center']} "
                  f"(|Δ| médian {metrics['median_center_shift_px']:.1f} px)")
            print(f"Segments basculés visage→objet : {metrics['segments_switching_face_to_object']}")

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nRésultat écrit : {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
