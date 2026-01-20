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
  - Source unique pour les 7 étapes (cmd, cwd, logs, patterns regex).
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

### Suivi Vidéo (STEP5) - 2025-12-18
- **Moteurs de Tracking** :
  - `mediapipe` : Moteur par défaut avec support GPU, fournissant 478 landmarks et 52 blendshapes ARKit
  - `opencv_haar` : Alternative légère basée sur les classificateurs en cascade d'OpenCV
  - `opencv_yunet` : Détecteur de visages YuNet optimisé pour la performance
  - `opencv_yunet_pyfeat` : Moteur hybride combinant YuNet, FaceMesh ONNX et py-feat pour les blendshapes

- **Multiprocessing** :
  - Tous les moteurs supportent le traitement parallèle via `process_video_worker_multiprocessing.py`
  - Configuration via `TRACKING_CPU_WORKERS` (nombre de workers) et `TRACKING_DISABLE_GPU` (désactivation GPU)
  - Gestion automatique des ressources et équilibrage de charge entre les workers

- **Format de Sortie** :
  - JSON dense avec une entrée par frame (1..N)
  - Chaque frame contient un tableau `tracked_objects` (vide si aucun objet détecté)
  - Les visages détectés incluent des landmarks et des blendshapes normalisés

### STEP5 — Profiling & Performance (2025-12-19)
- **Chargement `.env` en multiprocessing** : les workers sont des processus isolés; le `.env` doit être chargé côté worker/module (pas uniquement côté manager) pour que `STEP5_ENABLE_PROFILING`, `STEP5_BLENDSHAPES_THROTTLE_N`, etc. soient effectifs.
- **Profiling compatible chunking** : en multiprocessing, chaque worker peut traiter <100 frames; le seuil de log des stats doit être adapté (ex. toutes les 20 frames) pour que les logs `[PROFILING]` apparaissent.
- **YuNet downscaling + rescale coordonnées** : utiliser une largeur max configurable (`STEP5_YUNET_MAX_WIDTH`, défaut 640) pour accélérer YuNet, tout en rescalant `bbox/centroid` en coordonnées de la vidéo originale afin de garder un JSON exploitable.
- **OpenCV threads** : forcer `cv2.setNumThreads(1)` côté YuNet pour éviter la contention avec le multiprocessing.
- **Tuning workers CPU** : réduire `TRACKING_CPU_WORKERS` peut améliorer la stabilité et les perfs (moins de contention CPU).

### STEP5 — GPU Support (2025-12-22)
- **Lazy import MediaPipe** : Utiliser `importlib.import_module("mediapipe")` avec gestion d'exception pour éviter l'import automatique de TensorFlow dans `tracking_env` lors du chargement des workers. Permet de différer l'import jusqu'à l'utilisation réelle du moteur MediaPipe, évitant les conflits NumPy/TensorFlow. Exemple : `_ensure_mediapipe_loaded(required=True)` pour les moteurs MediaPipe, `required=False` pour les fallback object detector.
- **ONNX Runtime providers logging** : Journaliser les providers actifs (ex. `FaceMesh ONNX providers active: ['CUDAExecutionProvider', 'CPUExecutionProvider']`) dans `onnx_facemesh_detector.py` pour faciliter la validation GPU via logs/tests automatisés.
- **Configuration LD_LIBRARY_PATH** : Injection automatique des chemins CUDA `nvidia/cublas/lib` etc. dans `run_tracking_manager.py` pour les sous-processus ONNX Runtime.

### STEP5 — Réduction taille exports JSON (2025-12-20)
- **Variable STEP5_EXPORT_VERBOSE_FIELDS** : false (défaut) désactive l'export des landmarks et eos pour les moteurs non-MediaPipe; true pour debugging complet.
- **Logging upscale** : Logs DEBUG pour confirmer le rescale des coordonnées dans YuNet, OpenSeeFace, EOS lors de downscale.

### Frontend (JavaScript)
-   **État Centralisé (`AppState.js`)** : L'état de l'interface est immutable et géré de manière centralisée.
-   **Optimisation des Mises à Jour DOM (`DOMBatcher.js`)** : Les manipulations du DOM sont groupées pour de meilleures performances.
-   **Modals Conditionnelles** : Pour les types de contenu spécifiques (ex: FromSmash), adapter dynamiquement le titre, contenu et actions de la modale.
-   **Auto-scroll Timeline Connectée (2026-01-20)** : Utiliser un scroll déterministe basé sur `calculateOptimalScrollPosition()` + `window.scrollTo()` pour respecter la topbar. Éviter `scrollIntoView()` qui ignore les éléments fixes. Ajouter un espace scrollable en bas de timeline (`timeline-scroll-spacer`) pour permettre le centrage de la dernière étape. Supprimer les `scroll-margin-top` qui interfèrent avec le calcul. Recentrer de manière throttlée pendant les séquences pour compenser les changements de hauteur dynamiques.

## Général
-   **Logging** : Utiliser le logger centralisé et les logs spécifiques à chaque étape.
-   **Gestion des Erreurs** : Implémenter une gestion d'erreurs robuste (ex: `ErrorHandler.js` côté frontend).
-   **Tests** : Suivre la structure de tests `pytest` définie.
-   **Sécurité URL** : Valider et nettoyer les URLs externes avec allowlists pour éviter les vulnérabilités.
-   **Écriture JSON en streaming** : Pour éviter le stockage complet en mémoire lors de la génération de fichiers volumineux (2025-10-06 15:29:19+02:00).
-   **Politique device configurable via env** : CUDA prioritaire avec CPU fallback et threads ajustables pour optimisations PyTorch (2025-10-06 15:29:19+02:00).