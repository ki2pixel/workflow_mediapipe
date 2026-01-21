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

**Mode GPU (v4.2+)** : Le GPU est **strictement réservé** au moteur InsightFace. Tous les autres moteurs (MediaPipe, OpenSeeFace, OpenCV, EOS) s'exécutent en mode CPU même si `STEP5_ENABLE_GPU=1`. Le gestionnaire :
- force `args.disable_gpu=True` pour tout moteur non listé dans `STEP5_GPU_ENGINES`.
- vérifie la disponibilité matérielle via `Config.check_gpu_availability()` avant de lancer InsightFace.
- bascule automatiquement en mode CPU si `STEP5_GPU_FALLBACK_AUTO=1` et qu'une contrainte est détectée (VRAM insuffisante, absence du provider CUDA, etc.).

#### Restrictions GPU (décision 2025-12-27)
⚠️ **IMPORTANT** : Le support GPU est **réservé exclusivement à InsightFace**
- **MediaPipe Face Landmarker** : CPU-only (15 workers)
- **OpenSeeFace** : CPU-only (multiprocessing) 
- **OpenCV YuNet/PyFeat** : CPU-only
- **EOS** : CPU-only (3DMM fitting)
- Le gestionnaire force `args.disable_gpu=True` pour tous les moteurs non-InsightFace

⚠️ **Contraintes GPU** :
- 1 worker GPU séquentiel uniquement (pas de parallélisation).
- Nécessite un GPU NVIDIA (CUDA ≥ 12.0) avec ≥ 2 Go de VRAM libres (4 Go recommandés pour coexister avec STEP2/NVENC).
- `insightface_env` embarque ONNX Runtime GPU + dépendances InsightFace ; override possible via `STEP5_INSIGHTFACE_ENV_PYTHON`.
- CPU-only reste recommandé pour les batchs massifs (10+ vidéos) et demeure le mode par défaut (`TRACKING_DISABLE_GPU=1`).
- `STEP5_GPU_PROFILING=1` journalise l’usage VRAM et les timings toutes les 20 frames pour InsightFace.

## Moteurs de Détection Faciale

### Moteurs Disponibles

1. **MediaPipe Face Landmarker** (par défaut)
   - Utilise `face_landmarker_v2_with_blendshapes.task`
   - Support natif des blendshapes ARKit
   - Optimisé pour la détection en temps réel
   - **Mode CPU-only** : optimisé pour 15 workers multiprocessing.

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
   - - **Mode CPU-only** : optimisé pour 15 workers multiprocessing.

5. **OpenSeeFace**
   - Alternative open source complète
   - Nécessite des modèles spécifiques dans `STEP5_OPENSEEFACE_MODELS_DIR`
   - Activation : `--face_engine openseeface`
   - - **Mode CPU-only** : optimisé pour multiprocessing.

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

### Optimisations récentes (Décembre 2025)

| Optimisation | Description | Variables clés |
|--------------|-------------|----------------|
| Downscale YuNet / OpenSeeFace | YuNet et OpenSeeFace plafonnent la largeur d’analyse (`STEP5_YUNET_MAX_WIDTH`, `STEP5_OPENSEEFACE_MAX_WIDTH`) et rescalaient automatiquement les coordonnées/landmarks (logs DEBUG pour tracer les facteurs). | `STEP5_YUNET_MAX_WIDTH`, `STEP5_OPENSEEFACE_MAX_WIDTH` |
| Profiling généralisé | Les workers rechargent `.env` avant chaque chunk pour propager `STEP5_ENABLE_PROFILING`, `STEP5_BLENDSHAPES_THROTTLE_N`, `STEP5_EOS_*`. Logs `[PROFILING]` toutes les 20 frames, même sur de petits chunks multiprocessing. | Variables `STEP5_*` |
| Filtrage des blendshapes | `STEP5_BLENDSHAPES_PROFILE` (`full`, `mouth`, `mediapipe`, `custom`, `none`) + `STEP5_BLENDSHAPES_EXPORT_KEYS` réduisent la taille JSON (jusqu’à -95 %) tout en conservant la compatibilité STEP6. | `STEP5_BLENDSHAPES_PROFILE`, `STEP5_BLENDSHAPES_EXPORT_KEYS`, `STEP5_BLENDSHAPES_INCLUDE_TONGUE` |
| Registry Object Detector | `workflow_scripts/step5/object_detector_registry.py` centralise EfficientDet/SSD/YOLO/NanoDet et applique l’override `STEP5_OBJECT_DETECTOR_MODEL_PATH` si fourni. | `STEP5_ENABLE_OBJECT_DETECTION`, `STEP5_OBJECT_DETECTOR_MODEL`, `STEP5_OBJECT_DETECTOR_MODEL_PATH` |
| JSON allégé | `STEP5_EXPORT_VERBOSE_FIELDS=0` (défaut) supprime l’export des `landmarks`/`eos` pour les moteurs non MediaPipe afin d’accélérer STEP6 et réduire les transferts. | `STEP5_EXPORT_VERBOSE_FIELDS` |
| Warmup & seek robustes | Les workers OpenCV lisent une frame avant `cap.set()` et insèrent un placeholder si la frame est illisible, garantissant un JSON dense (1..N). | Implémenté dans `process_video_worker_multiprocessing.py` |

### Registry de détection d’objets

```
workflow_scripts/step5/object_detector_registry.py
├── efficientdet_lite0/1/2 (tflite)
├── ssd_mobilenet_v3 (tflite/tensorflow)
├── yolo11n (onnx)
└── nanodet_plus (onnx)
```

- `STEP5_OBJECT_DETECTOR_MODEL=efficientdet_lite2` pointe par défaut sur `workflow_scripts/step5/models/object_detectors/tflite/EfficientDet-Lite2-32.tflite`.
- Override absolu/relatif via `STEP5_OBJECT_DETECTOR_MODEL_PATH`.
- Le fallback MediaPipe Tasks fonctionne en mode `RunningMode.IMAGE` multi-threads (dimensionnés par `TRACKING_CPU_WORKERS`) pour InsightFace GPU, et single-thread pour les moteurs CPU historiques afin d’éviter la contention.

### JSON d’export & réduction

- `tracked_objects` reste dense : même sans détection, un tableau vide est émis par frame pour préserver l’alignement avec STEP6/7.
- `STEP5_EXPORT_VERBOSE_FIELDS=0` évite l’écriture des champs volumineux (`landmarks`, `eos`) pour la plupart des moteurs ; activer ce flag uniquement pour le debug ou lorsque STEP6 requiert un export complet.
- Les logs `[Progression-MultiLine]` signalent lorsqu’un chunk bascule en mode réduit, facilitant le suivi depuis `WorkflowState`.

### Gestionnaire STEP5 & Routage des Environnements

- `workflow_scripts/step5/run_tracking_manager.py` charge automatiquement `config.settings` pour récupérer les chemins des virtualenvs via `config.get_venv_python(<venv>)`.  
  - ✅ `tracking_env` est la valeur par défaut.  
  - ✅ Lorsque `STEP5_TRACKING_ENGINE=eos`, le gestionnaire bascule sur `eos_env` (override possible via `STEP5_EOS_ENV_PYTHON`).  
- `_EnvConfig` centralise désormais la lecture typée des variables `STEP5_*` (GPU, engines, workers, overrides). Le manager s’appuie sur cette couche pour :
  - appliquer les restrictions InsightFace GPU-only (`STEP5_ENABLE_GPU=1`, `STEP5_GPU_ENGINES`), 
  - construire un environnement subprocess via `_build_subprocess_env()` qui injecte automatiquement `LD_LIBRARY_PATH` (CUDA libs découvertes dans les venvs + chemins système `/usr/local/cuda*` lorsque nécessaire),
  - propager les limites CPU (`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, etc.) afin d’éviter la contention inter-process,
  - router chaque moteur vers son interpréteur dédié (`tracking_env`, `eos_env`, `insightface_env`, ou `STEP5_TF_GPU_ENV_PYTHON` pour MediaPipe GPU) avec vérification d’existence et messages d’erreur explicites.
- Les workers multiprocessing rechargent toujours `.env` pour récupérer ces variables à chaque fork, garantissant que les réglages (`STEP5_BLENDSHAPES_THROTTLE_N`, profil d’export, profiling) restent synchronisés même en mode chunké.
