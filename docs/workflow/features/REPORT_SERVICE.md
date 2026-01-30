# ReportService - Service de Génération de Rapports

> **Code-Doc Context** – Service critique pour la génération de rapports HTML mensuels et de projet avec complexité radon F/E sur les méthodes principales.

---

## Purpose & System Role

### Objectif
`ReportService` orchestre la génération de rapports HTML structurés pour l'analyse mensuelle des projets et les rapports de projet détaillés. Il transforme les données brutes du pipeline (métadonnées vidéos, analyses audio/vidéo) en visualisations exploitables.

### Rôle dans l'Architecture
- **Position** : Service backend central (`services/report_service.py`)
- **Prérequis** : Données STEP1-7, archives ResultsArchiver
- **Sortie** : Rapports HTML avec analyses par durée, métriques détaillées
- **Dépendances** : `FilesystemService`, `ResultsArchiver`, `WorkflowState`

### Valeur Ajoutée
- **Analyse mensuelle** : Répartition par durée (<2 min, 2-5 min, >5 min)
- **Rapports projet** : Vue complète avec métriques agrégées
- **HTML structuré** : Accessible, responsive, sans dépendance externe
- **Templates unifiés** : Cohérence visuelle entre types de rapports

---

## Architecture

### Composants Principaux
```python
class ReportService:
    def __init__(self, 
                 filesystem_service: FilesystemService,
                 results_archiver: ResultsArchiver,
                 workflow_state: WorkflowState):
        self._fs = filesystem_service
        self._archiver = results_archiver
        self._state = workflow_state
```

### Flux de Données
1. **Collecte** : Scan des projets via `ResultsArchiver`
2. **Analyse** : Calculs métriques (durée, résolution, détection)
3. **Génération** : Templates HTML avec données structurées
4. **Export** : Fichiers `.html` dans `archives/reports/`

---

## Complexité (Radon Analysis)

### Points Critiques (Score F/E)

#### `generate_monthly_archive_report()` (Score F)
- **Complexité** : 261 lignes, orchestration complexe
- **Défis** : Parsing HTML existant, agrégation multi-projets, gestion erreurs
- **Impact** : Service critique pour reporting mensuel

#### `analyze_monthly_report_html()` (Score E)
- **Complexité** : 32 lignes, parsing HTML complexe
- **Défis** : Extraction données depuis HTML, validation structure
- **Impact** : Réutilisation des rapports existants

#### `generate_project_report()` (Score D)
- **Complexité** : 612 lignes, génération complète projet
- **Défis** : Agrégation multi-sources, calculs métriques avancés
- **Impact** : Rapports détaillés par projet

---

## Configuration

### Variables d'Environnement
```bash
# Rapports
REPORTS_ENABLED=1
MONTHLY_REPORTS_DIR=archives/reports/monthly
PROJECT_REPORTS_DIR=archives/reports/projects

# Templates
REPORT_TEMPLATE_PATH=templates/reports/project_report.html
MONTHLY_TEMPLATE_PATH=templates/reports/monthly_archive_report.html

# Performance
REPORT_CACHE_TTL=3600
REPORT_MAX_PROJECTS=1000
```

### WorkflowCommandsConfig Intégration
```python
# Accès à la configuration du service
config = WorkflowCommandsConfig()
report_config = config.get_step_config('reports')
```

---

## API & Méthodes

### Méthodes Principales
```python
# Rapport mensuel (Score F)
def generate_monthly_archive_report(self, year: int, month: int) -> str:
    """Génère rapport mensuel HTML avec analyses par durée"""

# Analyse HTML existant (Score E)
def analyze_monthly_report_html(self, html_path: str) -> dict:
    """Extrait métriques depuis rapport HTML existant"""

# Rapport projet (Score D)
def generate_project_report(self, project_name: str) -> str:
    """Génère rapport détaillé pour un projet spécifique"""

# Utilitaires
def _group_videos_by_duration(self, videos: List[dict]) -> dict:
    """Regroupe vidéos par catégorie de durée"""
```

### Patterns d'Utilisation
```python
# Initialisation
report_service = ReportService(filesystem, archiver, workflow_state)

# Rapport mensuel
monthly_html = report_service.generate_monthly_archive_report(2026, 1)

# Rapport projet
project_html = report_service.generate_project_report("project_name")
```

---

## Performance & Monitoring

### Indicateurs Clés
- **Débit génération** : Rapports par seconde
- **Taille projets** : Projets traités par rapport mensuel
- **Temps parsing** : Durée analyse HTML existante
- **Mémoire pics** : Pics mémoire lors de gros rapports

### Patterns de Logging
```python
# Génération rapport
logger.info(f"[Report] Generated monthly report for {year}-{month}")

# Parsing HTML
logger.debug(f"[Report] Parsed HTML: {len(videos)} videos found")

# Erreurs
logger.warning(f"[Report] Failed to load project {project}: {error}")
```

---

## Actions Recommandées

### Refactoring Priorité Haute
1. **Extraire `ReportDataBuilder`** :
   ```python
   class ReportDataBuilder:
       def build_monthly_data(self, projects: List[dict]) -> dict:
           # Isoler logique d'agrégation
   ```

2. **Créer `HTMLTemplateRenderer`** :
   ```python
   class HTMLTemplateRenderer:
       def render_monthly_report(self, data: dict) -> str:
           # Séparer template vs données
   ```

3. **Simplifier `generate_monthly_archive_report`** :
   - Réduire complexité cyclomatique
   - Extraire helpers de parsing HTML
   - Isoler logique métier de génération

### Monitoring Continu
- **Radon** : Surveillance complexité méthodes F/E
- **Tests unitaires** : Couverture parsing HTML et génération
- **Performance** : Benchmark génération gros rapports

---

## Templates & Structure

### Template Mensuel
```html
<div class="monthly-report">
  <h1>Rapport Mensuel {year}-{month}</h1>
  <div class="duration-breakdown">
    <div class="video-names">
      <!-- Videos <2 min -->
    </div>
    <div class="video-names">
      <!-- Videos 2-5 min -->
    </div>
    <div class="video-names">
      <!-- Videos >5 min -->
    </div>
  </div>
</div>
```

### Template Projet
```html
<div class="project-report">
  <h1>Rapport Projet : {project_name}</h1>
  <section class="metadata">
    <!-- Métadonnées vidéo -->
  </section>
  <section class="analysis">
    <!-- Analyses audio/vidéo -->
  </section>
  <section class="metrics">
    <!-- Métriques agrégées -->
  </section>
</div>
```

---

## Documentation Croisée

- [Architecture Complète](../core/ARCHITECTURE_COMPLETE_FR.md) : Vue d'ensemble système
- [Analyse Complexité](../core/COMPLEXITY_ANALYSIS.md) : Métriques radon détaillées
- [ResultsArchiver](../features/RESULTS_ARCHIVER.md) : Persistance des données
- [FilesystemService](../features/FILESYSTEM_SERVICE.md) : Accès fichiers sécurisé
- [Templates](../../templates/reports/) : Structure des templates HTML
