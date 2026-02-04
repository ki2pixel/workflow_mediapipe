# API Routes - Contrats et Sécurité

> **Code-Doc Context** – Routes Flask (`routes/api_routes.py`) avec instrumentation `measure_api`, délégation services et sécurisation par tokens internes.

---

## Purpose & System Role

### Objectif
`routes/api_routes.py` expose les endpoints REST de l'application Flask en suivant le pattern **routes minces** : validation entrée, instrumentation, délégation aux services, réponse JSON.

### Rôle dans l'Architecture
- **Position** : Blueprint Flask `api_bp` (`routes/api_routes.py`)
- **Prérequis** : Services injectés (`WorkflowService`, `CacheService`, `PerformanceService`, etc.)
- **Sortie** : Réponses JSON sérialisées avec métriques de performance
- **Dépendances** : `WorkflowCommandsConfig`, `config.settings`, décorateurs sécurité

### Valeur Ajoutée
- **Contrats clairs** : Entrées/Sorties JSON documentées
- **Sécurité** : Tokens internes, validation step keys
- **Instrumentation** : `@measure_api` sur tous les endpoints
- **Séparation** : Zéro logique métier dans les routes

---

## Architecture Routes

### Pattern Contrôleur Mince
```python
@api_bp.route('/api/step/<step_key>/run', methods=['POST'])
@measure_api('/api/step/<step_key>/run')
def run_step(step_key: str):
    """Déclenche l'exécution d'une étape du pipeline."""
    payload = request.get_json()
    validate_step(step_key)  # Validation entrée
    workflow_service.run_step(step_key, payload)  # Délégation service
    return jsonify({"status": "queued"})
```

### Sécurité par Tokens
```python
from config.security import require_internal_worker_token

@api_bp.route('/api/cache/open', methods=['POST'])
@require_internal_worker_token
@measure_api('/api/cache/open')
def open_cache_folder():
    """Ouverture explorateur (sécurisé)."""
    return filesystem_service.open_path_in_explorer(...)
```

---

## Endpoint Matrix

| Endpoint | Méthode | Payload | Service délégué | Sécurité | Description |
|----------|---------|---------|-----------------|----------|-------------|
| `/api/step/<step_key>/run` | POST | `{"project_name", "video_name"}` | `WorkflowService.run_step` | `validate_step_key` | Lance étape pipeline |
| `/api/step_status/<step_key>` | GET | - | `WorkflowService.get_step_status` | - | Statut étape en temps réel |
| `/api/get_specific_log/<step_key>/<log_index>` | GET | query `offset` | `WorkflowService.get_step_log_file` | - | Fichier log streamé |
| `/api/cache/stats` | GET | - | `CacheService.get_cache_stats` | - | Statistiques cache |
| `/api/cache/list_today` | GET | - | `CacheService.list_today_cache_folders` | - | Dossiers cache du jour |
| `/api/cache/open` | POST | `{"folder_number"}` | `FilesystemService.open_path_in_explorer` | `@require_internal_worker_token` | Ouvre explorateur |
| `/api/cache/search` | GET | query `pattern` | `CacheService.search_cache` | - | Recherche dans cache |
| `/api/system_monitor` | GET | - | `MonitoringService.get_system_metrics` | - | Métriques système |
| `/api/system/diagnostics` | GET | - | `MonitoringService.get_diagnostics` | - | Diagnostics système |
| `/api/performance/metrics` | GET | - | `PerformanceService.get_performance_metrics` | - | Métriques de performance |
| `/api/performance/reset` | POST | - | `PerformanceService.reset_metrics` | - | Reset métriques |
| `/api/step4/lemonfox_audio` | POST | `{"project_name", "video_name"}` | `LemonfoxAudioService.process_video_with_lemonfox` | - | Analyse audio Lemonfox |

---

## Contrats Détaillés

### POST `/api/step/<step_key>/run`
**Entrée** :
```json
{
  "project_name": "projet_camille_001",
  "video_name": "video1.mp4",
  "sequence_id": "custom_seq_123"  // optionnel
}
```

**Sortie** :
```json
{
  "status": "queued",
  "step_key": "step5",
  "sequence_id": "custom_seq_123",
  "timestamp": "2026-02-04T13:45:00Z"
}
```

**Erreurs** :
- `400 Bad Request` : step_key invalide ou payload malformé
- `409 Conflict` : étape déjà en cours
- `500 Internal Server Error` : échec service

---

### GET `/api/get_specific_log/<step_key>/<log_index>`
**Entrée** :
- `step_key` : clé d'étape (ex: `step5`)
- `log_index` : index du fichier log (0 = plus récent)
- `offset` (query) : offset lignes pour pagination

**Sortie** :
```text
[2026-02-04 13:45:12] [INFO] Starting video processing...
[2026-02-04 13:45:13] [PROFILING] Frame 1000, FPS: 28.5
...
```

**Erreurs** :
- `400 Bad Request` : step_key non reconnu
- `404 Not Found` : fichier log absent
- `416 Range Not Satisfiable` : offset invalide

---

### POST `/api/cache/open`
**Entrée** :
```json
{
  "folder_number": 5
}
```

**Sortie** :
```json
{
  "status": "opened",
  "path": "/mnt/cache/projets_extraits_20260204_05"
}
```

**Sécurité** : Nécessite `INTERNAL_WORKER_TOKEN` dans header `X-Worker-Token`

---

## Instrumentation

### Décorateur `@measure_api`
```python
@measure_api(endpoint_name, sample_rate=1.0)
def endpoint_handler():
    """Automatiquement instrumenté."""
```

**Comportement** :
- Mesure durée exécution (ms) via `time.perf_counter_ns()`
- Capture statut HTTP et erreurs
- Enregistre métriques dans `PerformanceService`
- Génère logs structurés avec request_id

**Exemple Log** :
```json
{
  "timestamp": "2026-02-04T13:45:12.123Z",
  "level": "INFO",
  "component": "api",
  "request_id": "req_abc123",
  "endpoint": "/api/step5/run",
  "status_code": 200,
  "duration_ms": 1245.67,
  "tags": ["step5", "workflow", "v4.2"]
}
```

### Métriques Personnalisées
```python
@api_bp.route('/api/step4/lemonfox_audio', methods=['POST'])
@measure_api('/api/step4/lemonfox_audio', sample_rate=0.1)  # 10% sampling
async def analyze_audio():
    result = await LemonfoxAudioService.analyze(...)
    
    # Métriques enrichies
    PerformanceService.record_metric(
        component="audio",
        metric="processing_time_ms",
        value=result['processing_time'],
        tags={"model": result['model'], "duration_sec": result['duration']}
    )
    
    return jsonify({
        "status": "success",
        "data": result,
        "_metrics": {
            "processing_time_ms": result['processing_time'],
            "speech_segments": len(result['segments'])
        }
    })
```

---

## Sécurité

### Tokens Internes
```python
# config/settings.py
INTERNAL_WORKER_TOKEN = os.getenv('INTERNAL_WORKER_TOKEN', 'default-dev-token')

# config/security.py
def require_internal_worker_token(f):
    """Décorateur pour endpoints internes."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('X-Worker-Token')
        if token != current_app.config['INTERNAL_WORKER_TOKEN']:
            abort(401, description="Invalid worker token")
        return f(*args, **kwargs)
    return decorated
```

### Validation Step Keys
```python
def validate_step(step_key: str) -> None:
    """Valide que la clé d'étape existe dans WorkflowCommandsConfig."""
    config = WorkflowCommandsConfig()
    if step_key not in config.get_step_configs():
        abort(400, description=f"Invalid step key: {step_key}")
```

### CORS et Headers
```python
@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    return response
```

---

## Patterns d'Utilisation

### Validation Entrée
```python
def validate_run_step_payload(payload: dict) -> None:
    """Validation schéma payload."""
    required = ['project_name', 'video_name']
    missing = [k for k in required if k not in payload]
    if missing:
        abort(400, description=f"Missing required fields: {missing}")
```

### Gestion Erreurs
```python
@api_bp.errorhandler(404)
def handle_not_found(e):
    return jsonify({"error": "Resource not found"}), 404

@api_bp.errorhandler(500)
def handle_internal_error(e):
    logger.error(f"Internal error: {e}")
    return jsonify({"error": "Internal server error"}), 500
```

### Réponses Structurées
```python
def api_response(data: Any, status: str = "success", code: int = 200):
    """Format de réponse standardisé."""
    return jsonify({
        "status": status,
        "data": data,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }), code
```

---

## Performance & Monitoring

### Métriques Collectées
- **Temps de réponse** : par endpoint, percentiles
- **Taux d'erreur** : par type d'erreur
- **Débit** : requêtes/seconde par endpoint
- **Métriques métier** : temps traitement étapes, taille cache

### Monitoring Dashboard
- Endpoint `/api/performance/metrics` expose les métriques en JSON
- Widget System Monitor dans frontend consomme ces métriques
- Logs structurés permettent agrégation via ELK/Prometheus

### Optimisations
- **Sampling** : Endpoints lourds (ex: audio) échantillonnés à 10%
- **Cache** : Réponses statiques (diagnostics) mises en cache
- **Async** : Endpoints I/O-bound utilisent `async/await`

---

## Tests & Validation

### Tests d'Intégration
```python
def test_run_step_endpoint():
    """Test POST /api/step/<step_key>/run."""
    payload = {"project_name": "test_project", "video_name": "test.mp4"}
    response = client.post('/api/step5/run', json=payload)
    assert response.status_code == 200
    assert response.json['status'] == 'queued'

def test_invalid_step_key():
    """Test validation step_key."""
    response = client.post('/api/invalid_step/run', json={})
    assert response.status_code == 400
    assert 'Invalid step key' in response.json['error']
```

### Tests de Sécurité
```python
def test_internal_endpoint_without_token():
    """Test protection par token."""
    response = client.post('/api/cache/open', json={"folder_number": 1})
    assert response.status_code == 401

def test_internal_endpoint_with_token():
    """Test accès autorisé."""
    headers = {'X-Worker-Token': app.config['INTERNAL_WORKER_TOKEN']}
    response = client.post('/api/cache/open', json={"folder_number": 1}, headers=headers)
    assert response.status_code == 200
```

---

## Documentation Croisée

- [Architecture Complète](../core/ARCHITECTURE_COMPLETE_FR.md) : Vue d'ensemble système
- [API Instrumentation](API_INSTRUMENTATION.md) : Détails instrumentation `measure_api`
- [WorkflowService](../features/WORKFLOW_SERVICE.md) : Services délégués
- [CacheService](../features/CACHE_SERVICE.md) : Gestion cache
- [PerformanceService](../features/PERFORMANCE_SERVICE.md) : Métriques et monitoring

---

## Évolution Future

### v4.3 (Planifié)
- **OpenAPI/Swagger** : Génération automatique spécification API
- **Rate Limiting** : Protection par endpoint
- **Webhooks** : Notifications états terminés

### Améliorations Possibles
- **Validation Schéma** : Utilisation `marshmallow` ou `pydantic`
- **Pagination** : Pour endpoints listant des ressources
- **Versioning API** : `/api/v1/...` pour rétrocompatibilité

---

*Généré avec Code-Doc protocol – voir `../cloc_stats.json` et `../complexity_report.txt`.*
