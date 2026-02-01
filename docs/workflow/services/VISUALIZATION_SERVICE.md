# VisualizationService - Service de Visualisation et Rapports

> **Code-Doc Context** – Service de métriques avec complexité radon E/D sur les méthodes de chargement et traitement. Backend hotspot: génération rapports HTML, timeline interactive, métriques système.

---

## Purpose & System Role

### Objectif
`VisualizationService` génère les visualisations, rapports HTML et métriques pour l'analyse des résultats du pipeline. Il transforme les données brutes de tracking et audio en visualisations exploitables pour la post-production.

### Rôle dans l'Architecture
- **Position** : Service de visualisation (`services/visualization_service.py`)
- **Prérequis** : Données traitées des étapes 4-6, métriques système
- **Sortie** : Rapports HTML, timelines, métriques agrégées
- **Dépendances** : WorkflowState, FilesystemService, PerformanceService

### Valeur Ajoutée
- **Rapports mensuels** : Analyse par durée et projet automatique
- **Timeline interactive** : Visualisation pipeline complet avec navigation
- **Métriques système** : Monitoring CPU, RAM, GPU en temps réel
- **Export HTML** : Rapports autonomes pour partage

---

## Architecture

### Pattern d'Injection
```python
class VisualizationService:
    def __init__(self, 
                 filesystem_service: FilesystemService,
                 performance_service: PerformanceService,
                 workflow_state: WorkflowState):
        self._fs = filesystem_service
        self._perf = performance_service
        self._state = workflow_state
```

### Méthodes Principales

#### Génération de Rapports
```python
def generate_monthly_archive_report(self, year: int, month: int) -> str:
    """Génère un rapport HTML mensuel avec analyse par durée."""
    
def generate_project_report(self, project_path: str) -> str:
    """Génère un rapport détaillé pour un projet spécifique."""
```

#### Timeline et Visualisation
```python
def get_project_timeline(self, project_path: str) -> dict:
    """Construit une timeline interactive pour un projet."""
    
def get_available_projects(self) -> List[dict]:
    """Retourne la liste des projets disponibles avec métadonnées."""
```

#### Chargement de Données
```python
def _load_tracking_data(self, tracking_path: str) -> dict:
    """Charge et optimise le parsing des données de tracking."""
    
def _load_audio_data(self, audio_path: str) -> dict:
    """Charge et structure les données d'analyse audio."""
```

---

## Complexité (Radon Analysis)

### Points Critiques (Score E/D)
- `_get_video_metadata()` : Score D - Probe FFmpeg complexe avec parsing
- `_load_tracking_data()` : Score D - Parsing JSON optimisé avec validation
- `get_project_timeline()` : Score C - Construction timeline avec agrégation
- `_probe_video_file()` : Score C - Analyse FFmpeg avec gestion erreurs

### Architecture de Chargement
```python
def _load_tracking_data(self, tracking_path: str) -> dict:
    # Chargement optimisé avec streaming pour gros fichiers
    # Validation structure + conversion types
    # Indexation pour accès rapide par frame
```

---

## Features & Functionality

### Rapports Mensuels
- **Analyse par durée** : Catégorisation <2min, 2-5min, >5min
- **Métriques projet** : Nombre de vidéos, durée totale, tendances
- **Export HTML** : Fichier autonome avec styles embarqués
- **Navigation** : Interface interactive avec filtrage

### Timeline Interactive
- **Pipeline complet** : Visualisation 7 étapes avec statuts
- **Navigation temporelle** : Accès direct aux frames/clés
- **Métadonnées** : Infos vidéo, audio, tracking synchronisées
- **Export** : Génération PNG/SVG de la timeline

### Métriques Système
- **Performance** : CPU, RAM, GPU temps réel
- **Historique** : Tendances et alertes
- **Monitoring** : Intégration avec PerformanceService
- **Alerting** : Seuils configurables

---

## Data Processing Pipeline

### Flux de Données
1. **Collecte** : Agrégation données depuis STEP4/5/6
2. **Validation** : Vérification structure et cohérence
3. **Transformation** : Calcul métriques, agrégations
4. **Génération** : Création HTML/JSON/SVG
5. **Export** : Sauvegarde avec métadonnées

### Optimisations
- **Streaming** : Traitement chunk pour gros fichiers
- **Cache** : Mise en cache résultats intermédiaires
- **Indexation** : Accès rapide par frame/projet
- **Compression** : Optimisation taille exports

---

## Integration Points

### API Routes
```python
# routes/api_routes.py
@api_blueprint.get("/api/reports/monthly/<int:year>/<int:month>")
def get_monthly_report(year: int, month: int):
    report_html = visualization_service.generate_monthly_archive_report(year, month)
    return Response(report_html, mimetype='text/html')

@api_blueprint.get("/api/projects/<project_id>/timeline")
def get_project_timeline(project_id: str):
    timeline = visualization_service.get_project_timeline(project_id)
    return jsonify(timeline)
```

### Frontend Integration
```javascript
// static/reportViewer.js
async loadMonthlyReport(year, month) {
    const response = await fetch(`/api/reports/monthly/${year}/${month}`);
    const html = await response.text();
    this.displayReport(html);
}

async loadProjectTimeline(projectId) {
    const response = await fetch(`/api/projects/${projectId}/timeline`);
    const timeline = await response.json();
    this.renderTimeline(timeline);
}
```

---

## Configuration

### Variables d'Environnement
- `REPORTS_CACHE_TTL` : Durée cache rapports (défaut: 3600s)
- `TIMELINE_MAX_FRAMES` : Limite frames timeline (défaut: 10000)
- `METRICS_RETENTION_DAYS` : Conservation métriques (défaut: 30)

### Paramètres de Configuration
```python
# Configuration rapports mensuels
MONTHLY_REPORT_TEMPLATE = "templates/reports/monthly_archive_report.html"
PROJECT_REPORT_TEMPLATE = "templates/reports/project_report.html"

# Configuration timeline
TIMELINE_CONFIG = {
    "width": 1200,
    "height": 400,
    "step_height": 50,
    "margin": 20
}
```

---

## Error Handling & Performance

### Gestion des Erreurs
- **Validation** : Vérification formats JSON/vidéo
- **Fallback** : Mode dégradé pour données manquantes
- **Retry** : Tentatives pour FFmpeg/network
- **Logging** : Journalisation structurée des erreurs

### Performance Optimizations
- **Lazy Loading** : Chargement à la demande des données
- **Caching** : Mise en cache rapports et timelines
- **Streaming** : Traitement progressif des gros fichiers
- **Compression** : Gzip pour exports HTTP

---

## Testing Strategy

### Tests Unitaires
- **Isolation** : Mock FFmpeg et données de test
- **Couverture** : Validation parsing, génération, erreurs
- **Fixtures** : Données test standardisées

### Tests d'Intégration
- **API Endpoints** : Validation routes rapports/timeline
- **Frontend** : Intégration reportViewer.js
- **Performance** : Tests charge gros projets

---

## Security Considerations

### Validation
- **Input Validation** : Paths et paramètres structurés
- **Path Traversal** : FilesystemService pour accès sécurisé
- **Content Security** : Échappement HTML/CSS

### Access Control
- **API Authentication** : Token `INTERNAL_WORKER_COMMS_TOKEN`
- **Rate Limiting** : Limitation génération rapports
- **Audit Trail** : Journalisation accès rapports

---

## Evolution & Maintenance

### Architecture v4.1+
- **Service Pattern** : Logique métier isolée dans service
- **Template System** : Séparation contenu/présentation
- **API Integration** : Endpoints REST pour frontend

### Future Enhancements
- **Real-time Updates** : WebSocket pour métriques live
- **Advanced Analytics** : Machine learning sur métriques
- **Export Formats** : PDF, Excel, PowerBI
- **Dashboard** : Interface admin complète
