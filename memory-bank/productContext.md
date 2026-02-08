# Contexte Produit : Workflow MediaPipe v4.3

## Objectif du Produit
Le projet est une application web complète qui automatise le traitement et l'analyse de fichiers vidéo à travers un pipeline modulaire en plusieurs étapes. Le système est conçu pour être robuste, performant et facilement maintenable.

## Architecture Générale
Le système est composé d'un backend **Flask** et d'un frontend **JavaScript** natif. Il suit une **architecture orientée services** où la logique métier est découplée de l'API.

### Note de version (v4.3) — Février 2026
- Pipeline 8 étapes : introduction du STEP7 « Pré-traitement After Effects » (Python) et renumérotation de la finalisation en STEP8. Le script AE consomme désormais les fichiers `*_ae.json` produits par STEP7 avec fallback contrôlé.
- STEP5 simplifié : MediaPipe Landmarker sur CPU (via `tracking_env_slim`) devient le moteur par défaut; InsightFace est l’unique moteur GPU supporté via `insightface_env`. Tous les anciens moteurs (OpenCV, OpenSeeFace, EOS) et options avancées ont été retirés.
- Ponts After Effects : `preprocess_ae_json.py` est réutilisable depuis les scripts ExtendScript (Media-Solution) pour le recentrage et la génération des coupes CSV via `media_solution_bridge.py` (exécution `system.callSystem()`).
- UI pipeline : Timeline connectée, overlay de logs Phase 4 et paramètres consolidés. Le panneau Step Details a été supprimé (2026-02-04) pour alléger l’interface, mais l’overlay de logs reste synchronisé avec AppState et les séquences.

### Maintenabilité v4.1 (documentée)
- État centralisé avec `WorkflowState` (thread-safe via RLock; API étapes, séquences, téléchargements).
- Configuration centralisée avec `WorkflowCommandsConfig` (8 étapes, patterns regex, gestion token HF).
- Extraction de la logique de téléchargements dans `DownloadService` (callbacks, validation, dataclass `DownloadResult`).
- Réduction de la complexité: `execute_csv_download_worker()` ~230 → ~85 lignes (-63%); `run_process_async()` simplifié (~-40 lignes) avec helpers dans `WorkflowService`.
- Références documentation: `docs/PHASE1_FOUNDATIONS.md`, `docs/PHASE3_PLAN.md`, `docs/REFACTORING_SUMMARY.md`, `docs/COMPLETE_REFACTORING_REPORT.md`, `docs/FINAL_REFACTORING_REPORT.md`.
- Statut: documenté; validation codebase en cours côté `WorkflowService` (voir `docs/MIGRATION_STATUS.md`).

### Pipeline de Traitement
Le cœur du système est un pipeline en 8 étapes, chacune isolée dans son environnement Python :
1.  **Extraction** (`env/`) : Extraction sécurisée des apports (ZIP/RAR/TAR) via `FilesystemService`, avec cache relocalisable (`CACHE_ROOT_DIR`).
2.  **Conversion Vidéo** (`env/`) : Normalisation FFmpeg (25 FPS, profil GPU si disponible) et instrumentation de progression.
3.  **Détection de Scènes** (`transnet_env/`) : TransNetV2 PyTorch pour les coupures, avec skips conditionnels documentés lorsque les modèles manquent.
4.  **Analyse Audio** (`audio_env/`) : Pipeline Lemonfox + Pyannote (fallback) avec embeddings locuteurs optionnels (`AUDIO_INCLUDE_SPEAKER_EMBEDDINGS`).
5.  **Suivi Vidéo** (`tracking_env_slim/`, `insightface_env/`) : MediaPipe Landmarker CPU-only en multiprocessing (valeur par défaut). InsightFace GPU est disponible uniquement si `STEP5_ENABLE_GPU=1` et `STEP5_TRACKING_ENGINE=insightface`, sinon fallback CPU automatique.
6.  **Réduction JSON** (`env/`) : `json_reducer.py` produit `*_tracking.json` (source primaire AE) avec analytics et `temporal_alignment`.
7.  **Pré-traitement AE** (`env/`) : `preprocess_ae_json.py` génère `*_ae.json` optimisés, utilisables directement par le script AE et par `Media-Solution` via manifest.
8.  **Finalisation** (`env/`) : `finalize_and_copy.py` archive les sorties (ResultsArchiver) et publie les artefacts.

### Intégrations Clés
-   **Webhook JSON** : Source unique pour le monitoring temps réel (`CSVMonitorService` + `download_history.sqlite3`).
-   **FromSmash / Dropbox / SwissTransfer** : Parcours validé avec ouverture manuelle sécurisée lorsqu’un téléchargement automatique est impossible.
-   **NVIDIA GPU** : Exploité pour FFmpeg (STEP2), InsightFace (STEP5) et profils audio `gpu_fp32`. La validation GPU passe par `Config.check_gpu_availability()` (pynvml + `nvidia-smi`).

### Interface Utilisateur
Le frontend (vanilla JS + DOMBatcher/AppState) offre :
-   Lancement des étapes individuelles, séquences personnalisées et monitoring temps réel (Timeline connectée avec spine, statuts et auto-scroll structurel).
-   Overlay de logs Phase 4 : header contextuel, focus trap, préférence d’auto-ouverture persistée dans `AppState`/localStorage.
-   Paramètres consolidés : toggles structurés (Settings Sprint 2), badges d’état dynamiques, modales sécurisées.
-   Suppression des panneaux obsolètes (Step Details, Supervision, Smart Upload) pour réduire la dette UI tout en conservant l’accessibilité (focus-visible global, support `prefers-reduced-motion`).

### Gestion des Téléchargements
-   **Système de suivi** : Historique persistant stocké en SQLite (table `download_history`) via `download_history_repository`, garantissant l’intégrité en mode multi-workers.
-   **Robustesse** : Verrouillage natif SQLite + normalisation systématique des URLs pour éviter les doublons et garantir des écritures atomiques.
-   **Résilience** : Cache mémoire et mécanisme de fallback (DRY_RUN) pour éviter les re-téléchargements en cas d’erreur.
-   **Support multi-sources** : Prise en charge de Dropbox (direct + proxy), SwissTransfer et autres services validés par Webhook.

### Nouvelles Fonctionnalités Ajoutées
-   **Diagnostics Système** : Modale accessible affichant les versions Python/FFmpeg, disponibilité GPU, et flags de configuration filtrés.
-   **Notifications Utilisateur** : Notifications navigateur (avec fallback UI) pour les fins d'étapes ou erreurs, améliorant la réactivité utilisateur.
-   **Archives Persistantes (ResultsArchiver)** : Archivage durable des sorties d'analyse indexées par hash SHA-256 de la vidéo sous `ARCHIVES_DIR`, avec `metadata.json` (provenance, `created_at`).
-   **Frontend Report Viewer** : Modale accessible (A11y complète), prévisualisation HTML inline (iframe sandbox), téléchargement HTML, et styles dédiés `css/features/reports.css`.