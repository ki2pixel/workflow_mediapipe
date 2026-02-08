# Patrons et Conventions du Système

Ce document définit les règles et les patrons de conception à suivre pour le développement.
**Pour des règles de codage et d'architecture détaillées et obligatoires, consultez le document `coding_standards.md` qui fait autorité.**

### Audio (STEP4) – 2025-11-18
- **Environnement GPU rétrocompatible** : Python 3.10 + torch 1.12.1+cu113 sur drivers CUDA 11.x.
- **Auth HF** : HUGGINGFACE_HUB_TOKEN + HfFolder.save_token() pour compatibilité libs; vérification `whoami`.
- **Pipelines pyannote v2** : éviter `.to()` si absent; gérer modèle v3.1 → fallback v2.
- **OOM** : PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32 (torch 1.12), empty_cache() entre fichiers, fallback CPU per-file.
- **Découverte** : Exclure `.mov` de STEP4 pour éviter les erreurs d'extraction audio.
- **Politique** : Succès partiel possible via AUDIO_PARTIAL_SUCCESS_OK=1.
- **Cohérence GPU/CPU (2025-12-15)** : privilégier `AUDIO_PROFILE=gpu_fp32` (GPU FP32, AMP désactivé, batch_size=1). AMP (FP16) peut provoquer des faux négatifs massifs sur `is_speech_present`.
- **Lemonfox (2025-12-17)** : lorsque STEP4 exécute le wrapper Lemonfox dans `audio_env`, importer `services/lemonfox_audio_service.py` via `importlib` (import par chemin) plutôt que via `services` package, afin d’éviter l’exécution de `services/__init__.py` et ses dépendances Flask (`flask_caching`).

### Patrons Refactoring — 2025-11-18
- **État Centralisé (WorkflowState)** :
  - Singleton thread-safe (RLock) exposant APIs pour étapes, séquences, téléchargements.
  - Accès atomiques: `update_step_info`, `update_step_status`, `update_step_progress`, `append_step_log`.
- **Configuration (WorkflowCommandsConfig)** :
  - Source unique pour les 8 étapes (cmd, cwd, logs, patterns regex).
  - Gestion token HF via `update_hf_token()`; méthodes `get_step_config`, `get_step_command`.
- **Extraction Téléchargements (DownloadService)** :
  - `download_dropbox_file()` avec callbacks de progression et dataclass `DownloadResult`.
  - Helpers: extraction nom, résolution de conflits, validation ZIP.
- **Helpers WorkflowService** :
  - `prepare_step_execution`, `prepare_tracking_step`, `create_tracking_temp_file`, `calculate_step_duration`.
- **Tests & Documentation** :
  - Exigences: tests unitaires et d'intégration couvrant nouveaux services et workflows.
  - Références: `docs/PHASE1_FOUNDATIONS.md`, `docs/PHASE3_PLAN.md`, `docs/REFACTORING_SUMMARY.md`, `docs/COMPLETE_REFACTORING_REPORT.md`, `docs/FINAL_REFACTORING_REPORT.md`.
  - Statut: documenté; finalisation `WorkflowService` en cours (voir `docs/MIGRATION_STATUS.md`).

### Résumé des Patrons Clés

### Backend (Flask)
-   **Architecture Orientée Services** : Toute la logique métier réside dans le dossier `/services`. Les routes sont des contrôleurs légers.
-   **Gestion de la Configuration** : La configuration est centralisée dans `config/settings.py` et chargée depuis `.env`. Aucun secret dans le code.
-   **Environnements Virtuels Spécialisés** : Chaque étape du workflow utilise un environnement Python dédié pour éviter les conflits de dépendances.
-   **Extraction audio via ffmpeg subprocess** : Remplace MoviePy pour rapidité et réduction des dépendances (2025-10-06 15:29:19+02:00).
-   **Mode CPU-only par défaut pour le tracking** : Utilise multiprocessing avec workers configurables via env pour de meilleures performances (2025-10-06 01:30:00+02:00).
-   **Garde-fous pour la progression fractionnaire** : Clamping et réinitialisation pour éviter les sauts prématurés à 100% (2025-10-06 14:42:00+02:00).
-   **Rapports Mensuels** : Génération de rapports HTML avec catégorisation des vidéos par durée (<2 min, 2-5 min, >5 min) pour analyse des tendances (2025-10-11).

#### Rapports (Comptage & Analyse) — 2025-11-02 00:38:00+01:00
- **Source de vérité affichage** : Les compteurs par durée dans le HTML doivent être dérivés des longueurs réelles des listes `duration_names` (pas de calcul séparé).
- **Déduplication/Merge** : Avant rendu, fusionner les noms scindés (ligne préfixe sans extension + ligne suivante se terminant par `.mp4`).
- **Structure HTML** : Lister 1 vidéo = 1 entrée via `div.video-names > div.video-name` (éviter `<br>` qui coupe les noms).
- **Analyseur Upload** : Parser uniquement la section « Répartition des Durées par Projet » avec stratégies A/B/C: (A) conteneur `div.video-names`, (B) `span.video-names` + `<br>` (avec merge), (C) `div.video-name` isolés.
- **Mesures retournées** : Exposer `lines_mp4`, `list_items_total`, et `total_from_counters` (ce dernier n'est qu'un contrôle croisé, non la vérité métier).

### Gestion des Téléchargements
- **Accès Concurrents** : Utilisation de `threading.Lock()` pour sérialiser l'accès au fichier d'historique.
- **Écritures Atomiques** : Écriture dans un fichier temporaire suivi d'un `os.replace()` pour garantir l'intégrité des données.
- **Cache Mémoire** : Maintien d'un cache en mémoire pour éviter les lectures disque inutiles et fournir un fallback en cas d'erreur.
- **Migration Progressive** : Support rétrocompatible des anciens formats de données avec migration automatique vers le nouveau format structuré.

### Suivi Vidéo (STEP5) — 2026-02-03
- **Moteurs supportés** :
  - `mediapipe` (valeur vide) : moteur par défaut CPU-only exécuté dans `tracking_env_slim`. Fournit 478 landmarks + 52 blendshapes ARKit via MediaPipe Tasks. Import lazy pour éviter TensorFlow.
  - `insightface` : unique moteur GPU autorisé (ONNX Runtime) exécuté dans `insightface_env`. Nécessite `STEP5_ENABLE_GPU=1`, `STEP5_TRACKING_ENGINE=insightface` et présence dans `STEP5_GPU_ENGINES`. Toute autre valeur est rejetée par `run_tracking_manager.py`.
  - Tous les moteurs historiques (OpenCV, OpenSeeFace, EOS, pyfeat) et options UI avancées ont été supprimés.

- **Multiprocessing / workers** :
  - MediaPipe utilise `process_video_worker_multiprocessing.py` (workers CPU). `TRACKING_CPU_WORKERS` est injecté via `_EnvConfig`; chaque worker initialise `FaceLandmarker` + `ObjectDetector` via `ObjectDetectorRegistry`.
  - InsightFace est GPU-only; aucun worker CPU n’est lancé lorsque ce moteur est sélectionné. Si la validation GPU échoue (`Config.check_gpu_availability()`), le manager tombe en erreur (ou fallback CPU si `STEP5_GPU_FALLBACK_AUTO=1`).
  - Les snapshots d’environnement (`_log_env_snapshot()`) et la gestion `resource_worker_loop` s’assurent que GPU/CPU ne tournent que lorsque le moteur choisi le permet.

- **Format de sortie** :
  - STEP5 produit toujours un JSON dense frame-by-frame (`tracked_objects[]`, blendshapes/throttles configurables). `STEP5_EXPORT_VERBOSE_FIELDS` reste un flag de debugging.
  - STEP6 `json_reducer.py` produit la source de vérité `*_tracking.json` (analytics, `temporal_alignment`). Les scripts AE consomment STEP6 en priorité.

### STEP5 — Profiling & Performance (v4.3)
- `_EnvConfig` centralise la lecture des variables (workers, GPU flags, throttle). Les workers héritent d’un `args_dict` complet pour garantir que les throttles (`blendshapes_throttle_n`, `mediapipe_max_width`, `mediapipe_jawopen_scale`) sont appliqués.
- `ObjectDetectorRegistry` est la source unique pour les modèles EfficientDet (résolution, overrides). Toute erreur de résolution stoppe le worker.
- Le manager journalise la validation GPU (pynvml + `nvidia-smi`). InsightFace est strictement GPU-only : si `STEP5_ENABLE_GPU=0` ou `insightface` n’est pas listé dans `STEP5_GPU_ENGINES`, l’exécution est refusée.
- `tracking_env_slim` embarque uniquement Mediapipe + dépendances minimales : toute tentative d’activer YuNet/OpenCV doit être considérée comme non supportée.

### STEP5 — GPU Support (2025-12-22)
- **Lazy import MediaPipe** : Utiliser `importlib.import_module("mediapipe")` avec gestion d'exception pour éviter l'import automatique de TensorFlow dans `tracking_env` lors du chargement des workers. Permet de différer l'import jusqu'à l'utilisation réelle du moteur MediaPipe, évitant les conflits NumPy/TensorFlow. Exemple : `_ensure_mediapipe_loaded(required=True)` pour les moteurs MediaPipe, `required=False` pour les fallback object detector.
- **ONNX Runtime providers logging** : Journaliser les providers actifs (ex. `FaceMesh ONNX providers active: ['CUDAExecutionProvider', 'CPUExecutionProvider']`) dans `onnx_facemesh_detector.py` pour faciliter la validation GPU via logs/tests automatisés.
- **Configuration LD_LIBRARY_PATH** : Injection automatique des chemins CUDA `nvidia/cublas/lib` etc. dans `run_tracking_manager.py` pour les sous-processus ONNX Runtime.

### STEP5 — Réduction taille exports JSON (2025-12-20)
- **Variable STEP5_EXPORT_VERBOSE_FIELDS** : false (défaut) désactive l'export des landmarks et eos pour les moteurs non-MediaPipe; true pour debugging complet.
- **Logging upscale** : Logs DEBUG pour confirmer le rescale des coordonnées dans YuNet, OpenSeeFace, EOS lors de downscale.

### Frontend (JavaScript)
-   **AppState** : Immutable (diff via `structuredClone`). Préférences (auto-ouverture logs, toggles settings) persistées dans localStorage.
-   **DOMBatcher** : Toutes les mutations DOM doivent passer par `DOMBatcher.scheduleUpdate()`. `DOMUpdateUtils.escapeHtml()` obligatoire pour les contenus dynamiques (logs, popups).
-   **Timeline Connectée** : Spine unique, auto-scroll déterministe (calcul `calculateOptimalScrollPosition` + `window.scrollTo`). Panneau Step Details supprimé (2026-02-04) : ne plus dépendre de `stepDetailsPanel.js`.
-   **Overlay de logs Phase 4** : Header contextuel (étape/statut/timer), focus trap, bouton close robuste. Respecter la préférence `getAutoOpenLogOverlay()` (pas d’ouverture forcée pendant les séquences si désactivé).
-   **Modales actives** : Supervision/Smart Upload supprimées. Les modales restantes (diagnostics, téléchargements) doivent conserver focus trap et A11y (focus-visible global, support `prefers-reduced-motion`).

### Post-production / After Effects (2026-02-03)
- STEP7 `preprocess_ae_json.py` prépare `*_ae.json` (filtrage par frames, structures compactes). Les scripts ExtendScript (`Analyse-Écart-X...jsx`, `Media-Solution-v11.2-production.jsx`) déclenchent ce script via `system.callSystem()` (manifestes `--manifest_path/--output_path`).
- `media_solution_bridge.py` fournit un mode `cuts` pour externaliser le parsing CSV et générer des segments (`ms_cuts_manifest_*`). Feature flag `enablePythonCutsParser` + fallback ExtendScript automatique.
- Le pipeline AE consomme en priorité `*_tracking.json` (STEP6). STEP5 brut n’est utilisé qu’en fallback streaming. Les logs `[PY]` doivent être visibles côté script AE pour diagnostiquer les ponts Python.

## Général
-   **Logging** : Utiliser le logger centralisé et les logs spécifiques à chaque étape.
-   **Gestion des Erreurs** : Implémenter une gestion d'erreurs robuste (ex: `ErrorHandler.js` côté frontend).
-   **Tests** : Suivre la structure de tests `pytest` définie.
-   **Sécurité URL** : Valider et nettoyer les URLs externes avec allowlists pour éviter les vulnérabilités.
-   **Écriture JSON en streaming** : Pour éviter le stockage complet en mémoire lors de la génération de fichiers volumineux (2025-10-06 15:29:19+02:00).
-   **Politique device configurable via env** : CUDA prioritaire avec CPU fallback et threads ajustables pour optimisations PyTorch (2025-10-06 15:29:19+02:00).