#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vérification empirique de l'espace de classes du détecteur d'objets Coral TPU.

Le pipeline STEP4 TPU charge `assets/detect_edgetpu.tflite` et étiquette chaque objet
`f"class_{int(classes[i])}"` (indice brut du tenseur). La STEP6 ne conserve que
`label == "person"` : sans mapping, tous les objets sont jetés en aval.

Ce script sert à PROUVER l'espace d'index du modèle avant de figer le mapping :
  - tenseurs d'entrée/sortie réels du modèle ;
  - indices de classe, scores et boîtes détectées ;
  - libellé candidat par le `labelmap.txt` compagnon (`labelmap[indice + 1]`) ET par la
    liste COCO-80 contiguë (celle du chemin OpenCV 5, espace d'index DIFFÉRENT) ;
  - comparaison optionnelle avec les détections déjà publiées dans un JSON STEP4 ;
  - export des crops PNG pour contrôle visuel.

À exécuter avec le venv Coral (pycoral + tflite_runtime + cv2 + numpy) :

    coral_env/bin/python scripts/inspect_coral_object_detector.py \\
        --video "projets_extraits/1510 Camille/docs/<clip>.mp4" \\
        --json  "projets_extraits/1510 Camille/docs/<clip>.json" \\
        --sample-every 250 --dump-dir "$COMMANDCODE_SCRATCHPAD/inspector"
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = PROJECT_ROOT / "assets" / "detect_edgetpu.tflite"
DEFAULT_LABELMAP = PROJECT_ROOT / "workflow_scripts" / "step4" / "models" / "metadata" / "labelmap.txt"
DELEGATE_CANDIDATES = (
    PROJECT_ROOT / "tmp_lib" / "usr" / "lib" / "x86_64-linux-gnu" / "libedgetpu.so.1",
    "libedgetpu.so.1",
)

# Référence de diagnostic uniquement : liste COCO-80 contiguë utilisée par le chemin
# YOLO/OpenCV 5 (`run_tracking_cv5.py`). Son espace d'index est DIFFÉRENT de celui du
# modèle EfficientDet du chemin TPU — c'est précisément ce que ce script vérifie.
COCO80 = (
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
    "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
    "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
    "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
    "toothbrush",
)


def load_labelmap(path: Path) -> List[str]:
    """Charge le labelmap compagnon du modèle (1 ligne par entrée, la 1re est le padding)."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() != "" or True]


def labelmap_label(labels: Sequence[str], class_index: int) -> Optional[str]:
    """Libellé selon `labelmap[indice + 1]` (convention du fichier compagnon COCO 1-90)."""
    position = class_index + 1
    if 0 <= position < len(labels):
        name = labels[position]
        return None if name == "???" else name
    return None


def coco80_label(class_index: int) -> Optional[str]:
    """Libellé selon la liste COCO-80 contiguë (référence de diagnostic)."""
    if 0 <= class_index < len(COCO80):
        return COCO80[class_index]
    return None


def active_tpu_consumers() -> List[str]:
    """Détecte un autre pipeline STEP4 en cours (le TPU est mono-consommateur)."""
    try:
        proc = subprocess.run(
            ["pgrep", "-af", "workflow_scripts/step"],
            capture_output=True, text=True, check=False,
        )
    except OSError:
        return []
    own = str(os.getpid())
    return [
        line for line in proc.stdout.splitlines()
        if "inspect_coral_object_detector.py" not in line and own not in line.split()[:1]
    ]


def build_interpreter(model_path: Path):
    """Charge le modèle avec le delegate Edge TPU, ou lève une erreur explicite."""
    delegate_errors: List[str] = []
    try:
        from pycoral.utils.edgetpu import make_interpreter  # type: ignore

        for candidate in DELEGATE_CANDIDATES:
            try:
                return make_interpreter(str(model_path), device=":0"), "pycoral"
            except Exception as exc:  # pragma: no cover - dépend du matériel
                delegate_errors.append(f"pycoral/{candidate}: {exc}")
    except ImportError as exc:
        delegate_errors.append(f"pycoral indisponible: {exc}")

    try:
        import tflite_runtime.interpreter as tflite  # type: ignore

        for candidate in DELEGATE_CANDIDATES:
            try:
                delegate = tflite.load_delegate(str(candidate))
                interpreter = tflite.Interpreter(model_path=str(model_path), experimental_delegates=[delegate])
                interpreter.allocate_tensors()
                return interpreter, f"tflite_runtime delegate={candidate}"
            except Exception as exc:  # pragma: no cover - dépend du matériel
                delegate_errors.append(f"tflite_runtime/{candidate}: {exc}")
    except ImportError as exc:
        delegate_errors.append(f"tflite_runtime indisponible: {exc}")

    raise SystemExit(
        "Aucun interpreter Edge TPU n'a pu être chargé (vérification invalide sans delegate) :\n  "
        + "\n  ".join(delegate_errors)
    )


def extract_frame_rgb(video: Path, frame_index: int, fps: float) -> np.ndarray:
    """Extrait une frame en RGB24 via FFmpeg (seek temporel puis décodage de 1 frame)."""
    timestamp = max(0.0, frame_index / max(fps, 0.001))
    cmd = [
        "ffmpeg", "-nostdin", "-v", "error",
        "-ss", f"{timestamp:.6f}",
        "-i", str(video),
        "-frames:v", "1",
        "-pix_fmt", "rgb24",
        "-f", "rawvideo",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    if proc.returncode != 0 or not proc.stdout:
        raise SystemExit(f"Extraction FFmpeg impossible pour la frame {frame_index}: {proc.stderr.decode('utf-8', 'ignore')[:400]}")

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "csv=p=0:s=x", str(video)],
        capture_output=True, text=True, check=False,
    )
    try:
        width, height = (int(v) for v in probe.stdout.strip().split("x")[:2])
    except Exception:
        raise SystemExit(f"Résolution illisible via ffprobe: {probe.stdout!r} {probe.stderr!r}")

    expected = width * height * 3
    if len(proc.stdout) < expected:
        raise SystemExit(f"Flux RVB incomplet: {len(proc.stdout)} octets pour {expected} attendus")
    return np.frombuffer(proc.stdout[:expected], dtype=np.uint8).reshape((height, width, 3))


def run_inference(interpreter, image_rgb: np.ndarray) -> Tuple[List[Dict], Dict]:
    """Reproduit exactement l'inférence du pipeline (resize INTER_NEAREST, seuil 0,3, max 5)."""
    import cv2  # import local: dépendance du venv Coral

    input_details = interpreter.get_input_details()[0]
    _, in_h, in_w = input_details["shape"][:3]
    resized = cv2.resize(image_rgb, (int(in_w), int(in_h)), interpolation=cv2.INTER_NEAREST)
    if input_details["dtype"] == np.float32:
        resized = (resized.astype(np.float32) / 127.5) - 1.0
    interpreter.tensor(input_details["index"])()[0][:, :] = resized
    interpreter.invoke()

    output_details = interpreter.get_output_details()
    boxes = interpreter.get_tensor(output_details[0]["index"])[0]
    classes = interpreter.get_tensor(output_details[1]["index"])[0]
    scores = interpreter.get_tensor(output_details[2]["index"])[0]
    count = int(interpreter.get_tensor(output_details[3]["index"])[0])

    detections: List[Dict] = []
    for i in range(min(count, 5)):
        if float(scores[i]) < 0.3:
            continue
        ymin, xmin, ymax, xmax = (float(v) for v in boxes[i])
        detections.append({
            "raw_index": int(classes[i]),
            "score": float(scores[i]),
            "box_norm": (xmin, ymin, xmax, ymax),
        })

    meta = {
        "input_shape": tuple(int(v) for v in input_details["shape"]),
        "input_dtype": str(input_details["dtype"]),
        "count": count,
        "raw_classes": [int(c) for c in classes[:min(count, 5)]],
        "raw_scores": [round(float(s), 4) for s in scores[:min(count, 5)]],
    }
    return detections, meta


_JSON_CACHE: Dict[str, Dict[int, Dict]] = {}


def _load_json_frames(json_path: Path) -> Optional[Dict[int, Dict]]:
    """Charge (une seule fois) l'index frame -> entrée du JSON publié."""
    key = str(json_path)
    if key in _JSON_CACHE:
        return _JSON_CACHE[key]
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"  [avert.] JSON illisible ({exc})", file=sys.stderr)
        _JSON_CACHE[key] = {}
        return None
    _JSON_CACHE[key] = {int(item.get("frame", -1)): item for item in (payload.get("frames") or [])}
    return _JSON_CACHE[key]


def load_published_detections(json_path: Path, frame_index: int) -> Optional[List[Dict]]:
    """Récupère les objets `object_detector` enregistrés par le pipeline pour une frame."""
    by_frame = _load_json_frames(json_path)
    if not by_frame:
        return None
    entry = by_frame.get(frame_index)
    if entry is None:
        return None

    width = 1920.0
    height = 1080.0
    published: List[Dict] = []
    for obj in entry.get("tracked_objects") or []:
        if obj.get("source") != "object_detector":
            continue
        label = str(obj.get("label") or "")
        raw = None
        if label.startswith("class_"):
            try:
                raw = int(label.split("_", 1)[1])
            except ValueError:
                raw = None
        published.append({
            "label": label,
            "raw_index": raw,
            "score": float(obj.get("confidence") or 0.0),
            "box_norm": (
                float(obj.get("bbox_xmin", 0)) / width,
                float(obj.get("bbox_ymin", 0)) / height,
                float(obj.get("bbox_xmax", 0)) / width,
                float(obj.get("bbox_ymax", 0)) / height,
            ),
        })
    return published


def iou(box_a: Sequence[float], box_b: Sequence[float]) -> float:
    """IoU de deux boîtes normalisées (xmin, ymin, xmax, ymax)."""
    ax0, ay0, ax1, ay1 = box_a
    bx0, by0, bx1, by1 = box_b
    inter_w = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    inter_h = max(0.0, min(ay1, by1) - max(ay0, by0))
    intersection = inter_w * inter_h
    if intersection <= 0:
        return 0.0
    area_a = max(0.0, ax1 - ax0) * max(0.0, ay1 - ay0)
    area_b = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    union = area_a + area_b - intersection
    return float(intersection / union) if union > 0 else 0.0


def dump_crop(image_rgb: np.ndarray, box_norm: Sequence[float], out_path: Path, pad: int = 20) -> None:
    """Écrit un PNG du crop détecté pour contrôle visuel."""
    import cv2  # import local: dépendance du venv Coral

    h, w = image_rgb.shape[:2]
    x0, y0, x1, y1 = box_norm
    px0 = max(0, int(x0 * w) - pad)
    py0 = max(0, int(y0 * h) - pad)
    px1 = min(w, int(x1 * w) + pad)
    py1 = min(h, int(y1 * h) + pad)
    if px1 <= px0 or py1 <= py0:
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    crop = image_rgb[py0:py1, px0:px1]
    cv2.imwrite(str(out_path), cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))


def parse_frames(spec: str) -> List[int]:
    """Analyse `--frames` (liste d'indices et/ou plages `début:fin:pas`)."""
    frames: List[int] = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" in chunk:
            parts = [int(p) for p in chunk.split(":")]
            if len(parts) == 2:
                start, stop = parts
                step = 1
            elif len(parts) == 3:
                start, stop, step = parts
            else:
                raise SystemExit(f"Plage invalide: {chunk}")
            frames.extend(range(start, stop, max(1, step)))
        else:
            frames.append(int(chunk))
    return frames


def main() -> int:
    parser = argparse.ArgumentParser(description="Vérification de l'espace de classes du détecteur d'objets Coral TPU")
    parser.add_argument("--video", type=Path, required=True, help="Vidéo source (STEP1-3 déjà exécutées)")
    parser.add_argument("--json", type=Path, default=None, help="JSON STEP4 publié à comparer")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--labelmap", type=Path, default=DEFAULT_LABELMAP)
    parser.add_argument("--frames", type=str, default="0", help="Indices et/ou plages, ex. '0,250,500' ou '0:5000:250'")
    parser.add_argument("--fps", type=float, default=25.0)
    parser.add_argument("--dump-dir", type=Path, default=None, help="Dossier des crops PNG (contrôle visuel)")
    parser.add_argument("--min-iou", type=float, default=0.5, help="Seuil de correspondance avec le JSON publié")
    parser.add_argument("--force", action="store_true", help="Ne pas refuser si un pipeline STEP4 tourne déjà")
    args = parser.parse_args()

    consumers = active_tpu_consumers()
    if consumers and not args.force:
        print("Un pipeline STEP4 semble actif (le TPU est mono-consommateur) :", file=sys.stderr)
        for line in consumers:
            print(f"  {line}", file=sys.stderr)
        print("Relancer avec --force si c'est un faux positif.", file=sys.stderr)
        return 2

    if not args.video.exists():
        raise SystemExit(f"Vidéo introuvable: {args.video}")
    if not args.model.exists():
        raise SystemExit(f"Modèle introuvable: {args.model}")
    labels = load_labelmap(args.labelmap) if args.labelmap.exists() else []
    if not labels:
        print(f"[avert.] labelmap absent ou vide: {args.labelmap}", file=sys.stderr)

    interpreter, backend = build_interpreter(args.model)
    frames = parse_frames(args.frames)

    print(f"Modèle          : {args.model}")
    print(f"Backend         : {backend}")
    print(f"Labelmap        : {args.labelmap} ({len(labels)} lignes)")
    print(f"Vidéo           : {args.video.name}")
    print(f"Frames testées  : {len(frames)}")
    print()

    observed_indices: set = set()
    reproducibility_hits = 0
    reproducibility_tested = 0
    dead_indices_hit: set = set()

    for frame_index in frames:
        published = load_published_detections(args.json, frame_index) if args.json is not None else None
        # Le seek FFmpeg peut décaler d'une frame : on teste N-1, N, N+1 et on retient
        # la meilleure correspondance avec les détections publiées.
        candidates = [frame_index]
        if published:
            candidates = sorted({max(0, frame_index - 1), frame_index, frame_index + 1})
        best_matches: List[Tuple[float, Optional[int], int]] = [(0.0, None, frame_index) for _ in (published or [])]

        for candidate in candidates:
            image = extract_frame_rgb(args.video, candidate, args.fps)
            detections, meta = run_inference(interpreter, image)

            for det in detections:
                observed_indices.add(det["raw_index"])
                if labels and labelmap_label(labels, det["raw_index"]) is None:
                    dead_indices_hit.add(det["raw_index"])

            if candidate == frame_index:
                print(f"--- frame {frame_index} --- entrée {meta['input_shape']} {meta['input_dtype']} | count={meta['count']}")
                print(f"    indices bruts   : {meta['raw_classes']}")
                print(f"    scores bruts    : {meta['raw_scores']}")
                for rank, det in enumerate(detections):
                    index = det["raw_index"]
                    labelmap_name = labelmap_label(labels, index) if labels else None
                    coco_name = coco80_label(index)
                    flag = "" if labelmap_name == coco_name else "   <-- mapping divergent"
                    print(
                        f"    [{rank}] indice={index:<3} score={det['score']:.3f} "
                        f"labelmap[{index}+1]={labelmap_name!r} coco80[{index}]={coco_name!r}{flag}"
                    )
                    if args.dump_dir is not None:
                        dump_crop(
                            image, det["box_norm"],
                            args.dump_dir / f"frame{frame_index:06d}_idx{index}_score{det['score']:.2f}.png",
                        )

            if published:
                for position, pub in enumerate(published):
                    for det in detections:
                        value = iou(det["box_norm"], pub["box_norm"])
                        if value > best_matches[position][0]:
                            best_matches[position] = (value, det["raw_index"], candidate)

        if args.json is not None:
            if published is None:
                print("    [JSON] aucune entrée pour cette frame")
            else:
                for position, pub in enumerate(published):
                    best_iou, best_index, best_frame = best_matches[position]
                    reproducibility_tested += 1
                    ok = best_iou >= args.min_iou and (pub["raw_index"] is None or pub["raw_index"] == best_index)
                    if ok:
                        reproducibility_hits += 1
                    shift = "" if best_frame == frame_index else f" (frame {best_frame}: décalage seek)"
                    print(
                        f"    [JSON] publié label={pub['label']!r} score={pub['score']:.3f} "
                        f"-> meilleur IoU={best_iou:.3f} indice modèle={best_index}{shift} {'OK' if ok else 'ÉCART'}"
                    )
        print()

    print("=" * 72)
    print(f"Indices observés            : {sorted(observed_indices)}")
    print(f"Indices hors plage (>=91)   : {[i for i in observed_indices if i >= 91]}")
    print(f"Indices morts atteints      : {sorted(dead_indices_hit)} (attendu: aucun)")
    if reproducibility_tested:
        ratio = reproducibility_hits / reproducibility_tested
        print(f"Reproductibilité JSON       : {reproducibility_hits}/{reproducibility_tested} ({ratio:.0%}) — critère: 100% avec IoU >= {args.min_iou}")
    verdict = (
        "CRITÈRES OK"
        if not [i for i in observed_indices if i >= 91]
        and not dead_indices_hit
        and (reproducibility_tested == 0 or reproducibility_hits == reproducibility_tested)
        else "CRITÈRES NON SATISFAITS"
    )
    print(f"VERDICT                     : {verdict}")
    return 0 if verdict == "CRITÈRES OK" else 1


if __name__ == "__main__":
    sys.exit(main())
