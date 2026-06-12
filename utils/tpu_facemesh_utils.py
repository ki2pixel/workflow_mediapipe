import math
import numpy as np
import cv2

def generate_blazeface_anchors():
    """
    Génère les 896 ancres SSD pour le modèle BlazeFace 128x128.
    Feature maps : 16x16 (2 ancres) et 8x8 (6 ancres).
    """
    anchors = []
    # Paramètres standard BlazeFace
    strides = [8, 16]
    anchors_per_layer = [2, 6]
    image_size = 128.0

    for i, stride in enumerate(strides):
        grid_rows = int(image_size / stride)
        grid_cols = int(image_size / stride)
        for r in range(grid_rows):
            for c in range(grid_cols):
                y_center = (r + 0.5) / grid_rows
                x_center = (c + 0.5) / grid_cols
                for _ in range(anchors_per_layer[i]):
                    anchors.append([x_center, y_center, 1.0, 1.0])
    
    return np.array(anchors, dtype=np.float32)

def decode_blazeface_boxes(regressors, anchors):
    """
    Décode les 16 valeurs de régression (4 pour bbox, 12 pour 6 keypoints).
    regressors: shape (896, 16)
    anchors: shape (896, 4)
    """
    decoded = np.zeros_like(regressors)
    # Les coordonnées sont relatives à la taille de l'image (128x128)
    # Bbox: cx, cy, w, h
    x_center = regressors[:, 0] / 128.0 + anchors[:, 0]
    y_center = regressors[:, 1] / 128.0 + anchors[:, 1]
    w = regressors[:, 2] / 128.0
    h = regressors[:, 3] / 128.0
    
    decoded[:, 0] = x_center - w / 2.0 # xmin
    decoded[:, 1] = y_center - h / 2.0 # ymin
    decoded[:, 2] = x_center + w / 2.0 # xmax
    decoded[:, 3] = y_center + h / 2.0 # ymax
    
    # Keypoints (6 points: right_eye, left_eye, nose, mouth, right_ear, left_ear)
    for k in range(6):
        offset = 4 + k * 2
        decoded[:, offset] = regressors[:, offset] / 128.0 + anchors[:, 0]
        decoded[:, offset + 1] = regressors[:, offset + 1] / 128.0 + anchors[:, 1]
        
    return decoded

def nms(boxes, scores, score_threshold=0.75, iou_threshold=0.3):
    """
    Non-Maximum Suppression classique.
    """
    # Filtrer par score
    valid_mask = scores > score_threshold
    boxes = boxes[valid_mask]
    scores = scores[valid_mask]
    
    if len(boxes) == 0:
        return [], [], []
    
    # Trier par score décroissant
    order = scores.argsort()[::-1]
    keep = []
    
    while order.size > 0:
        i = order[0]
        keep.append(i)
        
        xx1 = np.maximum(boxes[i, 0], boxes[order[1:], 0])
        yy1 = np.maximum(boxes[i, 1], boxes[order[1:], 1])
        xx2 = np.minimum(boxes[i, 2], boxes[order[1:], 2])
        yy2 = np.minimum(boxes[i, 3], boxes[order[1:], 3])
        
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        
        area_i = (boxes[i, 2] - boxes[i, 0]) * (boxes[i, 3] - boxes[i, 1])
        area_others = (boxes[order[1:], 2] - boxes[order[1:], 0]) * (boxes[order[1:], 3] - boxes[order[1:], 1])
        
        iou = inter / (area_i + area_others - inter)
        
        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]
        
    return keep, boxes, scores

def get_affine_transform(right_eye, left_eye, output_size=192):
    """
    Calcule la matrice de transformation affine basée sur les yeux.
    right_eye, left_eye: tuples (x, y) normalisés.
    """
    # Calcul du centre entre les deux yeux
    center_x = (right_eye[0] + left_eye[0]) / 2.0
    center_y = (right_eye[1] + left_eye[1]) / 2.0
    
    # Calcul de l'angle
    dy = right_eye[1] - left_eye[1]
    dx = right_eye[0] - left_eye[0]
    angle_rad = math.atan2(dy, dx)
    angle_deg = math.degrees(angle_rad)
    
    # Distance entre les yeux (pour ajuster le scale)
    dist = math.hypot(dx, dy)
    
    return {
        "center": (center_x, center_y),
        "angle": angle_deg,
        "dist": dist,
        "output_size": output_size
    }

def apply_affine_crop(image_np, transform_params):
    """
    Applique le recadrage orienté avec cv2.warpAffine (C++ SIMD).
    """
    h, w = image_np.shape[:2]
    cx = transform_params["center"][0] * w
    cy = transform_params["center"][1] * h
    angle = transform_params["angle"]
    out_size = transform_params["output_size"]
    
    # Echelle empirique : La face fait généralement 2.0x à 2.5x la distance inter-oculaire.
    box_size = transform_params["dist"] * 2.5 * max(w, h)
    if box_size < 1e-5:
        box_size = 1e-5
    scale = out_size / box_size
    
    # getRotationMatrix2D prend l'angle en degrés (rotation anti-horaire).
    M = cv2.getRotationMatrix2D((cx, cy), angle, scale)
    # Translation pour centrer la boîte recadrée
    M[0, 2] += out_size / 2 - cx * scale
    M[1, 2] += out_size / 2 - cy * scale
    
    cropped = cv2.warpAffine(image_np, M, (out_size, out_size),
                             flags=cv2.INTER_LINEAR,
                             borderMode=cv2.BORDER_CONSTANT)
    return cropped
