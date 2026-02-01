# WorkflowService - Orchestrateur Central du Pipeline

> **Code-Doc Context** – Service principal d'orchestration avec 16,005 LOC et complexité radon C sur les méthodes critiques. Backend hotspot: coordination des 7 étapes, gestion d'état thread-safe.

---

## Purpose & System Role

### Objectif
`WorkflowService` est l'orchestrateur central qui coordonne l'exécution des 7 étapes du pipeline, gère l'état global et fournit les APIs pour le frontend et les scripts.

### Rôle dans l'Architecture
- **Position** : Service principal (`services/workflow_service.py`)
- **Prérequis** : WorkflowState, WorkflowCommandsConfig
- **Sortie** : Coordination des étapes, gestion d'état, logs
- **Dépendances** : Tous les autres services, FilesystemService

### Valeur Ajoutée
- **Orchestration unifiée** : Point d'entrée unique pour toutes les opérations
- **Gestion d'état** : WorkflowState thread-safe pour la concurrence
- **Abstraction** : Interface simplifiée pour le frontend
- **Instrumentation** : Monitoring et métriques intégrées

---

## Architecture

### Pattern d'Injection
```python
class WorkflowService:
    def __init__(self, 
                 workflow_state: WorkflowState,
                 commands_config: WorkflowCommandsConfig,
                 filesystem_service: FilesystemService,
                 cache_service: CacheService,
                 performance_service: PerformanceService):
        self._state = workflow_state
        self._config = commands_config
        self._fs = filesystem_service
        self._cache = cache_service
        self._perf = performance_service
```

### Méthodes Principales

#### Exécution des Étapes
```python
@measure_api("run_step")
def run_step(self, step_key: str, payload: dict) -> None:
    """Exécute une ét individuelle avec instrumentation."""
    with self._state.step_context(step_key):
        # Validation, préparation, exécution, monitoring
```

#### Séquences Personnalisées
```python
def run_custom_sequence(self, step_keys: List[str]) -> None:
    """Exécute une séquence d'étapes dans l'ordre."""
    for step_key in step_keys:
        self.run_step(step_key, {})
```

#### Gestion des Logs
```python
def get_step_log_file(self, step_key: str) -> str:
    """Retourne le chemin du fichier de log pour une étape."""
    return self._config.get_step_log_path(step_key)
```

---

## Complexité (Radon Analysis)

### Points Critiques (Score C)
- `get_step_log_file()` : Gestion des chemins et validation
- `run_step()` : Coordination complexe avec état
- `run_custom_sequence()` : Gestion des séquences avec erreurs

### Flux de Contrôle
1. **Frontend → API Routes** : Appels REST vers `/api/step/<key>/run`
2. **API Routes → WorkflowService** : Validation et délégation
3. **WorkflowService → Scripts** : Exécution des étapes via subprocess
4. **Scripts → Services** : Utilisation des services spécialisés
5. **Retour d'état** : Mise à jour WorkflowState → Frontend

---

## Integration Points

### API Routes
```python
# routes/api_routes.py
@api_blueprint.post("/api/step/<step_key>/run")
@measure_api("run_step")
def run_step(step_key: str):
    workflow_service.run_step(step_key, request.get_json())
    return jsonify({"status": "queued"})
```

### Frontend Integration
```javascript
// static/apiService.js
async runStep(stepKey, payload = {}) {
    const response = await fetch(`/api/step/${stepKey}/run`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    });
    return response.json();
}
```

---

## Error Handling & Monitoring

### Gestion des Erreurs
- **Validation** : Vérification des clés d'étape et payloads
- **Timeout** : Gestion des temps d'exécution maximums
- **Rollback** : Nettoyage automatique en cas d'échec
- **Logging** : Journalisation structurée via PerformanceService

### Monitoring
- **Métriques** : Temps d'exécution, taux de succès
- **État** : Progression en temps réel via WorkflowState
- **Alertes** : Notifications en cas d'échec critique

---

## Configuration

### WorkflowCommandsConfig Integration
```python
# Récupération de la configuration d'une étape
step_config = self._config.get_step_config(step_key)
command = self._config.get_step_command(step_key, **params)
```

### Variables d'Environnement
- `CACHE_ROOT_DIR` : Racine des caches temporaires
- `DISABLE_EXPLORER_OPEN` : Désactive l'ouverture explorateur
- `DRY_RUN_DOWNLOADS` : Mode test pour les téléchargements

---

## Testing Strategy

### Tests Unitaires
- **Isolation** : Mock de WorkflowState et WorkflowCommandsConfig
- **Couverture** : Validation, exécution, gestion d'erreurs
- **Fixtures** : `patched_workflow_state()` standardisée

### Tests d'Intégration
- **API Routes** : Validation des endpoints REST
- **Scripts** : Exécution des étapes via subprocess
- **État** : Synchronisation WorkflowState ↔ Frontend

---

## Performance Considerations

### Optimisations
- **Async** : Non-bloquant pour les opérations I/O
- **Cache** : Mise en cache des résultats intermédiaires
- **Parallelisme** : Support du multiprocessing pour STEP5

### Scalabilité
- **Concurrency** : Support multi-clients via WorkflowState
- **Resource Management** : Gestion mémoire et CPU
- **Monitoring** : Métriques temps réel pour l'optimisation

---

## Security Considerations

### Validation
- **Input Validation** : Payloads structurés et typés
- **Path Security** : FilesystemService pour les accès fichiers
- **Command Injection** : Échappement des paramètres subprocess

### Access Control
- **API Authentication** : Token `INTERNAL_WORKER_COMMS_TOKEN`
- **Rate Limiting** : Limitation des appels API
- **Audit Trail** : Journalisation des actions

---

## Evolution & Maintenance

### Architecture v4.1+
- **Services Pattern** : Logique métier dans services, routes minces
- **State Management** : WorkflowState centralisé et thread-safe
- **Configuration** : WorkflowCommandsConfig comme source unique

### Future Enhancements
- **Queue System** : File d'attente pour les tâches longues
- **Distributed** : Support multi-nœuds pour le scaling
- **Event Sourcing** : Historique complet des états
