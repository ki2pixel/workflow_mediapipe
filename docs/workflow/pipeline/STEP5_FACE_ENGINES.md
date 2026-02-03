# STEP5 - Moteurs de Détection Faciale

> **Code-Doc Context** – Composants critiques du pipeline STEP5 avec complexité radon E/F. Voir `STEP5_SUIVI_VIDEO.md` pour le contexte global du pipeline.

---

## Purpose & Pipeline Role

### Objectif
Documentation des 5 moteurs de détection faciale utilisés dans STEP5, chacun avec des caractéristiques spécifiques en termes de précision, performance et complexité d'implémentation.

### Rôle dans le Pipeline
- **Position** : Cœur de l'Étape 5 (STEP5)
- **Prérequis** : Vidéos standardisées (STEP2), analyses audio (STEP4)
- **Sortie** : JSON dense avec landmarks, blendshapes et métadonnées de détection
- **Étape suivante** : Réduction JSON (STEP6)

---

## Moteurs Disponibles

### Mode MediaPipe (défaut)
- **Sélection** : `STEP5_TRACKING_ENGINE` vide (ou valeur `mediapipe` / `mediapipe_landmarker` normalisée en vide)
- **Performance** : CPU
- **Complexité** : Traitement géré dans les workers STEP5
- **Cas d'usage** : Mode par défaut, stable, sans dépendances GPU

### InsightFace (RetinaFace + Antelopev2)
- **Caractéristiques** : Détection haute précision, embeddings faciaux
- **Performance** : GPU accéléré (CUDA)
- **Complexité** : Très élevée - `InsightFaceEngine.detect()` (Score E)
- **Cas d'usage** : Applications nécessitant haute précision

---

## Complexité (Radon Analysis)

### Points Critiques (Score E/F)

#### `InsightFaceEngine.detect()` (Score E)
- **Complexité** : 800 lignes, gestion GPU/CPU, fallback object detector
- **Défis** : Lazy import MediaPipe, gestion VRAM, throttling
- **Impact** : Moteur le plus précis mais complexe à maintenir

#### `InsightFaceEngine.__init__()` (Score D)
- **Complexité** : 611 lignes, configuration CUDA, modèles antelopev2
- **Défis** : Détection GPU, gestion dépendances ONNX
- **Impact** : Setup complexe mais performances excellentes

---

## Configuration GPU/CPU

### Variables d'Environnement
```bash
# Activation GPU (optionnel)
STEP5_ENABLE_GPU=1
STEP5_GPU_ENGINES=insightface

# Désactivation GPU (défaut pour stabilité)
STEP5_DISABLE_GPU=1

# Workers CPU
TRACKING_CPU_WORKERS=15

# Profiling et debugging
STEP5_ENABLE_PROFILING=1
STEP5_BLENDSHAPES_THROTTLE_N=1
```

### Lazy Import MediaPipe
```python
# Évite les conflits TensorFlow dans tracking_env
def _ensure_mediapipe_loaded(required=True):
    try:
        mediapipe = importlib.import_module("mediapipe")
        return mediapipe
    except ImportError as e:
        if required:
            raise
        return None
```

---

## Architecture Technique

### Registry de Moteurs
```python
# workflow_scripts/step5/face_engines.py
class FaceEngineRegistry:
    engines = {
        'mediapipe': None,
        'insightface': InsightFaceEngine,
    }
```

### Pattern de Détection
```python
def detect(self, frame: np.ndarray, frame_num: int) -> List[Dict]:
    """
    Détection standardisée pour tous les moteurs
    Returns: List[tracked_objects] pour JSON export
    """
    # 1. Préprocessing (downscaling, conversion)
    # 2. Détection visages/objets
    # 3. Extraction landmarks/blendshapes  
    # 4. Rescaling coordonnées si nécessaire
    # 5. Formatage JSON standardisé
```

---

## Performance & Optimisations

### Downscaling & Rescaling
- **InsightFace** : `STEP5_INSIGHTFACE_MAX_WIDTH` (fallback `STEP5_YUNET_MAX_WIDTH`, défaut 1280)
- **MediaPipe (défaut)** : options MediaPipe dans les workers (ex: `STEP5_MEDIAPIPE_MAX_WIDTH`)
- **Rescaling automatique** : Coordonnées remises à l'échelle de la vidéo originale

### Profiling Intégré
```python
# Logs toutes les 20 frames en multiprocessing
if frame_num % 20 == 0:
    logger.info(f"[PROFILING] Engine: {engine_name}, "
               f"FPS: {current_fps:.2f}, "
               f"Faces: {len(detections)}, "
               f"Memory: {memory_usage:.1f}MB")
```

### Multiprocessing Support
- Tous les moteurs supportent `process_video_worker_multiprocessing.py`
- Chargement `.env` côté worker pour configuration effective
- `cv2.setNumThreads(1)` pour éviter contention CPU

---

## Sélection du Moteur

### Recommandations par Cas d'Usage
- **Production stable** : Mode MediaPipe par défaut (CPU)
- **Haute précision** : InsightFace (GPU)

### Critères de Performance
- **Vitesse** : dépend fortement du matériel et des modèles; comparer uniquement MediaPipe (CPU) vs InsightFace (GPU)
- **Précision** : InsightFace (GPU) vise la meilleure précision; MediaPipe (CPU) est le mode par défaut
- **Complexité** : InsightFace est le moteur le plus complexe; MediaPipe est le mode le plus simple à opérer

---

## Debugging & Maintenance

### Logs Spécifiques
```bash
# Logs moteur spécifique
tail -f logs/step5/insightface_worker_*.log
tail -f logs/step5/manager_tracking_*.log

# Profiling activé
grep "[PROFILING]" logs/step5/worker_*.log
```

### Tests Unitaires
```bash
# Tests par moteur
pytest tests/unit/test_step5_face_engines.py
pytest tests/unit/test_step5_insightface_engine.py
pytest tests/unit/test_step5_multiprocessing.py
```

### Validation GPU
```bash
# Vérification providers ONNX
grep "ONNX providers active" logs/step5/worker_*.log
# Doit afficher ['CUDAExecutionProvider', 'CPUExecutionProvider']
```
