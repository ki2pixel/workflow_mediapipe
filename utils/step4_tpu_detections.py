"""Étiquetage et construction des détections du chemin STEP4 Coral TPU.

Le détecteur d'objets du chemin TPU (`assets/detect_edgetpu.tflite`, EfficientDet)
émet des **indices de classe 0-based** dans l'espace COCO 1-90 : l'indice 0 est
`person`, l'indice 89 est `toothbrush`, et les 10 identifiants morts du COCO
(11, 25, 28, 29, 44, 65, 67, 68, 70, 82) ne sont jamais émis.

Le libellé se lit donc `LABELS[indice + 1]` dans le fichier compagnon
`workflow_scripts/step4/models/metadata/labelmap.txt` (91 lignes, la première
étant le padding `???`).

Preuves (scripts/inspect_coral_object_detector.py, 23 frames de
`projets_extraits/1510 Camille/docs/Greg craque…`) :
  - reproductibilité 50/50 à IoU 0,96-0,998 entre l'indice 0 du modèle et les
    détections `class_0` déjà publiées par le pipeline ; idem pour l'indice 61 ;
  - indices observés sur 10 vidéos : 0..89, jamais ≥ 90, jamais un indice mort ;
  - contrôle visuel des cas discriminants : indice 61 = fauteuil (labelmap
    « chair ») et non des toilettes (liste COCO-80), indice 66 = table de repas
    (labelmap « dining table ») et non un clavier (liste COCO-80) ; la taille
    mesurée de la boîte d'indice 61 (≈ 1,0 × 0,9 m) est celle d'un fauteuil.

Le chemin OpenCV 5 (`run_tracking_cv5.py`) utilise un modèle YOLO/ONNX dont
l'espace d'index est **différent** (COCO-80 contigu) : ne jamais réutiliser sa
liste ici, ni l'inverse.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# Fichier compagnon du modèle, source de vérité du mapping (vérifié au démarrage).
LABELMAP_PATH = (
    Path(__file__).resolve().parents[1]
    / "workflow_scripts" / "step4" / "models" / "metadata" / "labelmap.txt"
)

# Les 91 lignes de labelmap.txt, dans l'ordre : LABELS[indice_modele + 1].
EFFICIENTDET_LABELS = (
    "???", "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "???", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "???", "backpack", "umbrella", "???",
    "???", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
    "surfboard", "tennis racket", "bottle", "???", "wine glass", "cup", "fork",
    "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange", "broccoli",
    "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "???", "dining table", "???", "???", "toilet", "???",
    "tv", "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
    "oven", "toaster", "sink", "refrigerator", "???", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
)

# Identifiants COCO absents de l'espace du modèle (jamais émis).
DEAD_CLASS_INDICES = frozenset({11, 25, 28, 29, 44, 65, 67, 68, 70, 82})

SOURCE_FACE = "face_landmarker"
SOURCE_OBJECT = "object_detector"
FACE_LABEL = "face"

# Le détecteur de visage du chemin TPU publie une confiance fixe.
FACE_CONFIDENCE = 0.95


def label_for_class_index(class_index: int) -> Optional[str]:
    """Libellé COCO d'un indice de classe du modèle, ou None si mort/hors plage."""
    position = int(class_index) + 1
    if 0 <= position < len(EFFICIENTDET_LABELS):
        name = EFFICIENTDET_LABELS[position]
        if name != "???":
            return name
    return None


def resolve_class_label(class_index: Any) -> str:
    """Libellé exploitable en aval ; repli `class_N` pour un indice invalide.

    Le repli garde le diagnostic mais ne peut jamais produire `person` par
    accident : un indice mort ou hors plage n'est donc pas confondu avec une
    personne par la STEP6.
    """
    try:
        index = int(round(float(class_index)))
    except (TypeError, ValueError):
        return f"class_{class_index}"
    return label_for_class_index(index) or f"class_{index}"


def verify_labelmap_file(path: Path = LABELMAP_PATH) -> Optional[str]:
    """Compare la liste embarquée au fichier compagnon ; retourne un écart éventuel."""
    try:
        lines = [line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines()]
    except OSError as exc:
        return f"labelmap illisible ({exc}) : mapping embarqué utilisé"
    lines = [line for line in lines if line != ""]
    if tuple(lines) != EFFICIENTDET_LABELS:
        return (
            f"labelmap divergent ({path}) : {len(lines)} lignes lues contre "
            f"{len(EFFICIENTDET_LABELS)} embarquées — vérifier le modèle"
        )
    return None


def build_face_detection(centroid, bbox, blendshapes, confidence: float = FACE_CONFIDENCE) -> Dict[str, Any]:
    """Détection de visage au format attendu par le tracker STEP4."""
    return {
        "centroid": centroid,
        "bbox": bbox,
        "blendshapes": blendshapes,
        "source_detector": SOURCE_FACE,
        "label": FACE_LABEL,
        "confidence": confidence,
    }


def build_object_detections(
    boxes: Sequence[Sequence[float]],
    classes: Sequence[float],
    scores: Sequence[float],
    count: int,
    width: int,
    height: int,
    score_threshold: float = 0.3,
    max_objects: int = 5,
) -> List[Dict[str, Any]]:
    """Construit les détections d'objets (EfficientDet) au format du tracker STEP4."""
    detections: List[Dict[str, Any]] = []
    for i in range(min(int(count), int(max_objects))):
        if float(scores[i]) < score_threshold:
            continue

        ymin, xmin, ymax, xmax = (float(value) for value in boxes[i])

        o_xmin = max(0, int(xmin * width))
        o_ymin = max(0, int(ymin * height))
        o_xmax = min(width, int(xmax * width))
        o_ymax = min(height, int(ymax * height))

        o_width_px = o_xmax - o_xmin
        o_height_px = o_ymax - o_ymin
        o_cx = o_xmin + o_width_px // 2
        o_cy = o_ymin + o_height_px // 2

        detections.append({
            "centroid": (o_cx, o_cy),
            "bbox": (o_xmin, o_ymin, o_width_px, o_height_px),
            "blendshapes": {},
            "source_detector": SOURCE_OBJECT,
            "label": resolve_class_label(classes[i]),
            "confidence": float(scores[i]),
        })
    return detections
