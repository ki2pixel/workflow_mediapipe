# Analyse de Complexité du Codebase

## Métriques Radon (2026-01-30)

### Vue d'Ensemble
- **Complexité moyenne** : D (22.68)
- **88 blocs analysés** (classes, fonctions, méthodes)
- **Répartition** : Python (15,211 LOC), JavaScript (5,641 LOC), CSS (3,594 LOC)
- **Total codebase** : 109,330 lignes

### Évolution depuis 2026-01-26
- **+3 blocs analysés** (85 → 88)
- **Complexité stable** : D (22.7 → 22.68)
- **LOC Python** : +168 lignes (15,043 → 15,211)

---

## Analyse Janvier 2026

### Nouveaux Points Critiques Identifiés

#### Services Backend (Score F/E)
- **`VisualizationService._get_video_metadata`** (Score D) : Extraction FFmpeg avec gestion timeout
- **`VisualizationService._load_tracking_data`** (Score D) : Parsing JSON volumineux optimisé
- **`VisualizationService.get_project_timeline`** (Score C) : Agrégation multi-sources
- **`ReportService.generate_monthly_archive_report`** (Score F) : Génération rapports mensuels HTML
- **`ReportService.analyze_monthly_report_html`** (Score E) : Parsing HTML existant complexe
- **`ReportService.generate_project_report`** (Score D) : Rapports détaillés par projet

#### Face Engines STEP5 (Score E/D)
- **`InsightFaceEngine.detect`** (Score E) : Détection faciale GPU optimisée
- **`OpenSeeFaceEngine.detect`** (Score D) : Pipeline OpenSeeFace complet
- **`EosFaceEngine.detect`** (Score E) : Fit 3DMM avec landmarks
- **`OpenCVYuNetPyFeatEngine.detect`** (Score D) : Hybride YuNet + py-feat

#### STEP5 Workers Multiprocessing (Score F)
- **`process_video_worker.py main`** (Score F) : 399 lignes, orchestration worker principale
- **`process_frame_chunk`** (Score F) : 315 lignes, traitement parallèle par chunks
- **`init_worker_process`** (Score F) : 96 lignes, initialisation multiprocessing
- **`run_tracking_manager.py main`** (Score F) : 491 lignes, gestion STEP5 complète

### Documentation Créée
- ✅ `features/VISUALIZATION_SERVICE.md` : Documentation complète VisualizationService
- ✅ `features/REPORT_SERVICE.md` : Documentation complète ReportService
- ✅ `technical/COMPLEXITY_HOTSPOTS.md` : Synthèse points chauds Radon
- ✅ `post_production/AFTER_EFFECTS_SCRIPTS_ANALYSIS.md` : Analyse scripts JSX

### Traçabilité Améliorée
- **100%** des services F/E maintenant documentés
- **Couverture complète** pipeline STEP1-7 maintenue
- **Synthèse centralisée** dans `COMPLEXITY_HOTSPOTS.md`

---

## Métriques Radon (2026-01-26) - Archive

### Vue d'Ensemble
- **Complexité moyenne** : D (22.7)
- **85 blocs analysés** (classes, fonctions, méthodes)
- **Répartition** : Python (15 043 LOC), JavaScript (5 641 LOC), CSS (3 594 LOC)

### Points Critiques (Score F)

#### CSVService (`services/csv_service.py`)
- **`_check_csv_for_downloads`** (Score F) : Parsing CSV complexe avec gestion multi-formats
- **`_normalize_url`** (Score F) : Normalisation URLs doublement encodées, entités HTML
- **Impact** : Service critique pour le monitoring des téléchargements

#### STEP5 Workers (`workflow_scripts/step5/`)
- **`process_video_worker.py main`** (Score F) : Orchestration worker principale
- **`process_frame_chunk`** (Score F) : Traitement parallèle par chunks
- **`init_worker_process`** (Score F) : Initialisation multiprocessing
- **Impact** : Cœur du pipeline de suivi vidéo

#### ReportService (`services/report_service.py`)
- **`generate_monthly_archive_report`** (Score F) : Génération HTML complexe
- **Impact** : Rapports mensuels pour l'analyse de projet

### Points Chauds (Score E/D)

#### Services Backend
- **`VisualizationService`** (Score E) : 638 lignes, chargement métadonnées
- **`DownloadService.download_dropbox_file`** (Score D) : Téléchargements Dropbox
- **`LemonfoxAudioService`** (Score C) : API Lemonfox et smoothing

#### Workflow Scripts
- **`run_tracking_manager.py main`** (Score F) : Gestion STEP5
- **`run_audio_analysis.py main`** (Score F) : Analyse audio STEP4
- **`convert_videos.py main`** (Score C) : Conversion vidéo STEP2

## Actions Recommandées

### 1. Refactoring CSVService (Priorité Haute)
- **Extraire `URLNormalizer`** : Isoler la logique de normalisation des URLs
- **Créer `DownloadDetector`** : Séparer la détection de téléchargements du parsing
- **Simplifier `_check_csv_for_downloads`** : Réduire la complexité cyclomatique

### 2. Refactoring ReportService (Priorité Haute)
- **Extraire `ReportDataBuilder`** : Isoler agrégation données vs génération HTML
- **Créer `HTMLTemplateRenderer`** : Séparer templates de logique métier
- **Simplifier `generate_monthly_archive_report`** : Réduire complexité cyclomatique

### 3. Simplification STEP5 (Priorité Moyenne)
- **Découper `process_frame_chunk`** : Créer des helpers plus spécialisés
- **Modulariser `init_worker_process`** : Séparer initialisation de logique métier
- **Documenter patterns IPC** : Communication inter-processus et gestion erreurs

## Monitoring Continu

### Outils Recommandés
- **Radon** : Surveillance continue de la complexité
- **SonarQube** : Dette technique et qualité code
- **Pre-commit hooks** : Validation complexité avant commit

### Seuils d'Alerte
- **Score F** : Action immédiate requise
- **Score E** : Planification refactoring dans sprint
- **Score D** : Surveillance accrue

## Documentation Croisée

- **Points Chauds Synthèse** : [COMPLEXITY_HOTSPOTS.md](../technical/COMPLEXITY_HOTSPOTS.md) - Analyse complète Radon 2026-01-30
- **VisualizationService** : [features/VISUALIZATION_SERVICE.md](../features/VISUALIZATION_SERVICE.md) - Documentation complète service D
- **ReportService** : [features/REPORT_SERVICE.md](../features/REPORT_SERVICE.md) - Documentation complète service F/E
- **Pipeline STEP5** : [pipeline/STEP5_SUIVI_VIDEO.md](pipeline/STEP5_SUIVI_VIDEO.md) - Détails workers multiprocessing et face engines
- **Services Backend** : [../services/README.md](../services/README.md) - Architecture services
- **Post-production** : [post_production/AFTER_EFFECTS_SCRIPTS_ANALYSIS.md](post_production/AFTER_EFFECTS_SCRIPTS_ANALYSIS.md) - Scripts After Effects
- **Guides Refactoring** : [../guides/REFACTORING_GUIDELINES.md](../guides/REFACTORING_GUIDELINES.md) - Patterns de simplification
