# Contexte Produit : Workflow MediaPipe v4.0

## Objectif du Produit
Le projet est une application web complète qui automatise le traitement et l'analyse de fichiers vidéo à travers un pipeline modulaire en plusieurs étapes. Le système est conçu pour être robuste, performant et facilement maintenable.

## Architecture Générale
Le système est composé d'un backend **Flask** et d'un frontend **JavaScript** natif. Il suit une **architecture orientée services** où la logique métier est découplée de l'API.

### Note de version (v4.1)
- Optimisation tracking: exécution par défaut en mode CPU-only avec 15 workers internes pour de meilleures performances et stabilité dans l'Étape 5.
- Optimisation audio: extraction ffmpeg vers tmpfs, diarisation GPU-first, écriture JSON streaming pour réduire les goulots d'étranglement I/O dans l'Étape 4.
- Génération de rapports: standardisée en HTML-only (PDF retiré).

### Note de version (v4.2) - Support GPU optionnel (2025-12-22)
- Support GPU **optionnel et expérimental** ajouté pour les moteurs STEP5 MediaPipe Face Landmarker et OpenSeeFace via `STEP5_ENABLE_GPU=1` et `STEP5_GPU_ENGINES`.
- Architecture lazy import pour éviter les conflits TensorFlow dans `tracking_env`.
- Gains observés : FaceMesh ~34× plus rapide, PyFeat ~5-6× (GTX 1650, 1 worker séquentiel).
- Mode CPU-only reste par défaut pour stabilité v4.1.

### Maintenabilité v4.1 (documentée)
- État centralisé avec `WorkflowState` (thread-safe via RLock; API étapes, séquences, téléchargements).
- Configuration centralisée avec `WorkflowCommandsConfig` (7 étapes, patterns regex, gestion token HF).
- Extraction de la logique de téléchargements dans `DownloadService` (callbacks, validation, dataclass `DownloadResult`).
- Réduction de la complexité: `execute_csv_download_worker()` ~230 → ~85 lignes (-63%); `run_process_async()` simplifié (~-40 lignes) avec helpers dans `WorkflowService`.
- Références documentation: `docs/PHASE1_FOUNDATIONS.md`, `docs/PHASE3_PLAN.md`, `docs/REFACTORING_SUMMARY.md`, `docs/COMPLETE_REFACTORING_REPORT.md`, `docs/FINAL_REFACTORING_REPORT.md`.
- Statut: documenté; validation codebase en cours côté `WorkflowService` (voir `docs/MIGRATION_STATUS.md`).

### Pipeline de Traitement
Le cœur du système est un pipeline en 7 étapes, chacune utilisant un environnement virtuel Python optimisé :
1.  **Extraction** (`env/`): Extrait de manière sécurisée les archives (ZIP, RAR, TAR).
2.  **Conversion Vidéo** (`env/`): Standardise toutes les vidéos à 25 FPS en utilisant FFmpeg et l'accélération GPU.
3.  **Détection de Scènes** (`transnet_env/`): Utilise TransNetV2 (PyTorch) pour identifier les changements de scène.
4.  **Analyse Audio** (`audio_env/`): Utilise Pyannote.audio pour la diarisation des locuteurs.
5.  **Suivi Vidéo** (`tracking_env/`, `eos_env/`): Détection et suivi des visages/objets avec choix du moteur (MediaPipe, OpenSeeFace, EOS 3DMM, OpenCV YuNet+py-feat).
6.  **Réduction JSON** (`env/`): Optimise la taille des fichiers de métadonnées JSON générés.
7.  **Finalisation** (`env/`): Consolide, valide et archive tous les résultats.

### Intégrations Clés
-   **Webhook JSON** : Source unique pour le monitoring en temps réel des téléchargements (https://webhook.kidpixel.fr/data/webhook_links.json).
-   **FromSmash** : Support ajouté pour les URLs FromSmash.com avec ouverture manuelle dans un nouvel onglet.
-   **NVIDIA GPU** : Utilisé pour l'accélération matérielle dans les étapes de conversion et d'analyse.

### Interface Utilisateur
Le frontend offre une interface interactive pour :
-   Exécuter chaque étape individuellement ou en séquence.
-   Monitorer en temps réel l'état du système (CPU, RAM, GPU).
-   Visualiser les logs en direct.
-   Configurer et suivre le monitoring des téléchargements avec support multi-sources (Dropbox, FromSmash).
-   **Timeline Connectée** : Visualisation pipeline moderne avec nœuds connectés, spine lumineux et micro-interactions (implémenté Phase 1 HTML/CSS).

### Gestion des Téléchargements
-   **Système de suivi** : Suivi des téléchargements via un fichier `download_history.json` structuré `{url, timestamp}` pour éviter les doublons.
-   **Robustesse** : Gestion des accès concurrents avec verrouillage, écritures atomiques, et sauvegarde automatique.
-   **Résilience** : Cache mémoire et mécanisme de fallback pour éviter les re-téléchargements en cas d'erreur.
-   **Support multi-sources** : Prise en charge de Dropbox, SwissTransfer, et autres services de partage de fichiers.

### Nouvelles Fonctionnalités Ajoutées
-   **Diagnostics Système** : Modale accessible affichant les versions Python/FFmpeg, disponibilité GPU, et flags de configuration filtrés.
-   **Notifications Utilisateur** : Notifications navigateur (avec fallback UI) pour les fins d'étapes ou erreurs, améliorant la réactivité utilisateur.
-   **Archives Persistantes (ResultsArchiver)** : Archivage durable des sorties d'analyse indexées par hash SHA-256 de la vidéo sous `ARCHIVES_DIR`, avec `metadata.json` (provenance, `created_at`).
{{ ... }}
-   **Frontend Report Viewer** : Modale accessible (A11y complète), prévisualisation HTML inline (iframe sandbox), téléchargement HTML, et styles dédiés `css/features/reports.css`.