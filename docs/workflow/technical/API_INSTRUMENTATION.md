# Instrumentation des API (measure_api + PerformanceService)

Ce document décrit la stratégie d'instrumentation des endpoints Flask afin de mesurer et suivre les performances API dans le projet.

## Objectifs
- Mesurer systématiquement le temps de réponse de chaque endpoint.
- Enregistrer le statut HTTP retourné pour faciliter l'analyse des erreurs et des régressions.
- Centraliser les métriques dans `PerformanceService` pour consultation et export.

## Implémentation

### Décorateur `measure_api` (Étendu)
- Emplacement: `routes/api_routes.py`
- Signature: `measure_api(endpoint_name: str, sample_rate: float = 1.0)`
- Comportement:
  - Mesure la durée d'exécution (ms) via `time.perf_counter_ns()` pour une meilleure précision
  - Intercepte le statut HTTP et les erreurs
  - Enregistre les métriques via `PerformanceService` avec des tags enrichis
  - Supporte l'échantillonnage pour réduire la surcharge
  - Génère des logs structurés avec l'ID de requête

### Exemple d'Utilisation

```python
@api_bp.route('/api/step4/lemonfox_audio', methods=['POST'])
@measure_api('/api/step4/lemonfox_audio', sample_rate=0.1)  # 10% des requêtes
async def analyze_audio():
    """Analyse audio Lemonfox avec instrumentation avancée."""
    with PerformanceService.timer('audio_analysis', 
                               tags={"endpoint": "step4_lemonfox_audio"}):
        data = request.get_json()
        result = await LemonfoxAudioService.analyze(data['project_name'], data['video_name'])
        
        # Métriques personnalisées
        PerformanceService.record_metric(
            component="audio",
            metric="processing_time_ms",
            value=result['processing_time'],
            tags={
                "model": result['model'],
                "duration_sec": result['duration']
            }
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

### Journalisation Améliorée

Les logs incluent maintenant des métriques structurées :

```json
{
  "timestamp": "2025-12-19T23:15:42.123Z",
  "level": "INFO",
  "component": "api",
  "request_id": "req_abc123",
  "endpoint": "/api/step4/lemonfox_audio",
  "status_code": 200,
  "duration_ms": 1245.67,
  "metrics": {
    "audio_processing_time_ms": 1200.5,
    "speech_segments": 8,
    "model": "whisper-large-v3"
  },
  "tags": ["audio", "step4", "v4.1.2"]
}
```

### Configuration du PerformanceService

```python
# Configuration de base
PerformanceService.configure(
    enable_metrics=True,
    enable_tracing=True,
    sample_rate=0.1,  # 10% des requêtes
    export_interval=60,  # secondes
    tags={
        "environment": os.getenv("ENV", "dev"),
        "version": "4.1.2",
        "service": "workflow_mediapipe"
    }
)

# Ajout d'exporteurs
if os.getenv("ENABLE_PROMETHEUS"):
    from prometheus_client import start_http_server
    start_http_server(9100)
    PerformanceService.add_exporter(prometheus_exporter)

if os.getenv("ENABLE_ELASTIC"):
    PerformanceService.add_exporter(elastic_exporter)
```

### Enregistrement des métriques
- Service: `services/performance_service.py` (API publique: `PerformanceService.record_api_response_time(...)`, `get_performance_metrics()`, etc.).
- Les routes REST restent des contrôleurs minces et délèguent toute logique métier aux services (règle MANDATORY).

### Endpoints instrumentés (exemples)
- `GET /api/system_monitor`
- `GET /api/system/diagnostics`
- `GET /api/step_status/<step_key>`
- `GET /api/cache/stats`
- `POST /api/performance/reset`
- `GET /api/performance/metrics`
- `GET /api/cache/search`
- `GET /api/cache/list_today`
- `POST /api/cache/open`

### Endpoints de Logs (v4.2 - Mise à jour WorkflowService)

Les endpoints de récupération des logs spécifiques utilisent désormais `WorkflowService` comme point d'entrée unique :

- `GET /api/get_specific_log/<step_key>/<log_index>`
  - **Implémentation** : Délègue à `WorkflowService.get_step_log_file()`
  - **Configuration** : Utilise `WorkflowCommandsConfig` (remplace `COMMANDS_CONFIG`)
  - **Instrumentation** : `@measure_api('/api/get_specific_log/<step_key>/<log_index>')`

**Architecture corrigée** :
```python
# Avant (obsolète)
from config.workflow_commands import COMMANDS_CONFIG

# Après (v4.2)
from config.workflow_commands import WorkflowCommandsConfig
from services.workflow_service import WorkflowService

@api_bp.route('/api/get_specific_log/<step_key>/<log_index>')
@measure_api('/api/get_specific_log/<step_key>/<log_index>')
def get_specific_log(step_key, log_index):
    return WorkflowService.get_step_log_file(step_key, int(log_index))
```

> Remarque: L'instrumentation doit être appliquée à tous les endpoints de `routes/api_routes.py`. Les autres Blueprints doivent suivre le même pattern.

Pour les autres Blueprints (ex: `routes/workflow_routes.py`) :
- Soit réutiliser le décorateur via import (ex: `from routes.api_routes import measure_api`),
- Soit conserver une implémentation locale équivalente.

Dans tous les cas, les routes restent des contrôleurs minces et délèguent la logique métier aux services.

## Consultation des métriques
- Endpoint: `GET /api/performance/metrics`
- Retourne un objet JSON incluant les métriques de profiling, cache, et performances système (selon l'implémentation du service).

## Bonnes pratiques (MANDATORY v4.1)
- Routes minces: aucune logique métier dans les routes; utiliser la couche Services (`services/`).
- Sécurité: appliquer les décorateurs de sécurité de `config/security.py` quand requis (ex: endpoints internes `@require_internal_worker_token`).
- Configuration: lire les flags depuis `config.settings.config` à l'exécution (éviter le cache module-scope pour préserver la testabilité).

## Tests recommandés
- Tests d'intégration (pytest):
  - Vérifier le code HTTP, la forme de la réponse, et l'absence d'exceptions.
  - Optionnel: mesurer un budget de temps maximum indicatif (tolérant) pour détecter les régressions flagrantes.
- Tests unitaires (services):
  - Valider que `PerformanceService.record_api_response_time()` enregistre correctement les données.
- DRY RUN: s'assurer que `DRY_RUN_DOWNLOADS=true` est activé en CI/tests pour éviter tout effet de bord.

## Frontend et instrumentation
- Aucun couplage direct requis: le frontend consomme simplement les endpoints.
- Les latences sont capturées côté backend; le frontend ne fait que réagir (ex: widget System Monitor dans `static/main.js`).

## Maintenance
- Lors de l'ajout d'un nouvel endpoint:
  1. Ajouter `@measure_api('...')` juste au-dessus de la fonction de route.
  2. Déléguer la logique au service dédié.
  3. Ajouter/adapter les tests d'intégration.
  4. Mettre à jour la documentation si l'API publique change (docs `/docs/workflow/`).

## Notes importantes
- **Endpoints de génération de rapports** : Les endpoints `/api/reports/generate` et `/api/reports/generate/project` ont été retirés du système. La documentation a été mise à jour pour refléter ce changement.
- **Endpoints STEP5 supprimés (2026-01-18)** : L'endpoint `/api/step5/chunk_bounds` et les méthodes associées ont été supprimés avec la feature "Étape 5 · Options avancées". Le chunking adaptatif fonctionne désormais avec des valeurs par défaut.
