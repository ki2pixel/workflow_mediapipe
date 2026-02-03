> ⚠️ **ARCHIVE / OBSOLETE**
>
> Ce document est conservé **à titre historique** et contient des sections obsolètes (ex: options avancées chunking, multi-moteurs legacy).
>
> STEP5 est désormais simplifié :
> - **Mode MediaPipe (défaut)** : `STEP5_TRACKING_ENGINE` vide (CPU)
> - **InsightFace** : `STEP5_TRACKING_ENGINE=insightface` (GPU-only)
>
> Références à jour :
> - `docs/workflow/pipeline/STEP5_SUIVI_VIDEO.md`
> - `docs/workflow/pipeline/STEP5_GPU_USAGE.md`
> - `docs/workflow/pipeline/STEP5_FACE_ENGINES.md`

```json
{
  "min": 100,    // Taille minimale de chunk en frames (null pour défaut)
  "max": 500     // Taille maximale de chunk en frames (null pour défaut)
}
```

**Paramètres** :
- `min` : `int|null` — Taille minimale de chunk. Doit être un entier positif ou `null`.
- `max` : `int|null` — Taille maximale de chunk. Doit être un entier positif ou `null`.

**Response** (Success) :
```json
{
  "status": "success",
  "message": "Chunk bounds updated",
  "min": 100,
  "max": 500
}
```

**Response** (Error) :
```json
{
  "status": "error",
  "message": "Paramètres invalides (min/max)"
}
```

**Status Codes** :
- `200` : Succès
- `400` : Paramètres invalides (non-entiers, négatifs)
- `500` : Erreur interne

**Implémentation** :

```python
# routes/api_routes.py
@api_bp.route('/step5/chunk_bounds', methods=['POST'])
@measure_api('/api/step5/chunk_bounds')
def set_step5_chunk_bounds():
    """Configure les limites de chunk pour Step5."""
    payload = request.get_json(silent=True) or {}
    min_val = payload.get('min', None)
    max_val = payload.get('max', None)
    
    def _norm(v):
        if v is None:
            return None
        if isinstance(v, int):
            return v
        try:
            return int(v)
        except:
            return 'invalid'
    
    min_norm = _norm(min_val)
    max_norm = _norm(max_val)
    
    if min_norm == 'invalid' or max_norm == 'invalid':
        return jsonify({"status": "error", "message": "Paramètres invalides"}), 400
    
    result = WorkflowService.set_step5_chunk_bounds(min_norm, max_norm)
    if result.get('status') != 'success':
        return jsonify(result), 400
    
    return jsonify(result)
```

**Utilisation** :

```bash
curl -X POST http://localhost:5000/api/step5/chunk_bounds \
  -H "Content-Type: application/json" \
  -d '{"min": 100, "max": 500}'

curl -X POST http://localhost:5000/api/step5/chunk_bounds \
  -H "Content-Type: application/json" \
  -d '{"min": null, "max": null}'
```

**Notes** :
- Route instrumentée via `@measure_api()` pour monitoring des performances
- Délégation complète à `WorkflowService.set_step5_chunk_bounds()`
- Validation stricte des paramètres côté route
- Support de `null` pour reset aux valeurs par défaut

## Spécifications Techniques

### Environnement Virtuel
- **Environnement utilisé** : `tracking_env/` (spécialisé MediaPipe)
- **Activation** : `source tracking_env/bin/activate`
- **Isolation** : Environnement dédié pour MediaPipe et OpenCV

### Technologies et Bibliothèques Principales

#### MediaPipe et Computer Vision
```python
import mediapipe as mp                    # Framework de ML pour vision
from mediapipe.tasks import python       # API Python MediaPipe
from mediapipe.tasks.python import vision # Tâches de vision
import cv2                               # OpenCV pour traitement d'image
import numpy as np                       # Calculs numériques
```

#### Traitement Parallèle et Optimisations
```python
from concurrent.futures import ThreadPoolExecutor  # Multi-threading
import multiprocessing                              # Multi-processing
import threading                                    # Synchronisation
import queue                                        # Communication inter-threads
```

#### Modules Personnalisés
```python
from utils.tracking_optimizations import apply_tracking_and_management
from utils.enhanced_speaking_detection import EnhancedSpeakingDetector
from utils.resource_manager import safe_video_processing
```

### Formats d'Entrée et de Sortie

#### Structure d'Entrée Attendue
```
projets_extraits/
├── projet_camille_001/
│   └── docs/
│       ├── video1.mp4           # Vidéo source
│       ├── video1.csv           # Scènes (STEP3)
│       ├── video1_audio.json    # Analyse audio (STEP4)
│       ├── video2.mov           # Vidéo source
│       ├── video2.csv           # Scènes (STEP3)
│       └── video2_audio.json    # Analyse audio (STEP4)
```

#### Structure de Sortie Générée
```
projets_extraits/
├── projet_camille_001/
│   └── docs/
│       ├── video1.mp4
│       ├── video1.csv
│       ├── video1_audio.json
│       ├── video1_tracking.json     # Données de tracking
│       ├── video2.mov
│       ├── video2.csv
│       ├── video2_audio.json
│       └── video2_tracking.json     # Données de tracking
```

### Paramètres de Configuration

#### Configuration d'exécution

**Mode par défaut (v4.1)**: L'Étape 5 utilise exclusivement le CPU avec 15 workers internes par défaut, offrant de meilleures performances globales sur la configuration actuelle.

**Mode GPU désactivé (v4.2+)**: Depuis la décision du 27/12/2025, **tous les moteurs fonctionnent en mode CPU**. L'utilisation du GPU est réservée exclusivement à InsightFace, et tous les autres moteurs (MediaPipe Face Landmarker, OpenSeeFace, OpenCV YuNet/PyFeat, EOS) sont forcés en mode CPU même lorsque `STEP5_ENABLE_GPU=1`.

**Activation InsightFace GPU** :
1. Définir `STEP5_ENABLE_GPU=1` et s’assurer que `STEP5_GPU_ENGINES=insightface`.
2. `run_tracking_manager.py` invoque `Config.check_gpu_availability()` pour vérifier VRAM et providers CUDA (ONNXRuntime). En cas d’échec, les logs affichent `GPU requested but unavailable: ...`. Avec `STEP5_GPU_FALLBACK_AUTO=1` (défaut), l’exécution bascule automatiquement en CPU.
3. Lorsqu’un worker InsightFace GPU démarre, le gestionnaire injecte automatiquement le `LD_LIBRARY_PATH` contenant les bibliothèques CUDA empaquetées dans `insightface_env` et les chemins système détectés.

⚠️ **Contraintes GPU** :
- **GPU réservé exclusivement à InsightFace** — tous les autres moteurs utilisent le CPU
- 1 worker GPU séquentiel uniquement (pas de parallélisation)
- Nécessite NVIDIA GPU avec CUDA 12.0+ et ≥2 Go VRAM libres (4 Go recommandés pour coexister avec STEP2/NVENC)
- Installation de `onnxruntime-gpu` dans `insightface_env`
- CPU-only reste recommandé pour batch processing de 10+ vidéos

## Moteurs de Détection Faciale

### Moteurs Disponibles

1. **MediaPipe Face Landmarker** (par défaut)
   - Utilise `face_landmarker_v2_with_blendshapes.task`
   - Support natif des blendshapes ARKit
   - Optimisé pour la détection en temps réel
   - **Mode CPU-only** : l'accélération GPU n'est plus supportée pour MediaPipe (réservée à InsightFace).

2. **OpenCV Haar Cascade**
   - Moteur de base pour la détection de visages
   - Moins précis mais très rapide
   - Utile pour les cas simples ou le matériel limité

3. **OpenCV YuNet**
   - Détecteur de visages basé sur CNN
   - Modèle : `face_detection_yunet_2023mar.onnx`
   - Configurable via `STEP5_YUNET_MODEL_PATH`

4. **OpenCV YuNet + PyFeat**
   - Combine YuNet pour la détection et PyFeat pour les expressions
   - Extrait des blendshapes avancés
   - Activation : `--face_engine opencv_yunet_pyfeat`
   - Mode hybride : détection YuNet reste sur CPU (OpenCV), mais FaceMesh ONNX et py-feat peuvent tirer parti du GPU (`CUDAExecutionProvider` / PyTorch CUDA) lorsque `use_gpu=True`, offrant ~5-6× de gains sur l’extraction de blendshapes.

5. **OpenSeeFace**
   - Alternative open source complète
   - Nécessite des modèles spécifiques dans `STEP5_OPENSEEFACE_MODELS_DIR`
   - Activation : `--face_engine openseeface`
   - Compatibilité GPU conditionnelle : si `onnxruntime-gpu` est installé, les sessions ONNX utilisent `CUDAExecutionProvider` (log explicite). Sinon, le worker reste en CPU sans interrompre l’exécution.

6. **EOS (3D Morphable Model)**
   - Modèle 3D paramétrique pour l'ajustement précis des expressions
   - Utilise YuNet pour la détection initiale puis ajuste 68 points 3D
   - S'exécute dans un **environnement dédié `eos_env`** (routé automatiquement par `run_tracking_manager.py`, override possible via `STEP5_EOS_ENV_PYTHON`)
   - Activation : `--face_engine eos` ou `STEP5_TRACKING_ENGINE=eos`
   - Variables d'environnement clés :
     ```env
     STEP5_EOS_MODELS_DIR=workflow_scripts/step5/models/engines/eos/share   # peut pointer vers /home/kidpixel6/kidpixel_assets/eos/share
     STEP5_EOS_SFM_MODEL_PATH=${STEP5_EOS_MODELS_DIR}/sfm_model.bin
     STEP5_EOS_EXPRESSION_BLENDSHAPES_PATH=${STEP5_EOS_MODELS_DIR}/expression_blendshapes_57.bin
     STEP5_EOS_LANDMARK_MAPPER_PATH=${STEP5_EOS_MODELS_DIR}/ibug_to_eos_landmarks.json
     STEP5_EOS_EDGE_TOPOLOGY_PATH=${STEP5_EOS_MODELS_DIR}/sfm_3448_edge_topology.json
     STEP5_EOS_MODEL_CONTOUR_PATH=${STEP5_EOS_MODELS_DIR}/sfm_model_contours.json
     STEP5_EOS_CONTOUR_LANDMARKS_PATH=${STEP5_EOS_MODELS_DIR}/ibug_to_eos_contour_landmarks.json
     STEP5_EOS_FIT_EVERY_N=2                         # fallback auto sur STEP5_BLENDSHAPES_THROTTLE_N si absent
     STEP5_EOS_MAX_WIDTH=1280                        # downscale + rescale coordonnées/landmarks
     STEP5_EOS_MAX_FACES=1                           # optionnel
     STEP5_ENABLE_PROFILING=1                        # logs [PROFILING] toutes les 20 frames (YuNet, FaceMesh, fit eos)
     ```
   - Exporte `tracked_objects[].eos = {shape_coeffs, expression_coeffs}` et `landmarks` 68x3 (toujours rescalés).
   - Les assets peuvent être installés hors repo (NAS/SSD). Il suffit d'ajuster `STEP5_EOS_MODELS_DIR`.
   - `workflow_scripts/step5/process_video_worker_multiprocessing.py` charge `.env` côté worker pour propager l'ensemble de ces variables à chaque sous-processus.

   > 💤 **Lazy import MediaPipe** : `process_video_worker.py` dispose de `_ensure_mediapipe_loaded(required=False)` afin d’éviter l’import du module tant que le moteur MediaPipe/objets n’est pas sollicité. Les moteurs OpenCV/EOS l’appellent en mode `required=False`, ce qui supprime les crashs TensorFlow lorsque seules les dépendances OpenCV sont installées. Quand MediaPipe est indispensable (`required=True`), l’erreur est loggée puis relancée pour guider l’utilisateur.

7. **InsightFace (GPU-only, réintroduit en v4.2)**
   - Détecteur + embeddings InsightFace `antelopev2` (SCRFD + glintr100) piloté par ONNX Runtime **CUDA**.
   - **GPU obligatoire** : si le provider CUDA échoue, le manager abandonne l’exécution avec une erreur explicite (pas de fallback CPU).
   - Routage dédié via `insightface_env` (créé sous `VENV_BASE_DIR/insightface_env`). Override possible avec `STEP5_INSIGHTFACE_ENV_PYTHON`.
   - Activation : `STEP5_TRACKING_ENGINE=insightface` (ou bouton dans l’UI).  
     ➜ Le manager force automatiquement le mode GPU unique et désactive le thread CPU.
   - Commandes InsightFace (tests rapides) :
     ```bash
     python - <<'PY'
     from insightface.app import FaceAnalysis
     app = FaceAnalysis(name='antelopev2')
     app.prepare(ctx_id=0, det_size=(640, 640))
     print(app.models.keys())
     PY
     ```

   ```env
   STEP5_TRACKING_ENGINE=insightface

   STEP5_ENABLE_GPU=1
   STEP5_GPU_ENGINES=mediapipe_landmarker,openseeface,opencv_yunet_pyfeat,insightface

   STEP5_GPU_MAX_VRAM_MB=3072        # GTX 1650 (4 Go) : laisse 1 Go pour le système
   STEP5_GPU_PROFILING=1             # Ajoute les logs [GPU] et [PROFILING]

   # STEP5_INSIGHTFACE_ENV_PYTHON=/mnt/venv_ext4/insightface_env/bin/python

   STEP5_INSIGHTFACE_MODEL_NAME=antelopev2
   STEP5_INSIGHTFACE_CTX_ID=0
   STEP5_INSIGHTFACE_DET_SIZE=640
   STEP5_INSIGHTFACE_MAX_WIDTH=1280
   STEP5_INSIGHTFACE_MAX_FACES=4
   STEP5_INSIGHTFACE_DETECT_EVERY_N=2
   STEP5_INSIGHTFACE_JAWOPEN_SCALE=1.0
   ```

   Bonnes pratiques :
   - **VRAM** : ajuster `STEP5_GPU_MAX_VRAM_MB` en fonction du GPU. Sur RTX 30xx/40xx, 4096–6144 Mo permettent d’éviter les OOM lors de runs prolongés.
   - **Tests courts** : pour valider rapidement la pile InsightFace, vous pouvez générer un clip de 100 frames via `ffmpeg -frames:v 100` et pointer `--videos_json_path` vers ce clip. Les temps de détection doivent se stabiliser autour de 80–90 ms/frame si CUDA est bien actif.
   - **Logs** : surveiller `logs/step5/manager_tracking_<ts>.log` pour vérifier la présence de `CUDAExecutionProvider`. En cas d’erreur `libcufft.so.11`, vérifier l’injection `LD_LIBRARY_PATH` (le manager ajoute automatiquement les libs `nvidia/*/lib` + `/usr/local/cuda-12.x/targets/.../lib`).

### Gestionnaire STEP5 & Routage des Environnements

- `workflow_scripts/step5/run_tracking_manager.py` charge automatiquement `config.settings` pour récupérer les chemins des virtualenvs via `config.get_venv_python(<venv>)`.  
  - ✅ `tracking_env` est la valeur par défaut.  
  - ✅ Lorsque `STEP5_TRACKING_ENGINE=eos`, le gestionnaire bascule sur `eos_env` (override possible via `STEP5_EOS_ENV_PYTHON`).  
  - ✅ Lorsque `STEP5_TRACKING_ENGINE=insightface`, le gestionnaire bascule sur `insightface_env` (override possible via `STEP5_INSIGHTFACE_ENV_PYTHON`).
  - ✅ Aucun chemin `env/bin/python` ne doit être hardcodé : déplacez simplement vos venvs et mettez `VENV_BASE_DIR=/mnt/cache/venv/workflow_mediapipe` dans `.env` ou votre environnement système.
- Dès le démarrage, le planificateur dynamique crée **un thread GPU séquentiel** (si `STEP5_ENABLE_GPU=1` + moteur autorisé) et **un thread CPU** qui alimente des workers multiprocessing. Le nombre de processus internes dépend directement de `TRACKING_CPU_WORKERS` (15 par défaut via `app_new.py`) et est propagé jusqu’aux workers via l’argument `--mp_num_workers_internal`. Même en mode GPU, `TRACKING_CPU_WORKERS` reste utilisé lorsque le fallback object detector est actif pour paralléliser les détections MediaPipe Tasks.
- En mode GPU, **seul InsightFace est autorisé**. Tous les autres moteurs (`mediapipe_landmarker`, `openseeface`, `opencv_yunet_pyfeat`, `opencv_haar`, `eos`) sont automatiquement forcés en CPU avec le log `GPU mode is reserved for InsightFace only`. Les logs pour InsightFace indiquent `GPU mode requested...` puis `✓ GPU mode ENABLED` ou fallback CPU si le GPU est indisponible.
- Les bornes de chunk (`TRACKING_CHUNK_MIN/MAX`) et le nombre de workers (`TRACKING_CPU_WORKERS`) sont propagés depuis `app_new.py` jusqu’aux workers via l’environnement et les arguments CLI générés (`--chunk_size 0` active le mode adaptatif décrit ci-dessous).
- Les logs normalisés permettent de suivre la progression :
  - `[Progression-MultiLine] video_a.mp4: 43% || video_b.mp4: 7%`
  - `[Gestionnaire] Succès pour video_a.mp4` / `[Gestionnaire] Échec pour video_b.mp4`
  - `[Progression]|43|video_a.mp4|chunk=2/5` (consommé par `app_new.py` pour la progression fractionnaire)
- Pensez à archiver ces logs (`logs/step5/manager_tracking_<timestamp>.log`) lorsqu’un run doit être audité.

### Configuration des Moteurs

```python

STEP5_YUNET_MODEL_PATH=models/face_detectors/opencv/face_detection_yunet_2023mar.onnx
STEP5_OPENSEEFACE_MODELS_DIR=models/engines/openseeface/
STEP5_EOS_MODEL_DIR=models/eos/
STEP5_BLENDSHAPES_THROTTLE_N=20  # Ne calcule les blendshapes que toutes les N frames


STEP5_ENABLE_GPU=0
STEP5_GPU_ENGINES=insightface
STEP5_GPU_MAX_VRAM_MB=2048
STEP5_GPU_FALLBACK_AUTO=1
```

## Optimisation des Performances

### Mode CPU Unifié (v4.1+)

**Améliorations majeures** :
- Tous les moteurs utilisent maintenant le multiprocessing
- Gestion unifiée des workers via `--mp_num_workers_internal` (défaut: 15)
- Optimisation mémoire pour le traitement par lots

**Configuration recommandée** :
```env
# Nombre de workers pour le traitement parallèle
MP_NUM_WORKERS_INTERNAL=15

# Désactiver le GPU pour forcer le mode CPU (recommandé)
TRACKING_DISABLE_GPU=1

# Limiter la résolution maximale pour YuNet/OpenSeeFace/EOS
STEP5_YUNET_MAX_WIDTH=640
STEP5_OPENSEEFACE_MAX_WIDTH=640
STEP5_EOS_MAX_WIDTH=640
```

### Profilage et Métriques

Le profilage peut être activé avec :
```env
STEP5_ENABLE_PROFILING=1
```

Les métriques sont enregistrées dans les logs avec le tag `[PROFILING]` :
- Temps moyen par frame
- Utilisation mémoire
- Taux de succès de détection
- Utilisation des workers

### Registre des Détecteurs d'Objets

Le système inclut un registre de modèles de détection d'objets utilisés en fallback :

```python
# Exemple d'utilisation du registre
from workflow_scripts.step5.object_detector_registry import ObjectDetectorRegistry

# Obtenir les spécifications d'un modèle
spec = ObjectDetectorRegistry.get_model_spec('efficientdet_lite2')

# Résoudre le chemin du modèle (vérifie les surcharges)
model_path = ObjectDetectorRegistry.resolve_model_path('efficientdet_lite2')
```

**Modèles disponibles** :
- `efficientdet_lite0` à `efficientdet_lite4` (modèles légers pour CPU)
- `ssd_mobilenet_v3`
- `yolo11n_tflite`, `yolo11n_onnx`
- `nanodet-plus-m`

**Configuration** :
```env
# Activer la détection d'objets (MediaPipe uniquement)
STEP5_ENABLE_OBJECT_DETECTION=1

# Sélectionner le modèle (doit être dans le registre)
STEP5_OBJECT_DETECTOR_MODEL=efficientdet_lite2

# Optionnel : surcharger le chemin du modèle
# STEP5_OBJECT_DETECTOR_MODEL_PATH=/chemin/vers/modele.tflite
```

Lorsque les moteurs OpenCV ne détectent aucun visage, `process_video_worker.py` tente automatiquement d’initialiser un `ObjectDetector` MediaPipe via `_ensure_mediapipe_loaded(required=False)`. Si la création réussit, les détections d’objets sont converties (bbox, centroid, label, confidence) et fusionnées avec la sortie du moteur en amont avant l’appel à `apply_tracking_and_management()`, évitant ainsi les frames “vides”. En cas d’échec (MediaPipe non installé ou modèle manquant), un avertissement est loggé mais le traitement continue en conservant un JSON dense.
- **Mode GPU + fallback multi-thread** : quand `STEP5_ENABLE_OBJECT_DETECTION=1` et que le worker est lancé avec `--use_gpu`, le gestionnaire propage `mp_num_workers_internal=TRACKING_CPU_WORKERS` afin de créer un pool de threads (`queue.Queue` + `threading.Thread`) qui consomment chacun leur propre instance `ObjectDetector` en `VisionRunningMode.IMAGE`. Ce mode supprime les warnings `Input timestamp must be monotonically increasing` rencontrés avec `RunningMode.VIDEO` et améliore la latence du fallback en exploitant tous les cœurs CPU disponibles, tout en conservant un worker GPU séquentiel pour la détection principale.

### Chunking adaptatif & bornes API

- **Activation** : lorsque `run_tracking_manager.py` lance un worker CPU multiprocess, il ajoute `--chunk_size 0`. Côté worker, un chunking adaptatif calcule automatiquement une taille de lot pour créer ~5 chunks par worker (avec un minimum global de 20 chunks) et applique les bornes `chunk_min/chunk_max`.
- **Borniers** :
  - via `.env` : `TRACKING_CHUNK_MIN` et `TRACKING_CHUNK_MAX` (valeurs positives, ignorées si non définies) ;
  - via API : `POST /api/step5/chunk_bounds` (voir section dédiée) qui alimente `WorkflowService.set_step5_chunk_bounds()` et persiste les valeurs dans `WorkflowState`.
- **Flux complet** : UI → `WorkflowService` → `app_new.py` → variables d’environnement → `run_tracking_manager.py` → arguments CLI (`--chunk_min`, `--chunk_max`) → worker multiprocessing.
- **Bénéfices** : saturation homogène des workers, réduction du temps perdu sur les vidéos courtes, et absence de fragmentation extrême sur les vidéos longues (>10k frames). Les logs contiennent toujours la ligne `Adaptive chunking enabled … selected_chunk_size=XXX`, utile pour vérifier l’application des bornes.

### Configuration Recommandée
- **CPU** : 8+ cœurs (15 workers internes par défaut)
- **Mémoire** : 16+ Go de RAM pour le traitement parallèle

### Mécanisme de Warmup pour cv2.VideoCapture

**Problème** : 
- Sur certains MP4, `cv2.VideoCapture().set(CAP_PROP_POS_FRAMES, start_frame)` peut échouer silencieusement
- Problème particulièrement fréquent avec les vidéos encodées avec certains codecs

**Solution** :
```python
def process_frame_chunk(video_path, start_frame, end_frame):
    cap = cv2.VideoCapture(video_path)
    
    # Warmup: Lire quelques frames pour initialiser le décodeur
    for _ in range(3):
        ret = cap.grab()
        if not ret:
            break
    
    # Positionnement précis après le warmup
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    # Vérification de la position
    actual_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
    if actual_frame != start_frame:
        # Fallback: Lire les frames une par une si nécessaire
        cap.release()
        cap = cv2.VideoCapture(video_path)
        for _ in range(start_frame):
            ret = cap.grab()
            if not ret:
                break
    
    # Traitement des frames...
    for _ in range(start_frame, end_frame):
        ret, frame = cap.read()
        if not ret:
            break
        # Traitement de la frame...
    
    cap.release()
```

**Avantages** :
- Garantit un positionnement précis des frames
- Évite les erreurs silencieuses de lecture vidéo
- Améliore la fiabilité du traitement par lots (chunking)
- **GPU** : Désactivé par défaut pour une meilleure stabilité

#### Robustesse du worker multiprocessing

- `process_video_worker_multiprocessing.py` recharge le `.env` avant toute lecture de variables pour que chaque sous-processus voie les mêmes valeurs (profiling, throttling, chemins modèles). Il injecte également dynamiquement toutes les variables spécifiques reçues via CLI (`STEP5_OPENSEEFACE_*`, `STEP5_EOS_*`, `STEP5_ONNX_*`, etc.) dans `os.environ` avant d’instancier le moteur, garantissant que les workers multiprocessing utilisent exactement la même configuration que le processus parent.  
- Lorsqu'une frame est illisible, le worker ré-ouvre la vidéo, tente `frame_idx-1`, puis recourt à `CAP_PROP_POS_MSEC` avant d'insérer un placeholder vide en fin de vidéo afin de préserver un JSON dense (`tracked_objects` présent pour chaque index).  
- Les logs `[WORKER-XXXX]` tracent les retries et rappellent quelle portion (`chunk_start`, `chunk_end`) est traitée, ce qui permet de corréler rapidement un éventuel `WARNING Failed to read frame` avec la vidéo incriminée.

### Variables d'Environnement
```bash
# Désactive l'utilisation du GPU
export TRACKING_DISABLE_GPU=1

# Définit le nombre de workers CPU (défaut: 15)
export TRACKING_CPU_WORKERS=15

# Optimisation pour TensorFlow (si utilisé)
export TF_GPU_THREAD_MODE=gpu_private
```

#### Chargement automatique du `.env` dans les workers

Les scripts d'exécution (`workflow_scripts/step5/face_engines.py` et `workflow_scripts/step5/process_video_worker_multiprocessing.py`)
chargent désormais explicitement le fichier `.env` **avant** de lire la moindre variable d'environnement.
Cette mesure garantit que les processus enfants créés par `ProcessPoolExecutor` reçoivent bien les flags
de profiling, de throttling ou de configuration OpenSeeFace, même lorsque STEP5 est lancé depuis un autre
répertoire de travail.

- Aucun paramétrage supplémentaire n'est requis : assurez-vous simplement que le `.env` du projet contient les clés STEP5.
- Les logs `[WORKER-XXXX]` affichent la configuration effective au démarrage, ce qui permet de vérifier rapidement
  qu'un changement (ex. `STEP5_BLENDSHAPES_THROTTLE_N=2`) est pris en compte.

#### Paramètres de profiling & export des blendshapes

| Variable | Description | Recommandation |
| --- | --- | --- |
| `STEP5_ENABLE_PROFILING` | Active les logs `[PROFILING]` toutes les **20** frames (compatible chunking). | `1` uniquement lors d'un diagnostic de performance. |
| `STEP5_ONNX_INTRA_OP_THREADS` / `STEP5_ONNX_INTER_OP_THREADS` | Contrôle du threading ONNX Runtime pour YuNet/py-feat/OpenSeeFace. | `2/1` sur CPU 8 cœurs, augmenter `intra` pour 12+ cœurs. |
| `STEP5_BLENDSHAPES_THROTTLE_N` | Calcule les blendshapes toutes les *N* frames (cache utilisé entre temps). | `2` pour réduire la charge py-feat de ~50 %. |
| `STEP5_OPENSEEFACE_DETECT_EVERY_N` | Spécifique OpenSeeFace : fréquence d'exécution du détecteur. Si absent, retombe sur `STEP5_BLENDSHAPES_THROTTLE_N`. | Garder `2` pour benchmark CPU, `1` pour précision maximale. |
| `STEP5_BLENDSHAPES_PROFILE` / `STEP5_BLENDSHAPES_EXPORT_KEYS` | Filtre l'export JSON (`full`, `mouth`, `none`, `mediapipe`, `custom`). | Documenter le profil choisi côté intégration front. |

> **Astuce** : lorsque `STEP5_ENABLE_PROFILING=1`, surveillez les logs toutes les 20 frames pour comparer le coût
> YuNet vs FaceMesh vs py-feat et ajuster `STEP5_BLENDSHAPES_THROTTLE_N` en conséquence.

Ces paramètres s'appuient sur `utils/tracking_optimizations._filter_blendshapes_for_export()` (profil `full`, `mouth`, `mediapipe`, `custom`, etc.).  
Les tests `tests/unit/test_step5_export_verbose_fields.py` et `tests/unit/test_tracking_blendshape_profiles.py` assurent la couverture de ces combinaisons : pensez à les mettre à jour si vous ajoutez un nouveau profil ou modifiez le filtrage.

#### Downscale YuNet & OpenSeeFace

Les moteurs YuNet et OpenSeeFace partagent maintenant des limites de résolution configurables :

| Variable | Impact |
| --- | --- |
| `STEP5_YUNET_MAX_WIDTH` | Si la vidéo dépasse cette largeur, YuNet travaille sur une frame réduite, puis les `bbox/centroid` sont **rescalés** vers la résolution originale. |
| `STEP5_OPENSEEFACE_MAX_WIDTH` | Même logique côté OpenSeeFace (retombe sur `STEP5_YUNET_MAX_WIDTH` si absent) pour garantir un débit constant sur CPU modestes. |
| `STEP5_EOS_MAX_WIDTH` | Applique le même downscale lors de la détection YuNet préalable au fit EOS, avec rescale systématique des coordonnées et des landmarks 3D. |

Des logs `DEBUG` (`[WORKER-XXXX] Rescale bbox ...`) confirment la remontée des coordonnées pour YuNet, OpenSeeFace **et** EOS. Couplé à `STEP5_ENABLE_PROFILING=1`, cela permet de visualiser les timings toutes les 20 frames (détection, landmarks ONNX, fit eos) et d'identifier les goulots d'étranglement.

#### Limitation du nombre de visages & scaling `jawOpen`

Ces garde-fous évitent de saturer le CPU quand plusieurs moteurs tournent en parallèle. Ils sont tous chargés automatiquement dans les workers multiprocessing (voir logs `[WORKER-XXXX]`).

| Variable | Moteur | Description | Recommandation |
| --- | --- | --- | --- |
| `STEP5_OPENCV_MAX_FACES` | Haar, YuNet, YuNet+py-feat | Tronque la liste de visages retournée par OpenCV avant post-traitement. | `1` à `2` sur machines modestes, `None` pour tout capturer. |
| `STEP5_OPENCV_JAWOPEN_SCALE` | Haar, YuNet, YuNet+py-feat | Multiplie la valeur `jawOpen` calculée à partir des blendshapes FaceMesh/py-feat. | >1 pour lisser les faibles amplitudes (parole douce). |
| `STEP5_MEDIAPIPE_MAX_FACES` | MediaPipe Tasks | Nombre maximal de visages suivis simultanément par MediaPipe. | `4` par défaut ; descendre à `1` pour du mono-speaker. |
| `STEP5_MEDIAPIPE_MAX_WIDTH` | MediaPipe Tasks | Limite facultative similaire à YuNet pour réduire le coût d’inférence. | Laisser vide (= résolution native) sauf si CPU très limité. |
| `STEP5_MEDIAPIPE_JAWOPEN_SCALE` | MediaPipe Tasks | Ajuste `jawOpen` exactement comme pour OpenCV. | Harmoniser avec la valeur OpenCV pour comparabilité. |

> **Note** : `STEP5_OPENSEEFACE_MAX_FACES` et `STEP5_OPENSEEFACE_JAWOPEN_SCALE` restent documentés dans la section suivante. Ce tableau couvre uniquement les moteurs OpenCV/Mediapipe récemment harmonisés côté code (`face_engines.py`, `config.settings`).

Réduire la largeur à `640` offre ~69 FPS pour YuNet sur une vidéo 1080p ; remonter à `1280` privilégie la précision.
Adapter la valeur au hardware et au type de contenus (talking heads vs plans larges).

#### Tuning OpenSeeFace (profil léger)

Les variables suivantes sont exposées dans `.env` et loguées au démarrage de chaque worker :

| Variable | Description |
| --- | --- |
| `STEP5_OPENSEEFACE_MODELS_DIR`, `_DETECTION_MODEL_PATH`, `_LANDMARK_MODEL_PATH` | Résolution automatique des modèles ONNX (détection + landmarks). |
| `STEP5_OPENSEEFACE_MODEL_ID` | Sélection du modèle landmark (équilibre précision/vitesse). |
| `STEP5_OPENSEEFACE_DETECTION_THRESHOLD` | Confiance minimale pour conserver une détection. |
| `STEP5_OPENSEEFACE_MAX_FACES` | Nombre maximum de visages suivis simultanément. |
| `STEP5_OPENSEEFACE_JAWOPEN_SCALE` | Ajustement du seuil `jawOpen` pour les analyses vocales. |

> Les logs `[WORKER-XXXX] OpenSeeFace config: ...` facilitent le support : capturez-les lors d'une demande d'aide.

#### Hiérarchie des modèles STEP5

L’ensemble des modèles nécessaires à STEP5 est structuré par moteur et type pour faciliter les mises à jour :

```
workflow_scripts/step5/models/
├── face_detectors/
│   ├── mediapipe/face_landmarker_v2_with_blendshapes.task
│   └── opencv/face_detection_yunet_2023mar.onnx
├── face_landmarks/
│   └── opencv/face_landmark.onnx
├── blendshapes/
│   └── mediapipe/face_blendshapes*.onnx
├── object_detectors/
│   ├── tflite/EfficientDet-Lite*.tflite
│   ├── onnx/yolo11n*.onnx
│   └── onnx/nanodet-plus-m_416.onnx
└── engines/openseeface/
    ├── mnv3_detection_opt.onnx
    └── lm_model*.onnx
```

> **Astuce** : si vous ajoutez un modèle custom, respectez cette hiérarchie et versionnez uniquement les métadonnées (les poids volumineux peuvent être montés via volume externe).

#### Registry de détection d'objets

Le fallback object detection (MediaPipe Tasks uniquement) est centralisé dans `workflow_scripts/step5/object_detector_registry.py`. Il expose 6 modèles pré-analysés :

| Modèle | Backend | Fichier | Hardware recommandé | mAP COCO | Notes |
| --- | --- | --- | --- | --- | --- |
| `efficientdet_lite0` | TFLite | `EfficientDet-Lite0.tflite` | Edge TPU / CPU ARM | 25.69 | +50 % plus rapide que Lite2 |
| `efficientdet_lite1` | TFLite | `EfficientDet-Lite1.tflite` | Edge TPU équilibré | 30.55 | Latence ~49 ms Pixel 4 |
| `efficientdet_lite2` *(défaut)* | TFLite | `EfficientDet-Lite2-32.tflite` | CPU desktop / GPU | 33.97 | Baseline historique |
| `ssd_mobilenet_v3` | TFLite | `ssd_mobilenet_v3.tflite` | CPU ARM | 28.0 | Écosystème mature |
| `yolo11n_onnx` | ONNX | `yolo11n.onnx` | CPU desktop | 39.5 | Précision max, nécessite `onnxruntime` |
| `nanodet_plus` | ONNX | `nanodet-plus-m_416.onnx` | CPU ARM léger | 34.1 | ~25 ms sur ARM |

**Variables `.env` à déclarer** :

```bash
STEP5_ENABLE_OBJECT_DETECTION=1                       # Active le fallback (MediaPipe uniquement)
STEP5_OBJECT_DETECTOR_MODEL=efficientdet_lite2        # Nom présent dans le registry
# STEP5_OBJECT_DETECTOR_MODEL_PATH=/chemin/custom     # Optionnel : surcharge absolue/relative
```

**Priorité de résolution** : `override_path` CLI > `STEP5_OBJECT_DETECTOR_MODEL_PATH` > `workflow_scripts/step5/models/object_detectors/<backend>/...`. Chaque résolution est loguée pour audit (`[WORKER-XXXX] Using object detector model …`).

**Bonnes pratiques** :

1. Utiliser `efficientdet_lite0` sur Edge TPU/ARM pour limiter la latence.
2. Basculer vers `yolo11n_onnx` lorsqu’`onnxruntime` est disponible et que la précision prime.
3. Garder `STEP5_ENABLE_OBJECT_DETECTION=0` sur les moteurs OpenCV/OpenSeeFace : seuls les workflows MediaPipe consomment cette détection fallback.

> Pour une analyse détaillée des compromis, voir **[Alternatives GPU pour Tracking Facial Blendshapes](../optimization/Alternatives%20GPU%20pour%20Tracking%20Facial%20Blendshapes.md)**. Les tests de régression couvrant la résolution et les chemins custom se trouvent dans `tests/unit/test_object_detector_registry.py`.

### Avantages du Mode CPU-Only
- **Stabilité accrue** : Évite les problèmes de mémoire GPU
- **Prévisibilité** : Performances plus constantes
- **Compatibilité** : Fonctionne sur n'importe quelle machine
- **Évolutivité** : Mise à l'échelle linéaire avec le nombre de cœurs

### Gestion des Chunks

#### Configuration des Tailles de Chunks
```json
{
  "min": 100,    // Taille minimale de chunk en frames (par défaut: 100)
  "max": 500     // Taille maximale de chunk en frames (par défaut: 500)
}
```

#### API de Configuration
```python
# Exemple de configuration via l'API
response = requests.post(
    'http://localhost:5000/api/step5/chunk_bounds',
    json={"min": 100, "max": 500}
)
```

#### Propagation des bornes vers le sous-processus (ENV)

Lors de l'exécution, les bornes configurées peuvent être propagées au gestionnaire de tracking via des variables d'environnement si définies côté application ; le gestionnaire reprend ensuite ces valeurs et les transmet au worker multiprocessing.

```bash
# Propagation optionnelle si fixées dynamiquement par le service
export TRACKING_CHUNK_MIN=100
export TRACKING_CHUNK_MAX=500
```

Le service `WorkflowService.set_step5_chunk_bounds(min,max)` met à jour ces bornes au niveau de l'application. Lors du lancement de STEP5, `app_new.py` transmet ces valeurs au sous-processus via l'environnement si elles sont présentes.

#### Stratégie de Découpage (Adaptive Chunking)

Le worker multiprocessing utilise un **adaptive chunking** qui calcule dynamiquement la taille des chunks :

1. **Calcul cible** : vise `max(internal_workers * 5, 20)` chunks
2. **Clampage** : taille finale limitée par `--chunk_min` et `--chunk_max`
3. **Priorité des paramètres** :
   - `--chunk_size > 0` : force une taille fixe (désactive l'adaptive)
   - Sinon : adaptive avec `--chunk_min/--chunk_max`
   - Valeurs par défaut si non spécifiées : `min=20`, `max=400`

- **Chaîne de propagation** :
  1. API `/api/step5/chunk_bounds` → `WorkflowService.set_step5_chunk_bounds()`
  2. Stockage en mémoire via `WorkflowState` + variables `TRACKING_CHUNK_MIN/MAX`
  3. `app_new.py` exporte ces variables avant de lancer STEP5
  4. `run_tracking_manager.py` lit les bornes et les injecte dans la commande (`--chunk_min/--chunk_max`)
  5. `process_video_worker_multiprocessing.py` applique l’adaptive chunking avec ces limites

Les bornes effectives et la taille réelle par chunk sont tracées dans les logs `[WORKER-XXXX]` pour faciliter le support.

**Cas d'usage** :
- Petites vidéos (< min frames) : traitées en un seul chunk
- Vidéos moyennes : découpées selon calcul adaptatif
- Grandes vidéos : limitées par la borne maximale

### Surveillance des Performances
- Métriques en temps réel via l'API `/api/system_monitor`
- Journalisation détaillée dans les logs d'application
- Suivi de la mémoire et de l'utilisation CPU
- **OS** : Linux/Windows/macOS (testé sur Ubuntu 20.04+)

### Activation du Mode CPU

#### Variables d'Environnement (définies dans `app_new.py`)
- `TRACKING_DISABLE_GPU=1` — Désactive complètement l'utilisation du GPU
- `TRACKING_CPU_WORKERS=15` — Nombre de workers CPU internes par vidéo

#### Configuration via API
```bash
# Désactiver le GPU et configurer 15 workers CPU
curl -X POST http://localhost:5000/api/step5/configuration \
  -H "Content-Type: application/json" \
  -d '{"use_gpu": false, "cpu_workers": 15}'
```

### Avantages du Mode CPU Uniquement

#### 1. Stabilité Améliorée
- Élimination des problèmes de mémoire GPU partagée
- Pas de conflits entre les processus pour les ressources GPU
- Meilleure isolation entre les tâches

#### 2. Performances Prédictibles
- Pas de variation des performances due à la charge du GPU
- Meilleure scalabilité sur les serveurs multi-cœurs
- Facilité de parallélisation

#### 3. Utilisation des Ressources
- Répartition uniforme de la charge sur les cœurs CPU
- Possibilité d'ajuster dynamiquement le nombre de workers
- Meilleure gestion de la mémoire partagée

### Configuration Recommandée

#### Pour les Stations de Travail
- **CPU** : 16+ cœurs
- **RAM** : 32+ Go
- **Workers** : 15 (valeur par défaut)

#### Pour les Serveurs
- **CPU** : 32+ cœurs
- **RAM** : 64+ Go
- **Workers** : Nombre de cœurs - 1

### Monitoring des Performances
```bash
# Utilisation CPU
htop

# Utilisation mémoire
top -o %MEM

# Suivi des processus
watch -n 1 "ps -eo pid,ppid,cmd,%mem,%cpu --sort=-%cpu | head -20"
```

### Dépannage

#### Problèmes Courants
1. **Surcharge CPU**
   - Réduire le nombre de workers
   - Activer le mode basse consommation

2. **Mémoire Insuffisante**
   - Réduire la taille des chunks vidéo
   - Diminuer le nombre de workers
   - Augmenter la mémoire swap

3. **Performances Lentes**
   - Vérifier la charge système
   - S'assurer que le mode GPU est bien désactivé
   - Optimiser les paramètres de détection

### Métriques de Performance
| Métrique | Valeur Moyenne | Unité |
|----------|----------------|-------|
| FPS (CPU) | 12-18 | images/s |
| Utilisation CPU | 90-100% | % |
| Utilisation RAM | 8-12 | Go |
| Temps de Traitement (1min) | 3-5 | secondes |

### Bonnes Pratiques
- **Éviter la surcharge** : Ne pas dépasser 80% d'utilisation CPU moyenne
- **Surveillance** : Mettre en place un système de monitoring
- **Mises à jour** : Maintenir le système et les dépendances à jour
- **Tests** : Valider les performances avec un sous-ensemble de données avant le traitement complet

**Flags CLI équivalents** (si exposés par le runner):
- `--disable_gpu` — Désactivation explicite du GPU
- `--cpu_internal_workers 15` — Configuration du nombre de workers CPU

**Raison de conception**:
- Performances observées 2.1x supérieures avec CPU (15 workers) vs GPU
- Réduction significative de la consommation énergétique
- Meilleure stabilité du système
- Élimination des conflits de ressources GPU

**Configuration CPU optimisée**:
```python
CPU_OPTIMIZED_CONFIG = {
    "mp_landmarker_min_face_detection_confidence": 0.3,  # Seuils plus bas pour meilleur taux
    "mp_landmarker_min_face_presence_confidence": 0.2,   # de détection CPU
    "mp_landmarker_min_tracking_confidence": 0.3,        # 
    "object_score_threshold": 0.4,                       # Seuil plus permissif
    "mp_max_distance_tracking": 80,                      # Distance légèrement plus permissive
    "mp_num_workers_internal": 15                        # 15 workers CPU par défaut
}
```

**Note importante**: Le batching GPU+CPU n'est plus utilisé par défaut en Étape 5. L'accélération GPU reste principalement exploitée en Étape 2 (Conversion vidéo).

#### Configuration MediaPipe Face Landmarker
```python
FACE_LANDMARKER_CONFIG = {
    "mp_landmarker_num_faces": 5,                           # Nombre max de visages
    "mp_landmarker_min_face_detection_confidence": 0.5,     # Seuil détection
    "mp_landmarker_min_face_presence_confidence": 0.3,      # Seuil présence
    "mp_landmarker_min_tracking_confidence": 0.5,           # Seuil tracking
    "mp_landmarker_output_blendshapes": True                # Export blendshapes
}
```

#### Configuration Object Detection
```python
OBJECT_DETECTION_CONFIG = {
    "enable_object_detection": True,     # Activation détection objets
    "object_score_threshold": 0.5,       # Seuil de confiance objets
    "object_max_results": 5               # Nombre max d'objets détectés
}
```

#### Configuration Tracking et Gestion
```python
TRACKING_CONFIG = {
    "mp_max_distance_tracking": 70,                    # Distance max pour tracking
    "mp_frames_unseen_deregister": 7,                  # Frames avant désenregistrement
    "speaking_detection_jaw_open_threshold": 0.08      # Seuil ouverture mâchoire
}
```

#### Configuration Performance
```python
# CPU Optimizations (multiprocessing)
CPU_OPTIMIZED_CONFIG = {
    "mp_landmarker_min_face_detection_confidence": 0.3,  # Seuils plus bas
    "mp_landmarker_min_face_presence_confidence": 0.2,   # pour meilleur taux
    "mp_landmarker_min_tracking_confidence": 0.3,        # de détection CPU
    "mp_num_workers_internal": 15                        # 15 workers CPU
}

# GPU Configuration (sequential)
GPU_CONFIG = {
    "mp_num_workers_internal": 1  # Traitement séquentiel GPU
}
```

#### Système de Progression Avancé (v4.1)

L'Étape 5 implémente un système de progression sophistiqué pour gérer l'avancement global sur plusieurs vidéos, évitant les sauts visuels déroutants et fournissant une expérience utilisateur fluide.

##### Composants du Système

**Backend (`app_new.py`)**:
- **Progression Fractionnaire**: Utilisation de `progress_current_fractional` pour représenter la progression précise par vidéo
- **Garde-fous anti-100% prématuré**: Chaque contribution de fichier est limitée à 99% pendant le traitement
- **Réinitialisation après succès**: La progression fractionnaire est effacée après chaque succès pour éviter les reports
- **Initialisation robuste**: Le compteur `files_completed` est initialisé lors de la détection du total

**Frontend (`static/uiUpdater.js`)**:
- **Désactivation fallback parsing**: Pour STEP5, le parsing des pourcentages dans le texte est désactivé pendant l'exécution
- **Garde-fous UI**: La progression est limitée à 99% tant que `progress_current == progress_total` mais status ≠ 'completed'
- **Gestion spéciale STEP5**: Logique dédiée pour prévenir les sauts à 100% entre vidéos

##### Logique de Calcul de Progression

```python
# Pour chaque fichier en cours de traitement
files_completed = int(info.get('files_completed', 0))
current_file_progress = max(0.0, min(0.99, percent / 100.0))  # Max 99% pendant traitement
overall_progress = (files_completed + current_file_progress)
info['progress_current_fractional'] = max(0.0, min(float(total_files), overall_progress))
```

**Avantages**:
- Progression fluide et cumulative sur plusieurs vidéos
- Élimination des sauts intempestifs à 100%
- Meilleure expérience utilisateur avec suivi précis
- Gestion robuste des états intermédiaires

## Architecture Interne

### Structure du Code

#### Gestionnaire Principal (`run_tracking_manager.py`)
```python
def main():
    """Gestionnaire principal avec stratégie par lots roulants GPU+CPU."""
    
def launch_worker_process(video_path, use_gpu, internal_workers):
    """Lance un processus worker avec configuration optimisée."""
    
def run_job_and_monitor(job_info, processes, progress_map, lock):
    """Exécute et surveille un job de tracking."""
    
def monitor_progress(processes, progress_map, lock, total_jobs):
    """Monitoring en temps réel de la progression."""
```

#### Worker Séquentiel (`process_video_worker.py`)
```python
def main():
    """Worker principal pour traitement séquentiel (GPU) ou multi-threadé (CPU)."""
    
def process_video_multithreaded(args, video_capture, landmarker, object_detector, enhanced_speaking_detector, total_frames):
    """Traitement multi-threadé pour CPU avec ThreadPoolExecutor."""
    
class FrameProcessor:
    """Processeur de frame thread-safe pour traitement parallèle."""
```

#### Worker Multiprocessing (`process_video_worker_multiprocessing.py`)
```python
def init_worker_process(models_dir, args_dict):
    """Initialise les modèles MediaPipe pour le worker multiprocessing."""
    
def process_frame_chunk(chunk_data):
    """Traite un chunk de frames en multiprocessing avec warmup OpenCV."""
    
def process_video_multiprocessing(args, video_capture, total_frames):
    """Orchestrate le traitement multiprocessing avec export dense."""
    
def main():
    """Worker multiprocessing pour CPU avec 15 processus parallèles."""
```

### Algorithmes et Méthodes

#### Stratégie par Lots Roulants
```python
def rolling_batch_strategy():
    """
    Stratégie optimisée pour traitement parallèle GPU+CPU.
    
    Workflow:
    1. Lot 1: GPU (vidéo 1) + CPU (vidéo 2) en parallèle
    2. Lot 2: GPU (vidéo 3) + CPU (vidéo 4) en parallèle
    3. Continue jusqu'à épuisement de la queue
    
    Avantages:
    - Utilisation maximale des ressources
    - CPU 2.1x plus rapide que GPU avec 15 workers
    - Pas de conflit de ressources
    """
    while videos_to_process:
        current_batch = []
        
        # GPU job
        if videos_to_process:
            gpu_job = {'path': videos_to_process.popleft(), 'use_gpu': True}
            current_batch.append(gpu_job)
        
        # CPU job (15 workers)
        if videos_to_process:
            cpu_job = {'path': videos_to_process.popleft(), 'use_gpu': False}
            current_batch.append(cpu_job)
        
        # Exécution parallèle du lot
        execute_batch_parallel(current_batch)
```

#### Détection et Tracking Intégrés
```python
def integrated_detection_workflow(frame, frame_idx, timestamp_ms):
    """
    Workflow intégré de détection et tracking.
    
    1. Détection faciale primaire (MediaPipe Face Landmarker)
    2. Fallback détection d'objets si taux de réussite < 10%
    3. Extraction des blendshapes pour analyse de parole
    4. Application du tracking avec gestion des ID
    5. Détection de parole enrichie (audio + visuel)
    """
    
    # 1. Détection faciale
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, 
                       data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    face_result = landmarker.detect_for_video(mp_image, timestamp_ms)
    
    current_detections = []
    face_detected = False
    
    if face_result.face_landmarks:
        for i, landmarks in enumerate(face_result.face_landmarks):
            # Extraction bbox et centroid
            bbox, centroid = extract_face_bbox_and_centroid(landmarks, frame.shape)
            
            # Extraction blendshapes
            blendshapes = None
            if face_result.face_blendshapes and i < len(face_result.face_blendshapes):
                blendshapes = {bs.category_name: bs.score 
                             for bs in face_result.face_blendshapes[i]}
            
            detection = {
                "bbox": bbox,
                "centroid": centroid,
                "source_detector": "face_landmarker",
                "confidence": calculate_face_confidence(landmarks),
                "blendshapes": blendshapes,
                "landmarks": landmarks
            }
            current_detections.append(detection)
            face_detected = True
    
    # 2. Fallback détection d'objets
    if not face_detected and use_object_detection_fallback:
        object_result = object_detector.detect_for_video(mp_image, timestamp_ms)
        for detection in object_result.detections:
            # Conversion en format unifié
            object_detection = convert_object_to_detection_format(detection)
            current_detections.append(object_detection)
    
    return current_detections, face_detected
```

#### Détection de Parole Enrichie
```python
def enhanced_speaking_detection(frame_num, blendshapes, enhanced_detector):
    """
    Détection de parole multi-source avec fusion audio/visuel.
    
    Sources:
    1. Audio (STEP4): is_speech_present, active_speakers
    2. Visuel: jaw_open (blendshapes), mouth_activity
    3. Contextuel: segment de scène (STEP3)
    
    Fusion:
    - Poids audio: 60%
    - Poids visuel: 40%
    - Seuil confiance: 30%
    """
    
    if not enhanced_detector:
        # Fallback simple basé sur jaw_open
        jaw_open = blendshapes.get('jawOpen', 0.0) if blendshapes else 0.0
        return jaw_open > jaw_threshold
    
    # Détection enrichie multi-source
    result = enhanced_detector.detect_speaking(
        frame_num=frame_num,
        blendshapes=blendshapes,
        source_detector="face_landmarker"
    )
    
    return result.is_speaking, result.confidence, result.method
```

#### Gestion du Tracking et des ID
```python
def apply_tracking_and_management(active_objects, current_detections, next_id_counter, 
                                distance_threshold, frames_unseen_to_deregister):
    """
    Gestion complète du cycle de vie des objets trackés.
    
    Algorithme:
    1. Incrémentation frames_unseen pour tous les objets actifs
    2. Association détections ↔ objets existants (KDTree optimisé)
    3. Mise à jour des objets associés
    4. Création de nouveaux objets pour détections non associées
    5. Désenregistrement des objets non vus depuis N frames
    6. Génération de la sortie finale avec métadonnées
    """
    
    # Phase 1: Incrémentation frames_unseen
    for obj_id in active_objects:
        active_objects[obj_id]["frames_unseen"] += 1
    
    # Phase 2: Association via KDTree (optimisé)
    if active_objects and current_detections:
        associations = find_optimal_associations_kdtree(
            active_objects, current_detections, distance_threshold
        )
    
    # Phase 3: Mise à jour objets existants
    for obj_id, detection_idx in associations:
        update_tracked_object(active_objects[obj_id], current_detections[detection_idx])
    
    # Phase 4: Création nouveaux objets
    for unmatched_detection in unmatched_detections:
        create_new_tracked_object(active_objects, unmatched_detection, next_id_counter)
    
    # Phase 5: Désenregistrement objets perdus
    remove_lost_objects(active_objects, frames_unseen_to_deregister)
    
    # Phase 6: Génération sortie
    return generate_frame_output(active_objects)
```

### Warmup OpenCV et Retry (Multiprocessing)

#### Problème
Sur certains MP4, `cv2.VideoCapture().set(CAP_PROP_POS_FRAMES, start_frame)` peut échouer silencieusement si le décodeur n'a pas été « réveillé » par une lecture préalable.

#### Solution implémentée
```python
# Dans process_frame_chunk()
cap.read()  # Warmup obligatoire avant le seek
cap.set(cv2.CAP_PROP_POS_FRAMES, chunk_start)

# Retry si échec à la première frame du chunk
if frame_idx == chunk_start and not ret:
    cap.release()
    cap = cv2.VideoCapture(video_path)
    if cap.isOpened():
        cap.read()  # Warmup
        cap.set(cv2.CAP_PROP_POS_FRAMES, chunk_start)  # Retry
        ret, frame = cap.read()
```

#### Validation
Test unitaire `tests/unit/test_step5_mp_seek_warmup.py` vérifie que `read()` est bien appelé avant `set(CAP_PROP_POS_FRAMES)`.

### Export Dense des Frames

Pour garantir l'alignement avec STEP4, le worker multiprocessing s'assure que **toutes les frames sont exportées**, même si une frame n'a pas été traitée (chunk incomplet) :

```python
# Boucle dense sur toutes les frames
for frame_idx in range(total_frames):
    result = all_results.get(frame_idx)
    if result is None:
        # Frame manquante côté multiprocessing → export vide
        detections = []
        logging.warning(f"Missing detection results for frame {frame_idx + 1}. Output remains dense.")
    else:
        detections = result.get('detections', [])
    
    final_output["frames"].append({
        "frame": frame_idx + 1,
        "tracked_objects": tracked_for_frame if tracked_for_frame else []
    })
```

**Différence importante** :
- **Pas de détection** : frame traitée mais aucune bbox → `tracked_objects: []`
- **Frame manquante** : chunk incomplet → `tracked_objects: []` avec warning

### Gestion des Erreurs et Logging

#### Niveaux de Logging
```python
logging.INFO     # Progression normale et statistiques
logging.WARNING  # Fallback détection objets, problèmes de performance
logging.ERROR    # Échecs de traitement MediaPipe ou OpenCV
logging.CRITICAL # Modèles MediaPipe non trouvés
```

#### Types d'Erreurs Gérées
- **Modèles MediaPipe manquants** : Face landmarker ou object detector non trouvés
- **Erreurs de traitement vidéo** : Corruption, codecs non supportés
- **Erreurs de mémoire** : GPU/CPU overload, gestion gracieuse
- **Erreurs de multiprocessing** : Synchronisation, communication inter-processus
- **Erreurs de tracking** : Associations impossibles, objets corrompus

#### Structure des Logs
```
logs/step5/tracking_20240120_143022.log
```

Exemple de sortie :
```
2024-01-20 14:30:22 - INFO - --- DÉMARRAGE DU GESTIONNAIRE DE TRACKING (Stratégie par Lots Roulants) ---
2024-01-20 14:30:23 - INFO - Vidéos à traiter: 6
2024-01-20 14:30:24 - INFO - --- Démarrage du lot n°1 ---
2024-01-20 14:30:25 - INFO - Préparation du job GPU pour: video1.mp4
2024-01-20 14:30:26 - INFO - Préparation du job CPU (x15) pour: video2.mp4
2024-01-20 14:30:27 - INFO - Using multiprocessing worker with 15 processes
2024-01-20 14:30:28 - INFO - Applied CPU optimizations: lower confidence thresholds for better detection rate
2024-01-20 14:30:30 - INFO - [Progression-MultiLine]video1.mp4: Processing frame 150/2500 (6%) || video2.mp4: Processing frame 300/3000 (10%)
```

### Optimisations de Performance

#### Optimisations CPU (Multiprocessing)
- **15 workers parallèles** : Optimal pour CPU modernes (2.1x plus rapide que GPU)
- **Seuils de confiance réduits** : Meilleur taux de détection sur CPU
- **Traitement par batches** : Réduction overhead de communication
- **KDTree optimisé** : Association rapide détections ↔ objets trackés

#### Optimisations GPU (Séquentiel)
- **Traitement séquentiel** : Évite les conflits de mémoire VRAM
- **Delegate GPU** : Utilisation native des accélérations MediaPipe
- **Gestion mémoire** : Libération explicite des ressources

#### Optimisations Générales
```python
# Fallback intelligent détection objets
if face_success_rate < 0.1:  # < 10% de réussite
    enable_object_detection_fallback = True

# Threading optimisé pour CPU
if not use_gpu and internal_workers > 1:
    use_multithreading = True
    max_workers = min(internal_workers, os.cpu_count())

# Gestion mémoire vidéo
with safe_video_processing(video_path) as video_capture:
    # Traitement sécurisé avec nettoyage automatique

## Interface et Utilisation

### Paramètres d'Exécution

#### Arguments de Ligne de Commande (Gestionnaire)
```bash
python run_tracking_manager.py --videos_json_path VIDEOS_JSON

# --videos_json_path : Fichier JSON avec liste des vidéos à traiter
```

#### Arguments de Ligne de Commande (Worker)
```bash
python process_video_worker.py VIDEO_PATH --models_dir MODELS_DIR [OPTIONS]

# VIDEO_PATH : Chemin vers la vidéo à traiter
# --models_dir : Répertoire des modèles MediaPipe
# --use_gpu : Utilisation GPU (optionnel)
# --mp_landmarker_num_faces : Nombre max de visages (défaut: 5)
# --mp_landmarker_min_face_detection_confidence : Seuil détection (défaut: 0.5)
# --enable_object_detection : Activation détection objets
# --mp_num_workers_internal : Nombre de workers internes (CPU uniquement)
```

#### Exécution Automatique via Workflow
```python
# Via WorkflowService
result = WorkflowService.run_step("STEP5")

# Via API REST
curl -X POST http://localhost:5000/run/STEP5
```

#### Préparation côté service (helpers)

Avant le lancement du gestionnaire STEP5, la préparation est réalisée côté service pour fiabiliser la sélection des vidéos et la communication:

- `WorkflowService.prepare_tracking_step(base_path, keyword, subdir)` — Recherche les vidéos à traiter (ignore les vidéos déjà pourvues d'un JSON sibling) et retourne la liste.
- `WorkflowService.create_tracking_temp_file(videos)` — Crée un fichier JSON temporaire listant les vidéos, transmis au gestionnaire via `--videos_json_path`.

Ces helpers réduisent le code spécifique dans `app_new.py` et standardisent le flux de préparation.

#### Exécution Manuelle (Debug)
```bash
# Activation de l'environnement spécialisé
source tracking_env/bin/activate

# Génération du fichier JSON des vidéos (automatique dans le workflow)
python -c "
import json
from pathlib import Path
videos = [str(p) for p in Path('projets_extraits').rglob('*.mp4')]
with open('videos_to_track.json', 'w') as f:
    json.dump(videos, f, indent=2)
"

# Exécution du gestionnaire
python workflow_scripts/step5/run_tracking_manager.py --videos_json_path videos_to_track.json

# Avec logging détaillé
python workflow_scripts/step5/run_tracking_manager.py --videos_json_path videos_to_track.json 2>&1 | tee tracking.log
```

### Exemples d'Utilisation

#### Test de Tracking sur Vidéo Unique
```bash
# Préparation d'un test
mkdir -p test_tracking/docs
cp sample_video.mp4 test_tracking/docs/
cp sample_video.csv test_tracking/docs/  # Scènes (STEP3)
cp sample_video_audio.json test_tracking/docs/  # Audio (STEP4)

# Activation de l'environnement
source tracking_env/bin/activate

# Test worker direct
cd test_tracking
python ../workflow_scripts/step5/process_video_worker.py docs/sample_video.mp4 --models_dir ../workflow_scripts/step5/models

# Vérification du résultat
ls -la docs/sample_video_tracking.json
head -50 docs/sample_video_tracking.json
```

#### Comparaison Performance GPU vs CPU
```bash
# Test GPU (séquentiel)
time python process_video_worker.py video.mp4 --models_dir models --use_gpu

# Test CPU (15 workers multiprocessing)
time python process_video_worker_multiprocessing.py video.mp4 --models_dir models --mp_num_workers_internal 15

# Test CPU (multi-threadé)
time python process_video_worker.py video.mp4 --models_dir models --mp_num_workers_internal 8
```

#### Intégration dans Séquence
```javascript
pollingManager.startPolling('step5Status', async () => {
    const status = await apiService.getStepStatus('STEP5');
    if (status.status === 'running') {
        updateTrackingProgress(status.progress);
    }
}, 1000);
```

## Structure des Données de Sortie

### Optimisation de Taille des Exports JSON (v4.1.3+)

**Problématique** : Certains moteurs (`opencv_yunet_pyfeat`, `openseeface`, `eos`) exportent des données volumineuses (`landmarks`, coefficients EOS) qui sont **systématiquement supprimées par STEP6** (`json_reducer.py`).

**Solution** : Variable `STEP5_EXPORT_VERBOSE_FIELDS` pour contrôler l'export de ces données.

| Moteur | Taille avec export complet | Taille optimisée | Réduction |
|--------|---------------------------|------------------|-----------|
| `opencv_yunet_pyfeat` | ~95M | ~5M | **95%** |
| `openseeface` | ~19M | ~5M | **74%** |
| `eos` | ~24M | ~5M | **79%** |
| `mediapipe_landmarker` | ~5M | ~5M | Aucune (déjà optimisé) |

**Configuration** :
```bash
# Dans .env - Défaut recommandé (export léger)
STEP5_EXPORT_VERBOSE_FIELDS=false

# Pour debugging ou analyse approfondie uniquement
STEP5_EXPORT_VERBOSE_FIELDS=true
```

**Champs contrôlés** :
- `landmarks` : Coordonnées 3D des points faciaux (66-478 points selon moteur)
- `eos.shape_coeffs` : Coefficients de forme du modèle 3DMM
- `eos.expression_coeffs` : Coefficients d'expression du modèle 3DMM

**Compatibilité STEP6** : Totalement préservée. Les champs nécessaires pour After Effects (`id`, `centroid_x`, `bbox_width/height`, `active_speakers`) sont toujours exportés.

**Validation** : le comportement est couvert par `tests/unit/test_step5_export_verbose_fields.py`, qui vérifie toutes les variantes (`true/false/1/0/...`) et garantit la présence des champs requis par STEP6 même lorsque les données volumineuses sont supprimées.

## Hiérarchie des Modèles STEP5

```
workflow_scripts/step5/models/
├── face_detectors/
│   ├── mediapipe/face_landmarker_v2_with_blendshapes.task
│   └── opencv/face_detection_yunet_2023mar.onnx
├── face_landmarks/
│   └── opencv/face_landmark.onnx
├── blendshapes/
│   ├── mediapipe/face_blendshapes*.onnx
│   └── opencv/pyfeat_models/...
├── object_detectors/ (tflite, onnx, tensorflow)
├── engines/
│   ├── openseeface/
│   ├── eos/
└── metadata/labelmap.txt
```

| Variables .env | Répertoire | Description |
| --- | --- | --- |
| `STEP5_YUNET_MODEL_PATH` | `face_detectors/opencv/` | ONNX YuNet (détection CPU). |
| `STEP5_OPENSEEFACE_MODELS_DIR`, `STEP5_OPENSEEFACE_*_PATH` | `engines/openseeface/` | Modèles detection/landmarks OpenSeeFace. |
| `STEP5_EOS_MODELS_DIR`, `STEP5_EOS_*_PATH` | `engines/eos/` | Assets EOS 3DMM (peuvent pointer vers un dossier externe). |
| `STEP5_OBJECT_DETECTOR_MODEL(_PATH)` | `object_detectors/<backend>/` | Résolution via `ObjectDetectorRegistry`. |

> **Bonne pratique** : garder la structure intacte dans le repo et utiliser uniquement des overrides `.env` (relatifs ou absolus) lorsque les modèles sont placés sur un SSD externe. Les workers STEP5 résolvent d'abord les overrides, puis les chemins du repo.

### Format JSON de Sortie (v4.1+)

Le format de sortie a été mis à jour pour inclure des métriques supplémentaires et une meilleure organisation des données :

```json
{
  "metadata": {
    "version": "4.1",
    "engine": "eos",  // ou "mediapipe", "openseeface", etc.
    "fps": 30,
    "total_frames": 1000,
    "processing_time_sec": 45.2,
    "blendshapes_profile": "arkit",
    "detection_stats": {
      "face_detection_rate": 0.95,
      "avg_faces_per_frame": 1.2,
      "object_detection_fallback_used": false
    },
    "performance_metrics": {
      "avg_frame_processing_ms": 45.2,
      "max_memory_usage_mb": 1200,
      "cpu_utilization_percent": 85.5
    }
  },
  "frames": [
    {
      "frame_number": 1,
      "timestamp_ms": 33.33,
      "faces": [
        {
          "bounding_box": [x, y, width, height],
          "landmarks": [[x, y, z], ...],  // 468 points
          "blendshapes": {
            "eyeBlinkLeft": 0.8,
            "mouthSmile": 0.6,
            // ... autres blendshapes ARKit
          },
          "rotation": [pitch, yaw, roll],
          "translation": [x, y, z],
          "tracking_id": 1,
          "detection_confidence": 0.98
        }
      ],
      "objects": [
        {
          "class": "person",
          "score": 0.92,
          "bounding_box": [x, y, width, height],
          "tracking_id": 2
        }
      ]
    }
  ]
}
```

### Métriques de Performance

Les métriques suivantes sont maintenant incluses dans le fichier de sortie :

1. **Taux de détection** : Pourcentage de frames où au moins un visage a été détecté
2. **Utilisation CPU** : Moyenne et pics d'utilisation du processeur
3. **Mémoire** : Utilisation maximale de la RAM
4. **Débit** : Temps moyen de traitement par frame
5. **Statistiques de suivi** : Nombre moyen de visages par frame, utilisation du fallback de détection d'objets

### Ancien Format (Obsolète)

> **Note** : Les versions précédentes pouvaient contenir des champs obsolètes comme `processing_info`, `frames_tracked`, `frames_unseen`, etc. Ces champs ne sont plus utilisés dans la version 4.1+.

```json
{
  "metadata": {
    "video_path": "/path/to/video1.mp4",
    "total_frames": 2500,
    "fps": 25.0,
    "tracking_engine": "mediapipe_landmarker"
  },
  "frames": [
    {
      "frame": 1,
      "tracked_objects": []
    },
    {
      "frame": 125,
      "tracked_objects": [
        {
          "id": "obj_1",
          "bbox_xmin": 100,
          "bbox_xmax": 300,
          "centroid_x": 200,
          "centroid_y": 275,
          "source_detector": "face_landmarker",
          "label": "face",
          "confidence": 0.92,
          "is_speaking": true,
          "speaking_confidence": 0.87,
          "speaking_method": "audio_primary",
          "speaking_sources": ["audio", "blendshapes"],
          "blendshapes": {
            "jawOpen": 0.12,
            "mouthSmileLeft": 0.05,
            "mouthSmileRight": 0.04,
            "eyeBlinkLeft": 0.02,
            "eyeBlinkRight": 0.01
          }
        }
      ]
    },
    {
      "frame": 200,
      "tracked_objects": [
        {
          "id": "obj_2",
          "bbox_xmin": 150,
          "bbox_xmax": 330,
          "centroid_x": 240,
          "centroid_y": 210,
          "source_detector": "object_detector",
          "label": "person",
          "confidence": 0.78
        }
      ]
    }
  ]
}
```

#### Description des Champs

##### Métadonnées
- **video_path** : Chemin complet vers la vidéo traitée
- **total_frames** : Nombre total de frames dans la vidéo
- **fps** : Framerate de la vidéo
- **tracking_engine** : Moteur utilisé (`mediapipe_landmarker`, `opencv_haar`, `opencv_yunet`, `opencv_yunet_pyfeat`, `openseeface`)

##### Données par Frame
- **frame** : Numéro de frame (base 1)
- **tracked_objects** : Array des objets trackés dans cette frame (vide si aucune détection)

##### Objets Trackés
- **id** : Identifiant unique persistant (chaîne, ex: `"obj_1"`, `"obj_2"`)
- **bbox_xmin**, **bbox_xmax**, **bbox_width**, **bbox_height** : Coordonnées et dimensions de la bounding box
  - Seuls `bbox_xmin` et `bbox_xmax` sont garantis pour les visages MediaPipe (compatibilité historique)
- **centroid_x**, **centroid_y** : Centre de l'objet
- **source** : Source de détection exportée dans le JSON (`"face_landmarker"` ou `"object_detector"`)
  - **Note** : en interne, les détections sont produites avec `source_detector`; lors de l’export final (`apply_tracking_and_management`), le champ sérialisé est `source`.
- **label** : Étiquette (`"face"` pour les visages, nom de classe pour les objets)
- **confidence** : Confiance de la détection (0.0-1.0)
- **is_speaking** : Booléen (uniquement pour les visages avec détection de parole)
- **speaking_confidence** : Confiance de la détection de parole (0.0-1.0)
- **speaking_method** : Méthode utilisée (`"audio_primary"`, `"visual_primary"`, `"blendshapes"`, `"no_blendshapes"`, etc.)
- **speaking_sources** : Liste des sources utilisées pour la décision (`["audio"]`, `["blendshapes"]`, `["audio","blendshapes"]`)
- **blendshapes** : Coefficients d'animation faciale (voir section **Filtrage Blendshapes** ci-dessous)
- **landmarks** : Points de repère faciaux 3D (uniquement pour les moteurs qui les fournissent, ex: `opencv_yunet_pyfeat`, `openseeface`)

> **Note `openseeface`** :
> - Les landmarks sont une liste de 66 points, exportés au format `[x, y, z]` avec `z=0.0`.
> - Les blendshapes sont exportées au format ARKit 52 clés (compatibilité JSON). Seule `jawOpen` est actuellement estimée (les autres clés valent `0.0`).

> **Important** : Pour les objets non-faciaux (`source_detector: "object_detector"`), les champs `is_speaking`, `speaking_*`, et `blendshapes` sont **absents** (pas `null`).

#### Filtrage Blendshapes (export JSON)

Le champ `blendshapes` peut être filtré à l’export via des variables d’environnement. Cela permet de réduire la taille des JSON ou de se concentrer sur des régions d’intérêt (ex: bouche pour la parole).

| Variable | Valeurs possibles | Comportement |
|----------|-------------------|--------------|
| `STEP5_BLENDSHAPES_PROFILE` | `full` (défaut) | Exporte toutes les clés blendshapes détectées |
| | `mouth` | Exporte uniquement les clés commençant par `mouth*` ou `jaw*` |
| | `none` | Désactive l’export (`blendshapes: null`) |
| | `mediapipe` | Supprime `tongueOut`, ajoute `_neutral: 0.0` si absent |
| | `custom` | Exporte une whitelist définie via `STEP5_BLENDSHAPES_EXPORT_KEYS` |
| `STEP5_BLENDSHAPES_INCLUDE_TONGUE` | `1`/`true`/`yes` (optionnel) | Avec profil `mouth`, inclut `tongueOut` si présent |
| `STEP5_BLENDSHAPES_EXPORT_KEYS` | `key1,key2,...` (séparé par des virgules) | Whitelist pour profil `custom` |

**Exemples pratiques**

```bash
# .env : ne garder que la bouche (utile pour analyse parole)
STEP5_BLENDSHAPES_PROFILE=mouth
STEP5_BLENDSHAPES_INCLUDE_TONGUE=1

# .env : désactiver les blendshapes (économie de taille)
STEP5_BLENDSHAPES_PROFILE=none

# .env : export personnalisé (mâchoire + sourires)
STEP5_BLENDSHAPES_PROFILE=custom
STEP5_BLENDSHAPES_EXPORT_KEYS=jawOpen,mouthSmileLeft,mouthSmileRight
```

**Résultat JSON (profil `mouth` avec langue)**

```json
{
  "blendshapes": {
    "jawOpen": 0.12,
    "mouthSmileLeft": 0.05,
    "mouthSmileRight": 0.04,
    "tongueOut": 0.01
  }
}
```

> **Note technique** : Le filtrage est appliqué dans `utils/tracking_optimizations._filter_blendshapes_for_export()` **après** la détection, donc il ne modifie pas les calculs internes (ex: EnhancedSpeakingDetector).

### Métriques de Progression et Monitoring

#### Indicateurs de Progression Console (Gestionnaire)
```python
# Sortie standardisée pour l'interface utilisateur
print(f"[Progression-MultiLine]{' || '.join(progress_parts)}")
# Exemple: video1.mp4: Processing frame 150/2500 (6%) || video2.mp4: Processing frame 300/3000 (10%)
```

#### Indicateurs de Progression Console (Worker)
```python
# Progression détaillée par worker
print(f"Processing frame {frame_idx + 1}/{total_frames} ({progress_percent:.1f}%)")
print(f"Face detection success rate: {face_success_rate:.1%}")
print(f"Enhanced speaking detection initialized")
```

#### Métriques de Performance
```python
# Statistiques de détection
logging.info(f"Face detection success rate: {face_success_rate:.1%}")
logging.info(f"Object detection fallback enabled due to low face detection rate")
logging.info(f"Using multiprocessing worker with {internal_workers} processes")

# Temps de traitement
start_time = time.time()
# ... traitement ...
processing_time = time.time() - start_time
logging.info(f"Video processing completed in {processing_time:.2f} seconds")
```

#### Monitoring via Logs Structurés
```python
# Progression détaillée
logging.info(f"--- Démarrage du lot n°{lot_number} ---")
logging.info(f"Préparation du job {worker_type_log} pour: {video_name}")
logging.info(f"Applied CPU optimizations: lower confidence thresholds for better detection rate")
logging.info(f"Enhanced speaking detection initialized")
```

## Dépendances et Prérequis

### Logiciels Externes Requis

#### MediaPipe (Obligatoire)
```bash
# Installation via pip
pip install mediapipe

# Vérification de l'installation
python -c "import mediapipe as mp; print(f'MediaPipe version: {mp.__version__}')"
```

#### OpenCV (Obligatoire)
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3-opencv

# Via pip
pip install opencv-python

# Vérification
python -c "import cv2; print(f'OpenCV version: {cv2.__version__}')"
```

#### Support GPU NVIDIA (Optionnel)
```bash
# Vérification du support CUDA
nvidia-smi
python -c "import cv2; print(cv2.cuda.getCudaEnabledDeviceCount())"

# Installation des drivers NVIDIA
sudo apt install nvidia-driver-470
```

### Versions Spécifiques des Bibliothèques

#### Requirements Python (tracking_env/)
```txt
# Computer Vision et ML
mediapipe>=0.10.0
opencv-python>=4.5.0
numpy>=1.21.0

# Traitement parallèle
concurrent.futures  # Inclus dans Python 3.2+
multiprocessing     # Inclus dans Python standard

# Utilitaires
pathlib2>=2.3.7    # Pour compatibilité
scipy>=1.7.0        # Pour optimisations KDTree
```

#### Installation Recommandée
```bash
# Création de l'environnement
python -m venv tracking_env
source tracking_env/bin/activate

# Installation des dépendances principales
pip install mediapipe opencv-python numpy scipy

# Vérification des installations
python -c "import mediapipe, cv2, numpy, scipy; print('All dependencies OK')"
```

### Configuration Système Recommandée

#### Ressources Minimales
- **RAM** : 8 GB minimum, 16 GB recommandé
- **CPU** : 8 cœurs minimum pour multiprocessing optimal (15 workers)
- **GPU** : NVIDIA GTX 1060 ou supérieure (optionnel)
- **Espace disque** : 2 GB pour modèles MediaPipe + espace de travail

#### Modèles MediaPipe Requis
```bash
# Structure attendue (modèles de base)
workflow_scripts/step5/models/
├── face_detectors/
│   └── mediapipe/
│       └── face_landmarker_v2_with_blendshapes.task  # ~3.6 MB (face tracking)
└── object_detectors/
    └── tflite/
        └── EfficientDet-Lite2-32.tflite              # ~23 MB (object detection fallback, default)

# Modèles alternatifs supportés (optionnels)
└── object_detectors/
    ├── tflite/
    │   ├── EfficientDet-Lite0.tflite                 # ~4.4 MB (plus rapide, Edge TPU compatible)
    │   ├── EfficientDet-Lite1.tflite                 # ~5.8 MB (équilibré)
    │   └── ssd_mobilenet_v3.tflite                   # ~5 MB (stable, CPU optimisé)
    └── onnx/
        └── yolo11n.onnx                              # ~5 MB (expérimental, ONNX Runtime requis)

# Configuration via variables d'environnement (.env)
STEP5_OBJECT_DETECTOR_MODEL=efficientdet_lite2  # Modèle par défaut (rétrocompatible)
STEP5_OBJECT_DETECTOR_MODEL_PATH=               # Override chemin (optionnel)
STEP5_ENABLE_OBJECT_DETECTION=0                 # Activer fallback object detection

# Modèles disponibles : efficientdet_lite0, efficientdet_lite1, efficientdet_lite2,
#                       ssd_mobilenet_v3, yolo11n_onnx, nanodet_plus
```

#### Choix du Modèle de Détection d'Objets

Le modèle de détection d'objets est utilisé comme **fallback** lorsque la détection de visages échoue (MediaPipe uniquement).

**Recommandations par hardware** :
- **Edge TPU / Coral** : `efficientdet_lite0` (100% compatible ops, ~50% plus rapide)
- **CPU ARM faible puissance** : `efficientdet_lite0` ou `nanodet_plus` (ONNX)
- **CPU desktop** : `efficientdet_lite0` (balance vitesse/précision) ou `yolo11n_onnx` (meilleure précision)
- **GPU** : `efficientdet_lite2` (résolution supérieure, baseline actuel)

**Exemple de configuration** :
```bash
# Dans .env pour Edge TPU
STEP5_OBJECT_DETECTOR_MODEL=efficientdet_lite0
STEP5_ENABLE_OBJECT_DETECTION=1

# Pour YOLO11 (ONNX Runtime requis)
STEP5_OBJECT_DETECTOR_MODEL=yolo11n_onnx
STEP5_OBJECT_DETECTOR_MODEL_PATH=/path/to/yolo11n.onnx
STEP5_ENABLE_OBJECT_DETECTION=1
```

#### Optimisations Système
```bash
# Augmentation des limites de processus
echo 'kernel.pid_max = 4194304' | sudo tee -a /etc/sysctl.conf

# Optimisation pour multiprocessing
echo 'kernel.shmmax = 68719476736' | sudo tee -a /etc/sysctl.conf
echo 'kernel.shmall = 4294967296' | sudo tee -a /etc/sysctl.conf

# Optimisation CPU
echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

#### Configuration GPU
```bash
# Variables d'environnement CUDA
export CUDA_VISIBLE_DEVICES=0

# Optimisation GPU MediaPipe
export TF_FORCE_GPU_ALLOW_GROWTH=true
export TF_GPU_THREAD_MODE=gpu_private
```

## Debugging et Résolution de Problèmes

### Erreurs Courantes et Solutions

#### 1. Erreur : "Modèles MediaPipe non trouvés"
```python
# Erreur
FileNotFoundError: face_landmarker.task not found

# Diagnostic
ls -la workflow_scripts/step5/models/
python -c "import mediapipe as mp; print(mp.__file__)"

# Solutions
# Télécharger les modèles manuellement
wget https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
mv face_landmarker.task workflow_scripts/step5/models/face_detectors/mediapipe/

# Vérifier les permissions
chmod 644 workflow_scripts/step5/models/face_detectors/mediapipe/*.task
```

#### 2. Erreur : "Multiprocessing spawn error"
```python
# Erreur
RuntimeError: context has already been set

# Diagnostic
python -c "import multiprocessing; print(multiprocessing.get_start_method())"

# Solutions
# Forcer la méthode de démarrage
export PYTHONPATH=$PWD
python -c "import multiprocessing; multiprocessing.set_start_method('spawn', force=True)"

# Ou utiliser le worker séquentiel
python process_video_worker.py video.mp4 --models_dir models --mp_num_workers_internal 1
```

#### 3. Erreur : "GPU memory allocation failed"
```python
# Erreur
RuntimeError: CUDA out of memory

# Diagnostic
nvidia-smi
python -c "import cv2; print(cv2.cuda.getCudaEnabledDeviceCount())"

# Solutions
# Forcer l'utilisation CPU
python process_video_worker.py video.mp4 --models_dir models  # Sans --use_gpu

# Réduire la résolution de traitement
# Ou traiter les vidéos une par une
```

#### 4. Erreur : "Low face detection rate"
```python
# Warning
Low face detection rate (8%). Enabling object detection fallback.

# Diagnostic
# C'est un comportement normal pour vidéos avec peu de visages
grep "Face detection success rate" logs/step5/tracking_*.log

# Solutions
# Ajuster les seuils de confiance
--mp_landmarker_min_face_detection_confidence 0.3
--mp_landmarker_min_face_presence_confidence 0.2

# Ou accepter le fallback vers détection d'objets
```

### Logs Spécifiques à Surveiller

#### Logs de Progression
```bash
# Progression du traitement
grep "Processing frame" logs/step5/tracking_*.log
grep "Progression-MultiLine" logs/step5/tracking_*.log
grep "Face detection success rate" logs/step5/tracking_*.log
```

#### Logs d'Optimisations
```bash
# Utilisation des optimisations
grep "Using multiprocessing worker" logs/step5/tracking_*.log
grep "Applied CPU optimizations" logs/step5/tracking_*.log
grep "Object detection fallback" logs/step5/tracking_*.log
```

#### Logs d'Erreurs
```bash
# Erreurs de traitement
grep "ERROR" logs/step5/tracking_*.log
grep "Failed to" logs/step5/tracking_*.log
grep "Exception" logs/step5/tracking_*.log
```

### Tests de Validation et Vérification

#### Test de Fonctionnement Basique
```bash
# Créer une vidéo de test avec visage
ffmpeg -f lavfi -i "testsrc=duration=5:size=640x480:rate=25" -vf "drawtext=text='TEST':fontsize=30:x=10:y=10" test_face.mp4

# Placer dans la structure attendue
mkdir -p test_tracking/docs
mv test_face.mp4 test_tracking/docs/

# Créer les fichiers prérequis (vides pour test)
echo "No,Timecode In,Timecode Out,Frame In,Frame Out" > test_tracking/docs/test_face.csv
echo '{"video_filename":"test_face.mp4","total_frames":125,"fps":25.0,"frames_analysis":[]}' > test_tracking/docs/test_face_audio.json

# Exécuter le tracking
source tracking_env/bin/activate
cd test_tracking
python ../workflow_scripts/step5/process_video_worker.py docs/test_face.mp4 --models_dir ../workflow_scripts/step5/models

# Vérifier le résultat
cat docs/test_face_tracking.json | jq '.metadata'
```

#### Test de Performance Multiprocessing
```bash
# Mesurer les performances CPU vs GPU
echo "Testing CPU multiprocessing (15 workers):"
time python process_video_worker_multiprocessing.py video.mp4 --models_dir models --mp_num_workers_internal 15

echo "Testing GPU sequential:"
time python process_video_worker.py video.mp4 --models_dir models --use_gpu

echo "Testing CPU sequential:"
time python process_video_worker.py video.mp4 --models_dir models --mp_num_workers_internal 1
```

#### Validation de l'Intégrité des Sorties
```python
#!/usr/bin/env python3
"""Script de validation pour l'étape 5."""

def validate_step5_output():
    """Valide les fichiers JSON de tracking."""
    import json
    from pathlib import Path

    base_dir = Path("projets_extraits")
    video_extensions = ['.mp4', '.mov', '.avi', '.mkv', '.webm']

    for video_file in base_dir.rglob("*"):
        if video_file.suffix.lower() in video_extensions:
            json_file = video_file.with_name(f"{video_file.stem}_tracking.json")

            if not json_file.exists():
                print(f"❌ Fichier JSON manquant pour {video_file}")
                return False

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Vérifier la structure des métadonnées
                if 'metadata' not in data or 'frames' not in data:
                    print(f"❌ Structure JSON invalide dans {json_file}")
                    return False

                metadata = data['metadata']
                required_metadata = ['video_path', 'total_frames', 'fps']
                if not all(field in metadata for field in required_metadata):
                    print(f"❌ Métadonnées manquantes dans {json_file}")
                    return False

                # Vérifier la cohérence des frames
                if len(data['frames']) != metadata['total_frames']:
                    print(f"❌ Incohérence nombre de frames dans {json_file}")
                    return False

                # Vérifier la structure des objets trackés
                total_tracked_objects = 0
                for frame_data in data['frames'][:10]:  # Vérifier les 10 premières
                    if 'tracked_objects' not in frame_data:
                        print(f"❌ Champ tracked_objects manquant dans {json_file}")
                        return False

                    for obj in frame_data['tracked_objects']:
                        required_obj_fields = ['id', 'bbox', 'centroid', 'source_detector']
                        if not all(field in obj for field in required_obj_fields):
                            print(f"❌ Champs objet manquants dans {json_file}")
                            return False
                        total_tracked_objects += 1

                print(f"✅ {json_file}: {metadata['total_frames']} frames, {total_tracked_objects} objets trackés")

            except Exception as e:
                print(f"❌ Erreur lors de la lecture de {json_file}: {e}")
                return False

    print("✅ Validation réussie: tous les fichiers JSON sont valides")
    return True

if __name__ == "__main__":
    validate_step5_output()
```

### Monitoring et Alertes

#### Surveillance des Performances CPU
```bash
# Monitoring continu pendant traitement multiprocessing
watch -n 1 'ps aux | grep process_video_worker | wc -l; echo "CPU Usage:"; top -bn1 | grep "Cpu(s)" | head -1'

# Log de l'utilisation CPU
while true; do
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
    worker_count=$(ps aux | grep process_video_worker | grep -v grep | wc -l)
    echo "$(date): CPU: $cpu_usage%, Workers: $worker_count"
    sleep 5
done > cpu_usage_tracking.log
```

#### Surveillance de la Mémoire
```bash
# Monitoring de l'utilisation mémoire
watch -n 2 'free -h; echo ""; ps aux | grep process_video_worker | head -5'

# Alerte mémoire critique
while true; do
    mem_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
    if [ $mem_usage -gt 90 ]; then
        echo "ALERTE: Utilisation mémoire critique ($mem_usage%)"
        # Optionnel: tuer les workers les plus gourmands
    fi
    sleep 30
done
```

#### Métriques de Qualité de Tracking
```bash
# Analyse des taux de détection
for json_file in projets_extraits/*/docs/*_tracking.json; do
    if [ -f "$json_file" ]; then
        face_rate=$(jq -r '.metadata.processing_info.face_detection_success_rate // 0' "$json_file")
        fallback_used=$(jq -r '.metadata.processing_info.object_detection_fallback_used // false' "$json_file")
        total_objects=$(jq -r '[.frames[].tracked_objects | length] | add' "$json_file")
        echo "$(basename "$json_file"): Face rate: $face_rate, Fallback: $fallback_used, Objects: $total_objects"
    fi
done

# Détection d'anomalies (pas d'objets trackés)
find projets_extraits/ -name "*_tracking.json" -exec sh -c 'objects=$(jq -r "[.frames[].tracked_objects | length] | add" "$1" 2>/dev/null); if [ "$objects" = "0" ] || [ "$objects" = "null" ]; then echo "ANOMALIE: $1 (aucun objet tracké)"; fi' _ {} \;
