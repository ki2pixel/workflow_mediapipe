# Documentation Technique - Étape 5 : Suivi Vidéo et Blendshapes

> **Code-Doc Context** – Part of the 7‑step pipeline; see `../README.md` for the uniform template. Backend hotspots: critical complexity in STEP5 workers (radon F/E), especially `process_video_worker.py` and `run_tracking_manager.py`.

---

## Purpose & Pipeline Role

### Objectif
L'Étape 5 effectue le suivi vidéo avec détection de visages, extraction de landmarks faciaux et génération de blendshapes ARKit.

Le pipeline est simplifié autour de 2 modes supportés :
- **Mode MediaPipe (défaut)** : `STEP5_TRACKING_ENGINE` vide (CPU)
- **InsightFace** : `STEP5_TRACKING_ENGINE=insightface` (GPU-only)

### Rôle dans le Pipeline
- **Position** : Cinquième étape du pipeline (STEP5)
- **Prérequis** : Vidéos standardisées (STEP2) et analyses audio (STEP4)
- **Sortie** : JSON dense avec tracked_objects, landmarks, et blendshapes par frame
- **Étape suivante** : Réduction JSON (STEP6)

### Valeur Ajoutée
- **Deux modes supportés** : MediaPipe (CPU) ou InsightFace (GPU-only)
- **GPU optionnel** : Accélération réservée à InsightFace
- **Blendshapes ARKit** : 52 blendshapes standard pour animation 3D
- **Multiprocessing** : Traitement parallèle avec workers configurables
- **Export dense** : Structure JSON optimisée pour les analyses suivantes

---

## Inputs & Outputs

### Inputs
- **Vidéos standardisées** : Fichiers vidéo à 25 FPS de STEP2
- **Analyses audio** : JSON diarization de STEP4 pour détection de parole
- **Configuration** : Moteur de tracking, paramètres GPU/CPU

### Outputs
- **JSON tracking** : Structure frame par frame avec tracked_objects
- **Landmarks faciaux** : 468 points MediaPipe ou équivalents
- **Blendshapes** : 52 coefficients ARKit par visage détecté
- **Logs détaillés** : Journal de tracking dans `logs/step5/`

---

## Command & Environment

### Commande WorkflowCommandsConfig
```python
# Exemple de commande (voir WorkflowCommandsConfig pour la commande exacte)
python workflow_scripts/step5/run_tracking_manager.py --videos_json_path videos.json --cpu_internal_workers 15
```

### Environnement Virtuel
- **Environnement utilisé** : `tracking_env/` (MediaPipe CPU + orchestration STEP5)
- **Isolation** : Environnement dédié tracking (imports MediaPipe en lazy-load dans les workers)

---

## Dependencies

### Bibliothèques Principales
```python
import mediapipe as mp                    # Framework ML pour vision
import cv2                               # OpenCV pour traitement d'image
import numpy as np                       # Calculs numériques
import onnxruntime                       # ONNX pour modèles optimisés
import multiprocessing                    # Multi-processing
```

### Dépendances Externes
- **MediaPipe** : Mode par défaut (CPU)
- **ONNX Runtime** : Requis pour InsightFace (GPU)
- **CUDA** : Accélération GPU pour InsightFace

---

## Configuration

### Variables d'Environnement
- **STEP5_TRACKING_ENGINE** : vide (MediaPipe par défaut) ou `insightface`
- **STEP5_ENABLE_GPU** : Activation GPU (défaut: 0)
- **STEP5_GPU_ENGINES** : Moteurs autorisés en GPU (uniquement `insightface` / `all`)
- **TRACKING_CPU_WORKERS** : Nombre de workers CPU (défaut: 15)
- **STEP5_BLENDSHAPES_THROTTLE_N** : Throttling blendshapes
- **STEP5_EXPORT_VERBOSE_FIELDS** : Contrôle verbosité export
- **STEP5_ENABLE_OBJECT_DETECTION** : Active le fallback object detector (EfficientDet)
- **STEP5_OBJECT_DETECTOR_MODEL** : Modèle EfficientDet (défaut: `efficientdet_lite2`)

### Configuration par Moteur
```json
{
  "mediapipe": {
    "max_faces": 5,
    "min_detection_confidence": 0.5,
    "model_complexity": 1
  },
  "insightface": {
    "gpu_only": true
  }
}
```

---

## Complexité (Radon Analysis)

### Points Critiques (Score F/E/D/C)

#### Workers Multiprocessing (Score F)
- **`process_video_worker.main()`** : Score F - 399 lignes, boucle de traitement frame par frame
- **`process_frame_chunk()`** : Score F - 315 lignes, gestion chunks, synchronisation IPC
- **`init_worker_process()`** : Score F - 96 lignes, initialisation worker, chargement .env
- **`process_video_multiprocessing()`** : Score D - 592 lignes, orchestration complète

#### Moteurs de Tracking (Score E/D)
- **`InsightFaceEngine.detect()`** : Score E - 800 lignes, GPU/CPU, fallback object detector
- **Mode MediaPipe (défaut)** : géré dans les workers (sans factory `create_face_engine`)

#### Gestion Manager (Score F)
- **`run_tracking_manager.main()`** : Score F - 491 lignes, orchestration globale, configuration
- **`launch_worker_process()`** : Score E - 316 lignes, lancement subprocess, injection CUDA
- **`_discover_system_cuda_lib_paths()`** : Score C - 168 lignes, détection chemins CUDA

#### Frame Processing (Score E)
- **`FrameProcessor.process_frame()`** : Score E - 114 lignes, traitement frame individuel
- **Détection multi-moteurs** : Appel moteur, formatage JSON, gestion erreurs
- **Profiling intégré** : Logs toutes les 20 frames, métriques performance

---

## Known Hotspots

### Complexité Backend (Critique)
- **`process_video_worker.py`** : Complexité critique (radon F) dans `main` et `process_frame_chunk`
- **`run_tracking_manager.py`** : Complexité critique (radon F) dans `main`
- **`face_engines.py`** : Complexité élevée (radon E) principalement sur InsightFace
- **Points d'attention** : Gestion multiprocessing, lazy imports MediaPipe, profiling

---

## Multiprocessing Hotspots (Radon F)

### Architecture Workers
- **`process_video_worker_multiprocessing.py`** : Orchestrateur principal (Score F: 315 lignes)
- **`init_worker_process`** : Initialisation worker (Score F: 96 lignes) 
- **`process_frame_chunk`** : Traitement par chunk (Score F: 315 lignes)
- **`process_video_worker.py main`** : Worker principal (Score F: 399 lignes)

### Points chauds (Complexité F)
- **Gestion des chunks** : Découpage vidéo en segments pour traitement parallèle
- **Synchronisation IPC** : Communication inter-processus et partage d'état
- **Gestion erreurs** : Recovery et fallback en cas d'échec worker
- **Optimisations** : Profiling toutes les 20 frames, throttling configurables

### Patterns de Communication
```python
# Structure IPC typique
worker_queue = multiprocessing.Queue()
result_queue = multiprocessing.Queue()

# Chunk processing
def process_frame_chunk(frames_chunk, config):
    # Traitement parallèle avec logging intégré
    # Gestion OOM et recovery automatique
```

### Recommandations Refactoring
- **Documenter les patterns IPC** : Échanges entre manager et workers
- **Simplifier `process_frame_chunk`** : Extraire helpers spécialisés
- **Monitoring continu** : Logs `[PROFILING]` pour tuning performance

---

## Workers Multiprocessing

### Architecture
- **`process_video_worker_multiprocessing.py`** : Orchestrateur principal
- **`init_worker_process`** : Initialisation worker multiprocessing
- **`process_frame_chunk`** : Traitement par chunk
- **`process_video_worker.py main`** : Worker principal

### Complexité Radon
- **Tous les workers** : Score F (complexité critique)
- **Causes** : Gestion IPC, chunking, error recovery, profiling
- **Impact** : Cœur du pipeline de suivi vidéo

### Patterns de Communication
```python
# Structure IPC typique
worker_queue = multiprocessing.Queue()
result_queue = multiprocessing.Queue()

# Chunk processing
def process_frame_chunk(frames_chunk, config):
    # Traitement parallèle avec logging intégré
    # Gestion OOM et recovery automatique
```

### Recommandations
- **Documenter les patterns IPC** : Échanges entre manager et workers
- **Simplifier `process_frame_chunk`** : Extraire helpers spécialisés
- **Monitoring continu** : Logs `[PROFILING]` pour tuning performance

---

## Known Hotspots

### Backend Complexity (Radon Analysis)
- **`process_video_worker.py main`** (Score F) : 399 lignes, orchestration worker
- **`process_frame_chunk`** (Score F) : 315 lignes, traitement chunks parallèles  
- **`init_worker_process`** (Score F) : 96 lignes, initialisation multiprocessing
- **`run_tracking_manager.py main`** (Score F) : 491 lignes, gestion STEP5

### Impact sur la Performance
- **Multiprocessing** : Parallélisme efficace mais complexité élevée
- **GPU Management** : Lazy imports et configuration CUDA
- **Memory Management** : Gestion OOM et nettoyage ressources

---

## Metrics & Monitoring

### Indicateurs de Performance
- **Débit de tracking** : FPS traités par worker
- **Utilisation GPU** : % GPU et mémoire VRAM
- **Précision détection** : Nombre de visages détectés
- **Taux de succès** : % frames traitées avec succès

### Patterns de Logging
```python
# Logs de progression
logger.info(f"Tracking {video_path} - {current}/{total}")

# Logs profiling (toutes les 20 frames)
if frame_count % 20 == 0:
    logger.info(f"[PROFILING] Engine: {engine}, FPS: {fps:.2f}")

# Logs GPU
logger.info(f"ONNX providers: {onnxruntime.get_providers()}")

# Logs d'erreur
logger.error(f"Échec tracking {video_path}: {error}")
```

---

## Failure & Recovery

### Modes d'Échec Communs
1. **GPU OOM** : Basculement automatique sur CPU
2. **Modèle non chargé** : Retry avec téléchargement du modèle
3. **Worker crash** : Redémarrage automatique du worker
4. **Timeout** : Augmentation du délai ou réduction workers

### Procédures de Récupération
```bash
# Réessayer avec CPU uniquement
STEP5_ENABLE_GPU=0 python workflow_scripts/step5/run_tracking_manager.py

# Réduire les workers
TRACKING_CPU_WORKERS=4 python workflow_scripts/step5/run_tracking_manager.py

# Validation post-tracking
python scripts/validate_step5_output.py
```

---

## Related Documentation

- **Pipeline Overview** : `../README.md`
- **GPU Usage Guide** : `../pipeline/STEP5_GPU_USAGE.md`
- **Testing Strategy** : `../technical/TESTING_STRATEGY.md`
- **WorkflowState Integration** : `../core/ARCHITECTURE_COMPLETE_FR.md`

---

*Generated with Code-Doc protocol – see `../cloc_stats.json` and `../complexity_report.txt`.*

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

**Mode GPU (v4.2+)** : Le GPU est **strictement réservé** au moteur InsightFace. Le mode MediaPipe (défaut) s'exécute en CPU même si `STEP5_ENABLE_GPU=1`. Le gestionnaire :
- force `args.disable_gpu=True` pour tout moteur non listé dans `STEP5_GPU_ENGINES`.
- vérifie la disponibilité matérielle via `Config.check_gpu_availability()` avant de lancer InsightFace.
- bascule automatiquement en mode CPU si `STEP5_GPU_FALLBACK_AUTO=1` et qu'une contrainte est détectée (VRAM insuffisante, absence du provider CUDA, etc.).

#### Restrictions GPU (décision 2025-12-27)
⚠️ **IMPORTANT** : Le support GPU est **réservé exclusivement à InsightFace**
- **MediaPipe Face Landmarker** : CPU-only (15 workers)
- Le gestionnaire force `args.disable_gpu=True` pour tous les moteurs non-InsightFace

⚠️ **Contraintes GPU** :
- 1 worker GPU séquentiel uniquement (pas de parallélisation).
- Nécessite un GPU NVIDIA (CUDA ≥ 12.0) avec ≥ 2 Go de VRAM libres (4 Go recommandés pour coexister avec STEP2/NVENC).
- `insightface_env` embarque ONNX Runtime GPU + dépendances InsightFace ; override possible via `STEP5_INSIGHTFACE_ENV_PYTHON`.
- CPU-only reste recommandé pour les batchs massifs (10+ vidéos) et demeure le mode par défaut (`TRACKING_DISABLE_GPU=1`).
- `STEP5_ENABLE_PROFILING=1` active les logs `[PROFILING]` (timings) côté workers.

#### Chunking adaptatif (depuis 2026-01-18)
- Le chunking adaptatif est désormais entièrement géré côté backend avec des **bornes internes par défaut** (≈20 chunks min, ≈400 chunks max) afin de saturer les workers CPU tout en évitant la fragmentation.
- **Plus aucune configuration dynamique** n’est exposée : l’API `/api/step5/chunk_bounds`, les variables `TRACKING_CHUNK_MIN/MAX` et les contrôles UI associés ont été retirés.
- Lorsqu’un worker multiprocessing se lance, il journalise toujours `Adaptive chunking enabled ... selected_chunk_size=XXX` pour vérifier l’application automatique de ces bornes.
- Pour les scénarios spéciaux, la recommandation officielle est d’ajuster le nombre de workers (`TRACKING_CPU_WORKERS`) ou de basculer en mode GPU InsightFace (séquentiel) plutôt que de modifier la taille des chunks.

## Moteurs de Détection Faciale

### Moteurs Disponibles

1. **MediaPipe Face Landmarker** (par défaut)
   - Utilise `face_landmarker_v2_with_blendshapes.task`
   - Support natif des blendshapes ARKit
   - Optimisé pour la détection en temps réel
   - **Mode CPU-only** : optimisé pour 15 workers multiprocessing.

2. **InsightFace (GPU séquentiel)**
   - Moteur ONNX Runtime réservé au mode GPU (`STEP5_TRACKING_ENGINE=insightface`).
   - Requiert l’environnement `insightface_env` et un GPU NVIDIA compatible CUDA ≥ 12 (≥ 2 Go VRAM libres, 4 Go recommandés).
   - Les variables `STEP5_ENABLE_GPU`, `STEP5_GPU_ENGINES=insightface` et `STEP5_INSIGHTFACE_*` (chemins modèles, throttling, overrides Python) se valident via `config/settings.py` @docs/workflow/core/GUIDE_DEMARRAGE_RAPIDE.md#125-189.
   - Respecte la décision du 27 décembre 2025 : **aucun autre moteur n’est autorisé sur GPU** (@memory-bank/decisionLog.md).
   - Profil recommandé : 1 worker GPU séquentiel, chunking automatique + fallback CPU (`STEP5_GPU_FALLBACK_AUTO=1`).

### Optimisations récentes (Décembre 2025)

| Optimisation | Description | Variables clés |
|--------------|-------------|----------------|
| Profiling généralisé | Les workers rechargent `.env` avant chaque chunk pour propager `STEP5_ENABLE_PROFILING`, `STEP5_BLENDSHAPES_THROTTLE_N`. Logs `[PROFILING]` toutes les 20 frames. | `STEP5_ENABLE_PROFILING`, `STEP5_BLENDSHAPES_THROTTLE_N` |
| Filtrage des blendshapes | `STEP5_BLENDSHAPES_PROFILE` (`full`, `mouth`, `mediapipe`, `custom`, `none`) + `STEP5_BLENDSHAPES_EXPORT_KEYS` réduisent la taille JSON (jusqu’à -95 %) tout en conservant la compatibilité STEP6. | `STEP5_BLENDSHAPES_PROFILE`, `STEP5_BLENDSHAPES_EXPORT_KEYS`, `STEP5_BLENDSHAPES_INCLUDE_TONGUE` |
| Registry Object Detector | `workflow_scripts/step5/object_detector_registry.py` centralise EfficientDet/SSD/YOLO/NanoDet et applique l’override `STEP5_OBJECT_DETECTOR_MODEL_PATH` si fourni. | `STEP5_ENABLE_OBJECT_DETECTION`, `STEP5_OBJECT_DETECTOR_MODEL`, `STEP5_OBJECT_DETECTOR_MODEL_PATH` |
| JSON allégé | `STEP5_EXPORT_VERBOSE_FIELDS=0` (défaut) supprime l’export des `landmarks`/`eos` pour les moteurs non MediaPipe afin d’accélérer STEP6 et réduire les transferts. | `STEP5_EXPORT_VERBOSE_FIELDS` |

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
  - ✅ Lorsque `STEP5_TRACKING_ENGINE=insightface`, le gestionnaire bascule sur `insightface_env` (override possible via `STEP5_INSIGHTFACE_ENV_PYTHON`).  
- `_EnvConfig` centralise désormais la lecture typée des variables `STEP5_*` (GPU, engines, workers, overrides). Le manager s’appuie sur cette couche pour :
  - appliquer les restrictions InsightFace GPU-only (`STEP5_ENABLE_GPU=1`, `STEP5_GPU_ENGINES`), 
  - construire un environnement subprocess via `_build_subprocess_env()` qui injecte automatiquement `LD_LIBRARY_PATH` (CUDA libs découvertes dans les venvs + chemins système `/usr/local/cuda*` lorsque nécessaire),
  - propager les limites CPU (`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, etc.) afin d’éviter la contention inter-process,
  - router l’exécution vers `tracking_env` (MediaPipe CPU) ou `insightface_env` (InsightFace GPU) avec vérification d’existence et messages d’erreur explicites.
- Les workers multiprocessing rechargent toujours `.env` pour récupérer ces variables à chaque fork, garantissant que les réglages (`STEP5_BLENDSHAPES_THROTTLE_N`, profil d’export, profiling) restent synchronisés même en mode chunké.
