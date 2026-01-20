# Fichier : tracking_optimizations.py

import os
import numpy as np
from scipy.spatial import KDTree
import sys
from typing import Dict, List, Tuple, Any, Optional


def _filter_blendshapes_for_export(blendshapes: Any) -> Any:
    profile = os.environ.get("STEP5_BLENDSHAPES_PROFILE", "full").strip().lower()
    if not blendshapes or not isinstance(blendshapes, dict):
        return blendshapes

    if profile in {"", "full", "all"}:
        return blendshapes

    if profile in {"none", "off", "0", "false", "no"}:
        return None

    if profile == "mouth":
        filtered = {
            k: v
            for k, v in blendshapes.items()
            if k.startswith("mouth") or k.startswith("jaw")
        }
        include_tongue = os.environ.get("STEP5_BLENDSHAPES_INCLUDE_TONGUE", "0").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        if include_tongue and "tongueOut" in blendshapes:
            filtered["tongueOut"] = blendshapes["tongueOut"]
        return filtered or None

    if profile == "mediapipe":
        filtered = dict(blendshapes)
        filtered.pop("tongueOut", None)
        filtered.setdefault("_neutral", 0.0)
        return filtered or None

    if profile == "custom":
        keys_raw = os.environ.get("STEP5_BLENDSHAPES_EXPORT_KEYS", "").strip()
        if not keys_raw:
            return blendshapes
        keys = [k.strip() for k in keys_raw.split(",") if k.strip()]
        filtered = {k: blendshapes[k] for k in keys if k in blendshapes}
        return filtered or None

    return blendshapes


def get_next_id(counter_ref, prefix="obj_"):
    """Incrémente et retourne un nouvel ID."""
    counter_ref["value"] += 1
    return f"{prefix}{counter_ref['value']}"


def apply_tracking_and_management(
    active_objects,
    current_detections,
    next_id_counter,
    distance_threshold,
    frames_unseen_to_deregister,
    speaking_detection_jaw_open_threshold=0.08,
    enhanced_speaking_detector=None,
    current_frame_num=None,
):
    """
    Gère le cycle de vie complet du tracking pour une frame en utilisant KDTree.
    Version optimisée et centralisée pour toute l'application.
    """
    # --- Phase 1: Incrémentation des 'frames_unseen' pour tous les objets actifs ---
    for obj_id in active_objects:
        active_objects[obj_id]["frames_unseen"] += 1

    matched_detection_indices = set()

    # --- Phase 2: Appariement si des objets actifs ET des détections existent ---
    if active_objects and current_detections:
        active_obj_ids = list(active_objects.keys())
        tracked_centroids = np.array([obj["centroid"] for obj in active_objects.values()])
        detection_centroids = np.array([det["centroid"] for det in current_detections])

        kdtree = KDTree(tracked_centroids)
        distances, indices = kdtree.query(detection_centroids, k=1)

        potential_matches = sorted(zip(distances, indices, range(len(current_detections))))
        
        matched_tracked_indices = set()

        for dist, tracked_idx, det_idx in potential_matches:
            if (
                dist > distance_threshold
                or det_idx in matched_detection_indices
                or tracked_idx in matched_tracked_indices
            ):
                continue

            obj_id = active_obj_ids[tracked_idx]
            matched_det = current_detections[det_idx]

            active_objects[obj_id].update({**matched_det, "frames_unseen": 0})
            
            matched_detection_indices.add(det_idx)
            matched_tracked_indices.add(tracked_idx)

    # --- Phase 3: Enregistrement des nouvelles détections non appariées ---
    # Ce bloc est maintenant exécuté que active_objects soit vide ou non.
    if current_detections:
        for i, det_info in enumerate(current_detections):
            if i not in matched_detection_indices:
                new_id = get_next_id(next_id_counter)
                active_objects[new_id] = {
                    "id": new_id,
                    **det_info,
                    "frames_unseen": 0,
                }

    # --- Phase 4: Préparation de la sortie et Nettoyage ---
    output_objects_for_json = []
    ids_to_remove = []

    for obj_id, obj_data in active_objects.items():
        if obj_data["frames_unseen"] > frames_unseen_to_deregister:
            ids_to_remove.append(obj_id)
            continue

        if obj_data["frames_unseen"] == 0:
            confidence_val = obj_data.get("confidence")
            output_obj = {
                "id": obj_id,
                "centroid_x": obj_data["centroid"][0],
                "centroid_y": obj_data["centroid"][1],
                "bbox_xmin": obj_data["bbox"][0],
                "bbox_xmax": obj_data["bbox"][0] + obj_data["bbox"][2],
                "source": obj_data.get("source_detector", "unknown"),
                "label": obj_data.get("label", ""),
                "confidence": (
                    round(float(confidence_val), 3) if confidence_val is not None else 0.0
                ),
                "blendshapes": _filter_blendshapes_for_export(obj_data.get("blendshapes")),
            }

            # Always include bbox size for face_landmarker before speaking detection branching
            try:
                bbox_tuple = obj_data.get("bbox")
                if bbox_tuple and len(bbox_tuple) >= 4:
                    output_obj["bbox_ymin"] = int(bbox_tuple[1])
                    output_obj["bbox_ymax"] = int(bbox_tuple[1] + bbox_tuple[3])
                    output_obj["bbox_width"] = int(bbox_tuple[2])
                    output_obj["bbox_height"] = int(bbox_tuple[3])
            except Exception:
                # Non-blocking if bbox is missing or malformed
                pass

            # Enhanced speaking detection
            if enhanced_speaking_detector and current_frame_num:
                # Use enhanced multi-source speaking detection
                detection_result = enhanced_speaking_detector.detect_speaking(
                    frame_num=current_frame_num,
                    blendshapes=output_obj.get("blendshapes"),
                    source_detector=output_obj["source"]
                )

                output_obj["is_speaking"] = detection_result.is_speaking
                output_obj["speaking_confidence"] = detection_result.confidence
                output_obj["speaking_method"] = detection_result.method
                output_obj["speaking_sources"] = detection_result.sources

            elif output_obj["source"] == "face_landmarker":
                # Fallback to original jaw-based detection
                if output_obj["blendshapes"] and "jawOpen" in output_obj["blendshapes"]:
                    jaw_open_score = output_obj["blendshapes"].get("jawOpen", 0.0)
                    output_obj["is_speaking"] = (
                        jaw_open_score > speaking_detection_jaw_open_threshold
                    )
                    output_obj["speaking_confidence"] = min(jaw_open_score / speaking_detection_jaw_open_threshold, 1.0)
                    output_obj["speaking_method"] = "jaw_threshold_fallback"
                else:
                    # S'assurer que la clé existe pour les visages, même sans blendshapes
                    output_obj["is_speaking"] = False
                    output_obj["speaking_confidence"] = 0.0
                    output_obj["speaking_method"] = "no_blendshapes"
            else:
                # For object detection, try enhanced detection or set defaults
                if enhanced_speaking_detector and current_frame_num:
                    detection_result = enhanced_speaking_detector.detect_speaking(
                        frame_num=current_frame_num,
                        blendshapes=None,
                        source_detector=output_obj["source"]
                    )
                    output_obj["is_speaking"] = detection_result.is_speaking
                    output_obj["speaking_confidence"] = detection_result.confidence
                    output_obj["speaking_method"] = detection_result.method
                    output_obj["speaking_sources"] = detection_result.sources
                else:
                    # Remove speaking-related fields for objects without enhanced detection
                    output_obj.pop("blendshapes", None)
                    output_obj.pop("is_speaking", None)
                    output_obj.pop("speaking_confidence", None)
                    output_obj.pop("speaking_method", None)
                    output_obj.pop("speaking_sources", None)

            # Optional exports for face engines (not present for object detector)
            # Controlled by STEP5_EXPORT_VERBOSE_FIELDS to reduce JSON size
            try:
                if output_obj.get("source") == "face_landmarker":
                    export_verbose = os.environ.get("STEP5_EXPORT_VERBOSE_FIELDS", "false").strip().lower()
                    should_export_verbose = export_verbose in {"true", "1", "yes", "on", "all"}
                    
                    if should_export_verbose:
                        landmarks_val = obj_data.get("landmarks")
                        if landmarks_val:
                            output_obj["landmarks"] = landmarks_val

                        eos_val = obj_data.get("eos")
                        if eos_val and isinstance(eos_val, dict):
                            output_obj["eos"] = eos_val
            except Exception:
                pass

            output_objects_for_json.append(output_obj)

    for obj_id in ids_to_remove:
        del active_objects[obj_id]

    output_objects_for_json.sort(key=lambda o: o.get("centroid_x", 0))

    return output_objects_for_json