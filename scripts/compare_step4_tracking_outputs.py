#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comparateur de précision entre deux exécutions de la STEP4 tracking.

Compare deux répertoires de JSON produits par ``run_tracking_tpu.py`` (référence
gelée vs variante optimisée) et vérifie l'absence de perte de précision :

- accord de présence de visage, IoU des boîtes, dérive des centroïdes ;
- RMSE par coefficient ARKit (globale, sous-ensembles bouche/yeux) ;
- indice de jittering ``J_k`` (RMS de la dérivée seconde) sur les coefficients critiques ;
- accord du flag ``is_speaking`` et churn d'identités.

La lecture des JSON se fait en streaming (``ijson``) : les fichiers de tracking
font plusieurs mégaoctets et ne doivent pas être chargés en mémoire d'un bloc.

Le code retour est non nul si un seuil bloquant est franchi, ce qui permet
d'utiliser l'outil comme gate de validation d'une optimisation.

Exemple :
    python3 scripts/compare_step4_tracking_outputs.py \
        --ref scratch/bench_step4_tpu/*_baseline/outputs \
        --test scratch/bench_step4_tpu/*_fast2/outputs
"""

import argparse
import json
import math
import sys
from pathlib import Path

try:
    import ijson
    _HAS_IJSON = True
except ImportError:
    _HAS_IJSON = False

CRITICAL_COEFFICIENTS = (
    "jawOpen",
    "mouthSmileLeft",
    "mouthSmileRight",
    "eyeBlinkLeft",
    "eyeBlinkRight",
)

# Seuils par défaut (cf. contrats de validation des rapports d'optimisation TPU).
DEFAULT_THRESHOLDS = {
    "max_rmse": 0.035,
    "min_face_presence_agreement": 0.999,
    "min_speaking_agreement": 0.995,
    "min_iou_p5": 0.99,
    "max_centroid_p95_px": 3.0,
    "max_id_ratio": 1.10,
    "jitter_tolerance": 0.02,
    "min_object_match_ratio": 0.99,
}


def iter_frames(path: Path):
    """Itère les frames d'un JSON de tracking sans charger le fichier entier."""
    if _HAS_IJSON:
        with open(path, "rb") as file_obj:
            for frame in ijson.items(file_obj, "frames.item"):
                yield frame
        return

    with open(path, "r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)
    for frame in payload.get("frames", []):
        yield frame


def bbox_of(obj) -> tuple:
    xmin = obj.get("bbox_xmin")
    xmax = obj.get("bbox_xmax")
    ymin = obj.get("bbox_ymin")
    ymax = obj.get("bbox_ymax")
    if None in (xmin, xmax, ymin, ymax):
        return None
    return float(xmin), float(ymin), float(xmax), float(ymax)


def iou(box_a, box_b) -> float:
    if not box_a or not box_b:
        return float("nan")
    inter_x = max(0.0, min(box_a[2], box_b[2]) - max(box_a[0], box_b[0]))
    inter_y = max(0.0, min(box_a[3], box_b[3]) - max(box_a[1], box_b[1]))
    inter = inter_x * inter_y
    area_a = max(0.0, box_a[2] - box_a[0]) * max(0.0, box_a[3] - box_a[1])
    area_b = max(0.0, box_b[2] - box_b[0]) * max(0.0, box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else float("nan")


def percentile(values, fraction: float):
    """Percentile par interpolation linéaire (même définition que numpy.percentile)."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = fraction * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def ordered_objects(frame, faces_only: bool = False) -> list:
    objects = frame.get("tracked_objects") or []
    if faces_only:
        objects = [obj for obj in objects if obj.get("source") == "face_landmarker"]
    return sorted(objects, key=lambda obj: obj.get("centroid_x", 0))


def match_objects(ref_objects: list, test_objects: list, max_distance: float = 80.0):
    """Apparie les objets par plus proche centroïde (glouton, comme le tracker).

    L'appariement par index est trompeur dès qu'un des runs compte un objet de plus
    (visage détourné par une détection d'objet, piste expirée) : on compare ici les
    objets qui correspondent réellement, et on compte les autres séparément.
    """
    candidates = []
    for ref_index, ref_obj in enumerate(ref_objects):
        for test_index, test_obj in enumerate(test_objects):
            if None in (ref_obj.get("centroid_x"), ref_obj.get("centroid_y"),
                        test_obj.get("centroid_x"), test_obj.get("centroid_y")):
                continue
            dx = float(test_obj["centroid_x"]) - float(ref_obj["centroid_x"])
            dy = float(test_obj["centroid_y"]) - float(ref_obj["centroid_y"])
            distance = math.hypot(dx, dy)
            candidates.append((distance, ref_index, test_index))
    candidates.sort()

    matched_ref, matched_test, pairs = set(), set(), []
    for distance, ref_index, test_index in candidates:
        if distance > max_distance:
            break
        if ref_index in matched_ref or test_index in matched_test:
            continue
        matched_ref.add(ref_index)
        matched_test.add(test_index)
        pairs.append((ref_objects[ref_index], test_objects[test_index]))
    return pairs, len(ref_objects) - len(matched_ref), len(test_objects) - len(matched_test)


def compare_video(ref_path: Path, test_path: Path, faces_only: bool = False) -> dict:
    """Compare une vidéo : appariement par position (les sorties sont triées par centroid_x)."""
    coefficient_sq_error = {}
    coefficient_count = {}
    coefficient_names = set()
    critical_series = {name: {"ref": [], "test": []} for name in CRITICAL_COEFFICIENTS}
    ious = []
    centroid_distances = []
    frames_total = 0
    presence_ref = 0
    presence_test = 0
    presence_agreement = 0
    speaking_total = 0
    speaking_agreement = 0
    ref_ids = set()
    test_ids = set()
    mismatched_counts = 0
    matched_total = 0
    unmatched_ref_total = 0
    unmatched_test_total = 0

    ref_frames = iter_frames(ref_path)
    test_frames = iter_frames(test_path)

    while True:
        ref_frame = next(ref_frames, None)
        test_frame = next(test_frames, None)
        if ref_frame is None or test_frame is None:
            break

        frames_total += 1
        ref_objects = ordered_objects(ref_frame, faces_only)
        test_objects = ordered_objects(test_frame, faces_only)

        has_ref = bool(ref_objects)
        has_test = bool(test_objects)
        presence_ref += int(has_ref)
        presence_test += int(has_test)
        presence_agreement += int(has_ref == has_test)

        if len(ref_objects) != len(test_objects):
            mismatched_counts += 1

        for obj in ref_objects:
            if obj.get("id"):
                ref_ids.add(obj["id"])
        for obj in test_objects:
            if obj.get("id"):
                test_ids.add(obj["id"])

        pairs, unmatched_ref, unmatched_test = match_objects(ref_objects, test_objects)
        unmatched_ref_total += unmatched_ref
        unmatched_test_total += unmatched_test
        matched_total += len(pairs)

        if pairs:
            first_ref, first_test = pairs[0]
            for coefficient in CRITICAL_COEFFICIENTS:
                value = (first_ref.get("blendshapes") or {}).get(coefficient)
                other = (first_test.get("blendshapes") or {}).get(coefficient)
                if value is not None and other is not None:
                    critical_series[coefficient]["ref"].append(float(value))
                    critical_series[coefficient]["test"].append(float(other))

        for ref_obj, test_obj in pairs:
            ref_box, test_box = bbox_of(ref_obj), bbox_of(test_obj)
            value = iou(ref_box, test_box)
            if value is not None and not math.isnan(value):
                ious.append(value)

            if None not in (ref_obj.get("centroid_x"), ref_obj.get("centroid_y"),
                            test_obj.get("centroid_x"), test_obj.get("centroid_y")):
                dx = float(test_obj["centroid_x"]) - float(ref_obj["centroid_x"])
                dy = float(test_obj["centroid_y"]) - float(ref_obj["centroid_y"])
                centroid_distances.append(math.hypot(dx, dy))

            ref_blendshapes = ref_obj.get("blendshapes") or {}
            test_blendshapes = test_obj.get("blendshapes") or {}
            if ref_blendshapes and test_blendshapes:
                for name in set(ref_blendshapes) & set(test_blendshapes):
                    if name.startswith("_"):
                        continue
                    delta = float(test_blendshapes[name]) - float(ref_blendshapes[name])
                    coefficient_sq_error[name] = coefficient_sq_error.get(name, 0.0) + delta * delta
                    coefficient_count[name] = coefficient_count.get(name, 0) + 1
                    coefficient_names.add(name)

            if "is_speaking" in ref_obj and "is_speaking" in test_obj:
                speaking_total += 1
                speaking_agreement += int(bool(ref_obj["is_speaking"]) == bool(test_obj["is_speaking"]))

    per_coefficient_rmse = {
        name: math.sqrt(coefficient_sq_error[name] / coefficient_count[name])
        for name in coefficient_names if coefficient_count.get(name)
    }

    mouth_rmse = [value for name, value in per_coefficient_rmse.items() if name.startswith("mouth")]
    eye_rmse = [value for name, value in per_coefficient_rmse.items() if name.startswith("eye")]

    jitter = {}
    for name, series in critical_series.items():
        ref_series, test_series = series["ref"], series["test"]
        if len(ref_series) < 4:
            continue
        jitter[name] = {
            "ref": round(second_difference_rms(ref_series), 6),
            "test": round(second_difference_rms(test_series), 6),
        }

    return {
        "video": ref_path.stem,
        "frames_compared": frames_total,
        "frame_count_delta": None,
        "objects_count_mismatch_frames": mismatched_counts,
        "objects": {
            "matched": matched_total,
            "unmatched_ref": unmatched_ref_total,
            "unmatched_test": unmatched_test_total,
            "matched_ratio": (
                round(matched_total / (matched_total + unmatched_ref_total), 6)
                if (matched_total + unmatched_ref_total) else None
            ),
        },
        "face_presence": {
            "ref_rate": round(presence_ref / frames_total, 6) if frames_total else None,
            "test_rate": round(presence_test / frames_total, 6) if frames_total else None,
            "agreement": round(presence_agreement / frames_total, 6) if frames_total else None,
        },
        "bbox_iou": {
            "count": len(ious),
            "p5": round(percentile(ious, 0.05), 6) if ious else None,
            "p50": round(percentile(ious, 0.5), 6) if ious else None,
        },
        "centroid_distance_px": {
            "count": len(centroid_distances),
            "p50": round(percentile(centroid_distances, 0.5), 4) if centroid_distances else None,
            "p95": round(percentile(centroid_distances, 0.95), 4) if centroid_distances else None,
            "max": round(max(centroid_distances), 4) if centroid_distances else None,
        },
        "blendshapes": {
            "coefficients": len(per_coefficient_rmse),
            "max_rmse": round(max(per_coefficient_rmse.values()), 6) if per_coefficient_rmse else None,
            "max_rmse_coefficient": (
                max(per_coefficient_rmse, key=per_coefficient_rmse.get) if per_coefficient_rmse else None
            ),
            "mouth_max_rmse": round(max(mouth_rmse), 6) if mouth_rmse else None,
            "eye_max_rmse": round(max(eye_rmse), 6) if eye_rmse else None,
            "critical_rmse": {
                name: round(per_coefficient_rmse[name], 6)
                for name in CRITICAL_COEFFICIENTS if name in per_coefficient_rmse
            },
        },
        "speaking": {
            "compared": speaking_total,
            "agreement": round(speaking_agreement / speaking_total, 6) if speaking_total else None,
        },
        "identities": {
            "ref_ids": len(ref_ids),
            "test_ids": len(test_ids),
            "ratio": round(len(test_ids) / len(ref_ids), 4) if ref_ids else None,
        },
        "jitter": jitter,
    }


def second_difference_rms(series) -> float:
    """RMS de la dérivée seconde discrète (indice de jittering J_k)."""
    if len(series) < 3:
        return 0.0
    total = 0.0
    for index in range(1, len(series) - 1):
        second = series[index + 1] - 2.0 * series[index] + series[index - 1]
        total += second * second
    return math.sqrt(total / (len(series) - 2))


def evaluate_thresholds(summary: dict, thresholds: dict) -> list:
    """Retourne la liste des seuils bloquants franchis."""
    failures = []
    videos = summary["videos"]

    worst_rmse = max((video["blendshapes"]["max_rmse"] or 0.0) for video in videos)
    if worst_rmse >= thresholds["max_rmse"]:
        failures.append(f"max_k RMSE {worst_rmse:.4f} >= {thresholds['max_rmse']}")

    worst_presence = min((video["face_presence"]["agreement"] or 1.0) for video in videos)
    if worst_presence < thresholds["min_face_presence_agreement"]:
        failures.append(
            f"accord de présence de visage {worst_presence:.4f} < {thresholds['min_face_presence_agreement']}"
        )

    iou_values = [video["bbox_iou"]["p5"] for video in videos if video["bbox_iou"]["p5"] is not None]
    if iou_values:
        worst_iou = min(iou_values)
        if worst_iou < thresholds["min_iou_p5"]:
            failures.append(f"IoU P5 {worst_iou:.4f} < {thresholds['min_iou_p5']}")

    centroid_values = [
        video["centroid_distance_px"]["p95"]
        for video in videos if video["centroid_distance_px"]["p95"] is not None
    ]
    if centroid_values:
        worst_centroid = max(centroid_values)
        if worst_centroid > thresholds["max_centroid_p95_px"]:
            failures.append(
                f"dérive centroïde P95 {worst_centroid:.3f} px > {thresholds['max_centroid_p95_px']} px"
            )

    speaking_values = [
        video["speaking"]["agreement"]
        for video in videos if video["speaking"]["agreement"] is not None
    ]
    if speaking_values:
        worst_speaking = min(speaking_values)
        if worst_speaking < thresholds["min_speaking_agreement"]:
            failures.append(
                f"accord is_speaking {worst_speaking:.4f} < {thresholds['min_speaking_agreement']}"
            )

    id_ratios = [video["identities"]["ratio"] for video in videos if video["identities"]["ratio"]]
    if id_ratios:
        worst_ratio = max(id_ratios)
        if worst_ratio > thresholds["max_id_ratio"]:
            failures.append(f"churn d'identités x{worst_ratio:.3f} > x{thresholds['max_id_ratio']}")

    match_ratios = [
        video["objects"]["matched_ratio"]
        for video in videos if video.get("objects", {}).get("matched_ratio") is not None
    ]
    if match_ratios:
        worst_match = min(match_ratios)
        if worst_match < thresholds["min_object_match_ratio"]:
            failures.append(
                f"appariement d'objets {worst_match:.4f} < {thresholds['min_object_match_ratio']}"
            )

    tolerance = thresholds["jitter_tolerance"]
    for video in videos:
        for name, values in (video["jitter"] or {}).items():
            allowed = values["ref"] * (1.0 + tolerance) + 1e-9
            if values["test"] > allowed:
                failures.append(
                    f"{video['video']}: jitter {name} {values['test']:.6f} > {values['ref']:.6f} (+{tolerance:.0%})"
                )

    return failures


def render_markdown(summary: dict, failures: list) -> str:
    lines = [
        "# Comparaison de précision STEP4 (référence vs variante)",
        "",
        f"- Référence : `{summary['ref']}`",
        f"- Variante : `{summary['test']}`",
        f"- Vidéos comparées : {len(summary['videos'])}",
        f"- Périmètre : {'visages uniquement' if summary.get('faces_only') else 'tous les objets suivis'}",
        "",
        "| vidéo | frames | accord présence | appariement | IoU P5 | centro P95 (px) | max RMSE | coeff | bouche RMSE | yeux RMSE | is_speaking | ids |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for video in summary["videos"]:
        lines.append(
            f"| {video['video']} | {video['frames_compared']} | {video['face_presence']['agreement']} | "
            f"{(video.get('objects') or {}).get('matched_ratio')} | "
            f"{video['bbox_iou']['p5']} | {video['centroid_distance_px']['p95']} | "
            f"{video['blendshapes']['max_rmse']} | {video['blendshapes']['max_rmse_coefficient']} | "
            f"{video['blendshapes']['mouth_max_rmse']} | {video['blendshapes']['eye_max_rmse']} | "
            f"{video['speaking']['agreement']} | {video['identities']['ref_ids']}→{video['identities']['test_ids']} |"
        )

    lines += ["", "## Jitter (RMS de la dérivée seconde)", "", "| vidéo | coefficient | ref | test |", "|---|---|---|---|"]
    for video in summary["videos"]:
        for name, values in (video["jitter"] or {}).items():
            lines.append(f"| {video['video']} | {name} | {values['ref']} | {values['test']} |")

    lines += ["", "## Verdict", ""]
    if failures:
        lines.append(f"**ÉCHEC** — {len(failures)} seuil(s) franchi(s) :")
        lines += [f"- {failure}" for failure in failures]
    else:
        lines.append("**OK** — aucun seuil de précision franchi.")
    lines.append("")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Comparaison de précision entre deux runs STEP4 tracking")
    parser.add_argument("--ref", required=True, help="Répertoire de référence (JSON gelés)")
    parser.add_argument("--test", required=True, help="Répertoire de la variante")
    parser.add_argument("--videos", nargs="*", default=None, help="Filtres sur le nom de fichier")
    parser.add_argument("--faces-only", action="store_true", help="Comparer uniquement les objets issus du détecteur de visage")
    parser.add_argument("--out", default=None, help="Rapport JSON de sortie")
    parser.add_argument("--markdown", default=None, help="Rapport Markdown de sortie")
    parser.add_argument("--max-rmse", type=float, default=DEFAULT_THRESHOLDS["max_rmse"])
    parser.add_argument("--min-iou-p5", type=float, default=DEFAULT_THRESHOLDS["min_iou_p5"])
    parser.add_argument("--max-centroid-p95", type=float, default=DEFAULT_THRESHOLDS["max_centroid_p95_px"])
    parser.add_argument("--min-speaking-agreement", type=float, default=DEFAULT_THRESHOLDS["min_speaking_agreement"])
    parser.add_argument("--max-id-ratio", type=float, default=DEFAULT_THRESHOLDS["max_id_ratio"])
    parser.add_argument("--jitter-tolerance", type=float, default=DEFAULT_THRESHOLDS["jitter_tolerance"])
    parser.add_argument("--min-face-presence", type=float, default=DEFAULT_THRESHOLDS["min_face_presence_agreement"])
    parser.add_argument("--min-object-match-ratio", type=float, default=DEFAULT_THRESHOLDS["min_object_match_ratio"])
    args = parser.parse_args()

    ref_dir = Path(args.ref)
    test_dir = Path(args.test)
    if not ref_dir.is_dir() or not test_dir.is_dir():
        parser.error("--ref et --test doivent être des répertoires")

    thresholds = {
        "max_rmse": args.max_rmse,
        "min_face_presence_agreement": args.min_face_presence,
        "min_speaking_agreement": args.min_speaking_agreement,
        "min_iou_p5": args.min_iou_p5,
        "max_centroid_p95_px": args.max_centroid_p95,
        "max_id_ratio": args.max_id_ratio,
        "jitter_tolerance": args.jitter_tolerance,
        "min_object_match_ratio": args.min_object_match_ratio,
    }

    if not _HAS_IJSON:
        print("avertissement: ijson indisponible — lecture des JSON en mémoire (json.load)", file=sys.stderr)

    test_index = {}
    for path in sorted(test_dir.glob("*.json")):
        if ".worker." in path.name or path.name == "run_fingerprint.json":
            continue
        test_index[path.name] = path

    videos = []
    for ref_path in sorted(ref_dir.glob("*.json")):
        if ".worker." in ref_path.name or ref_path.name == "run_fingerprint.json":
            continue
        if args.videos and not any(item.lower() in ref_path.name.lower() for item in args.videos):
            continue
        test_path = test_index.get(ref_path.name)
        if test_path is None:
            print(f"avertissement: {ref_path.name} absent de la variante — ignoré", file=sys.stderr)
            continue
        videos.append(compare_video(ref_path, test_path, faces_only=args.faces_only))

    if not videos:
        print("Aucune vidéo comparable (vérifier les répertoires).", file=sys.stderr)
        return 2

    summary = {
        "ref": str(ref_dir),
        "test": str(test_dir),
        "faces_only": bool(args.faces_only),
        "thresholds": thresholds,
        "videos": videos,
    }
    failures = evaluate_thresholds(summary, thresholds)
    summary["failures"] = failures
    summary["status"] = "FAIL" if failures else "OK"

    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.markdown:
        Path(args.markdown).write_text(render_markdown(summary, failures), encoding="utf-8")

    print(render_markdown(summary, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
