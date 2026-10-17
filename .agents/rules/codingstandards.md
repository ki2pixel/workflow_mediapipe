---
description: Workflow MediaPipe v4.x mandatory coding standards for all files
alwaysApply: true
---

# Workflow MediaPipe v4.x — Cursor Rules

> Déviation → `decisionLog.md`. Réf: `WorkflowState`, `WorkflowCommandsConfig`, `docs/workflow/*`.

## 1. Tech Stack & Config
- **Backend**: Flask Python 3.10, `services/` isolés.
- **Frontend**: JS natif (`DOMBatcher`+`AppState`), pas de SPA.
- **Config**: `.env` → `config/settings.py` → `WorkflowCommandsConfig`. Jamais de secrets en dur. `ENABLE_CORAL_TPU_ACCELERATION=true` bascule dynamiquement l'inférence vers le TPU.
- **Data**: Streaming JSON O(1) (`ijson`, `StreamingJSONOutput`). SQLite (via `CSVService`) unique BDD active. MySQL est obsolète (`USE_MYSQL=false`, `services.deprecated.mysql_service`).
- **Environnements (`envs/`)**:
  - `transnet_env/`, `audio_env/`, `tracking_env_slim/` (CPU-optimized), `insightface_env/` (GPU-only).
  - OpenCV 5.0 DNN (expérimental) : `tracking_cv5_env/`, `transnet_cv5_env/`.
  - `coral_env/` : Google Coral TPU (TFLite Runtime, PyCoral). Inférence audio hybride (STEP3) : **VAD** sur le TPU (architecture YAMNet Split avec CNN MobileNetV1 compilé 100% Edge TPU ou legacy INT8) et **Embeddings** sur le CPU (ECAPA-TDNN via ONNX Runtime Float32 avec OpenVINO EP, dynamic batching et topologie NUMA).

## 2. Project Structure
- `services/`: Fonctions pures, logique métier (ex: `FilesystemService`).
- `routes/`: Validation I/O, `@measure_api`, appel service.
- `workflow_scripts/`: Exécutables par étape.
- `static/`+`templates/`: Timeline, logs overlay, settings.

## 3. Code Style
### Backend
- Routes minces: Validation, appel service, réponse JSON. Aucune logique métier Flask.
- State: `WorkflowState` (RLock). Pas de globales type `PROCESS_INFO`.
- I/O: Via `FilesystemService.open_path_in_explorer()` avec verrous.
- Logging: `progress_text` brut + JSON streaming structuré.
- **Multiprocessing OpenCV 5.0**: Contexte `spawn` obligatoire (bannir `fork` pour éviter les deadlocks). Limitation à un seul thread par worker via `cv2.setNumThreads(1)` contre l'oversubscription CPU. Exception : STEP 2 (Transitions) sous OpenCV 5.0 DNN est strictement séquentiel (le coût de `spawn` est trop élevé pour le chargement du modèle).

### Frontend
- Immuabilité: `AppState.setState()` diff superficiel.
- DOM: `DOMBatcher.scheduleUpdate()` + `DOMUpdateUtils.escapeHtml()`.
- **DOMDiff**: Envelopper les listes dynamiques (`<li>`) dans `<ul>` avant `DOMDiff.morph`.
- Polling: `PollingManager` uniquement, bannir les `setInterval` isolés.
- Composants clés: Logs Overlay (focus trap, sync timeline), Timeline connectée (badges, auto-scroll).

## 4. Core Patterns
- **Services Singleton**: Accès statique via `get_workflow_state()`.
- **TPU Orchestrator**: L'orchestrateur `services/coral_tpu_orchestrator.py` gère une file séquentielle (Queue) pour protéger la SRAM (8 Mo) du Coral TPU contre l'éviction de cache. Obligatoire pour toute inférence TPU.
- **OpenCV 5.0 DNN Graph Engine**: Initialisation avec `cv2.dnn.DNN_BACKEND_OPENCV` et `cv2.dnn.DNN_TARGET_CPU`, activation explicite via `cv2.dnn.ENGINE_NEW`. Validation pré-vol du graphe via des tenseurs synthétiques (ex: `validate_onnx_slice_operator` pour TransNetV2). Fallback silencieux vers ONNX Runtime ou TFLite en cas d'échec, avec injection dynamique de `LD_LIBRARY_PATH`.
- **Routes**: Validation d'entrée → `@measure_api` → Service → `jsonify({"status": "queued"})`.
- **State Sync**: PollingManager met à jour AppState via WorkflowState.

## 5. Pipeline
- **STEP1 (Extraction + normalisation)**: extraction sécurisée puis normalisation vidéo MP4/H.264/yuv420p/25 fps via `utils/media_normalizer.py` (NVENC parallèle max 3 workers + fallback CPU `libx264`). Contrat obligatoire pour toutes les étapes aval.
- **STEP2 (Transitions)**:
  - GPU/CPU: TransNetV2 (batch=8, `mixed_precision=true`, O(1) RAM).
  - TPU: MobileNetV2 INT8 (GAP 1280D ou logits 1000D fallback) avec architecture Producer-Consumer (FFmpeg I/O asynchrone) + EMA embeddings (α=0.8) + Post-traitements JIT Numba (Filtre Médian 1D + Seuillage adaptatif Dugad μ+k·σ + Twin-Comparison FSM). Timecode `HH:MM:SS.mmm`.
- **STEP3 (Audio)**:
  - GPU/CPU: Lemonfox/Whisper + Fallback Pyannote. Isolement GPU (`AUDIO_GPU_ISOLATION=1`) en sous-processus. `AUDIO_PROFILE=gpu_fp32`.
  - TPU: Architecture YAMNet Split (`STEP3_YAMNET_SPLIT=1`, Frontend CPU Log-Mel NumPy `yamnet_frontend.py` + CNN MobileNetV1 compilé 100% Edge TPU `assets/yamnet_split_edgetpu_compiled.tflite`, 31 ops sur `/dev/apex_0`, latence ~1.1 ms, repli legacy automatique) ; fenêtrage glissant overlap 50% (hop 0.48s), pipeline Producer-Consumer double tampon par blocs de 256 sous `_tpu_lock`, vues directes `interpreter.tensor()` + noyau Numba fusionné Filtre Médian VAD + seuil strict 0.20 + FSM Hangover (1.0s) + AHC condensé (`fastcluster.linkage`, Gram BLAS, seuil 0.32, `np.nextafter`) + réassignation BLAS des locuteurs mineurs (<7.0s) + extraction d-vectors ECAPA-TDNN FP32 via ONNX Runtime (session unique partagée, IOBinding zéro-copie, EP OpenVINO CPU auto avec batch 8) avec fallback embeddings YAMNet 1024D. `STEP3_EMBEDDING_STRIDE=1` par défaut en production (parité stricte et zéro régression sur dialogues courts/rapides), règle adaptative intégrée `_get_embedding_stride(len(speech_indices))` basculant à K=2 si $\ge$ `STEP3_ADAPTIVE_THRESHOLD` (défaut 500 fenêtres, inactif par défaut `STEP3_ADAPTIVE_STRIDE=0`). Le délégué matériel est vérifié via `edgetpu-custom-op` : repli CPU/XNNPACK journalisé en erreur par défaut, bloquant avec `STEP3_REQUIRE_EDGETPU=1`.
- **STEP4 (Tracking)**:
  - CPU: MediaPipe (`tracking_env_slim`), multiprocessing obligatoire + `cv2.setNumThreads(0)`.
  - GPU: InsightFace (`insightface_env`, activé via `STEP4_ENABLE_GPU=1`).
  - TPU: Cascade séquentielle TFLite (BlazeFace + FaceMesh sans `half_pixel_centers` + Face Blendshapes) + Filtre One-Euro (OneEuroFilterND @njit 52 dimensions) CPU par défaut (Kalman de secours). Niveau d'optimisation `STEP4_TPU_FAST=1` (défaut livré : hystérésis du détecteur d'objets `STEP4_TPU_OBJECT_DETECTION_MIN_MISSING=25`, caches ancres BlazeFace et métadonnées interpréteur, écriture JSON tamponnée, temps par frame -34 %). Profilage par étage configurable via `STEP4_TPU_PROFILING_DIR`. Support optionnel des modèles co-compilés dans la SRAM partagée (8 Mo).
  - **Obligatoire**: `StreamingJSONOutput` pour export O(1).
- **STEP4, 5 & 6**: `ijson` obligatoire. Scripts AE priorisent `*_ae.json`.

## 6. After Effects & CEP (ExtendScript ES3)
- **Moteur ES3**: `var`, boucles `for` classiques, polyfill `JSON2`. **Interdit**: ES6 (`const`, `let`, `=>`, `map`, `filter`, templates). Encapsulation IIFE systématique.
- **Sécurité**: `system.callSystem()` avec chemins nettoyés et arguments validés (pas de concaténation brute).
- **Performance**: Batcher les mutations Timeline avec `app.beginUndoGroup`/`endUndoGroup`.
- **Contrats**: JSON strict (`{ "status": "ok", "data": ... }`), erreurs préfixées `[JS] Error:` ou `[PY] Error:`.

## 7. Quality & Process
- **Tests**: `tests/unit/` (fixtures `patched_workflow_state()`), CI avec `DRY_RUN_DOWNLOADS=true`.
- **Sécurité**: `validate_startup.py` bloque en prod si secrets par défaut détectés.
- **Docs**: Suivre méthode `SKILL.md` (TL;DR, trade-offs). Conventional Commits.
- **Skills**: 1. `workflow-operator` > 2. Debug/Skills locales > 3. Règles de ce doc > 4. Docs > 5. Skills globales.

## 8. Anti-Patterns
- Logique métier dans les blueprints Flask.
- Manipulation du DOM sans `DOMUpdateUtils.escapeHtml` ou via `document.getElementById` dès l'import.
- `setInterval` dispersés au lieu de `PollingManager`.
- Chemins hardcodés (ex: `/mnt/cache`). Utiliser `WorkflowCommandsConfig`.
- Activer GPU sur MediaPipe CPU.
- Charger de gros JSON entièrement en RAM avec `json.load()` (utiliser `ijson`).
- JS moderne dans ExtendScript (.jsx).
- Utiliser MySQL en production (déprécié).
- **TPU Anti-Patterns**: Inférences TPU concurrentes sans passer par le `coral_tpu_orchestrator`. Exécution de modèles non compilés pour Edge TPU ou non quantifiés (INT8). Tentative de compiler le frontend Log-Mel audio ou le modèle d'embeddings ECAPA-TDNN pour l'Edge TPU (Log-Mel relève du frontend CPU vectorisé via l'architecture Split ; ECAPA doit tourner sur CPU via ONNX Runtime / OpenVINO pour garantir la précision). Charger un délégué `libedgetpu.so.1` sans vérifier la présence effective d'opérations `edgetpu-custom-op` (repli XNNPACK silencieux). Partager un interpréteur TFLite entre plusieurs workers avec `set_tensor`/`get_tensor` **hors verrou** : la course sur les tenseurs corrompt les scores VAD (écrire, invoquer et lire sous le même verrou, idéalement par bloc). Exécuter des post-traitements lourds en Python pur après inférence TPU (utiliser Numba JIT) ou bloquer le TPU sur de l'I/O vidéo séquentiel (utiliser Producer-Consumer).
- **OpenCV 5.0 Anti-Patterns**: Invoquer le multiprocessing OpenCV 5.0 sans contexte `spawn` ou sans limiter les threads à 1 (`cv2.setNumThreads(1)`). Faire des inférences OpenCV 5.0 sans validation d'opérateurs pré-vol ou sans mécanisme de fallback. Utiliser le multiprocessing pour OpenCV 5.0 DNN dans STEP 2.

> **Note**: Maintenir <12 000 caractères. Réviser après chaque évolution majeure.