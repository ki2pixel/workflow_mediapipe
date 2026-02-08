# Workflow Service - Orchestrateur Central

**TL;DR** : Service principal qui orchestre toutes les étapes du pipeline MediaPipe avec état centralisé et injection de dépendances.

## Le Problème : Coordination Complexe du Pipeline

Tu as 8 étapes distinctes avec des environnements différents, des dépendances variées et des états à synchroniser. La coordination manuelle est complexe et source d'erreurs. Tu as besoin d'un orchestrateur centralisé qui gère tout automatiquement.

## Notre Solution : Orchestrateur Centralisé avec Injection de Dépendances

Nous utilisons `WorkflowService` comme point d'entrée unique qui orchestre toutes les étapes du pipeline. Chaque service est injecté au constructeur, garantissant une architecture propre et testable.

### ❌ Couplage fort (anti-pattern)
```python
# Approche rigide - dépendances directes
def run_step(step_key):
    # Import direct - test impossible !
    from services.workflow_state import get_workflow_state
    from config.workflow_commands import COMMANDS_CONFIG
    # Couplage fort, pas de mock possible
    ws = get_workflow_state()
    command = COMMANDS_CONFIG[step_key]['command']
    subprocess.run(command)  # Danger : pas de validation
```

### ✅ Injection de dépendances (pattern recommandé)
```python
# Approche propre - testable et maintenable
class WorkflowService:
    def __init__(self, filesystem, state, commands, performance):
        self._fs = filesystem      # Injecté, mockable
        self._state = state        # Injecté, mockable
        self._commands = commands  # Injecté, mockable
        self._performance = performance  # Injecté, mockable
    
    def run_step(self, step_key, payload=None):
        # Utilisation des dépendances injectées
        return self._execute_with_validation(step_key, payload)
```

### Flux d'Orchestration

1. **Validation** : Vérification des prérequis via `WorkflowCommandsConfig`
2. **Exécution** : Lancement du script dans l'environnement approprié
3. **Surveillance** : Monitoring continu via `WorkflowState`
4. **Instrumentation** : Métriques via `PerformanceService`
5. **Nettoyage** : Gestion centralisée des erreurs et rollback

### Architecture Centralisée

```python
# Injection des dépendances principales
workflow_service = WorkflowService(
    filesystem=filesystem_service,      # Gestion I/O sécurisée
    state=workflow_state,              # État centralisé thread-safe
    commands=workflow_commands_config,      # Configuration centralisée
    performance=performance_service,     # Métriques et monitoring
)

# Pattern d'utilisation
workflow_service.run_step("STEP3", payload)
workflow_service.run_custom_sequence(["STEP1", "STEP2", "STEP3"])
workflow_service.get_step_status("STEP3")
```

## Configuration Essentielle

### Variables d'Environnement

```bash
# Configuration générale
FLASK_SECRET_KEY=your-secret-key
INTERNAL_WORKER_COMMS_TOKEN=your-worker-token
RENDER_REGISTER_TOKEN=your-render-token
FLASK_PORT=5000
DEBUG=false

# Environnements virtuels
VENV_BASE_DIR=/mnt/cache/venv/workflow_mediapipe
PYTHON_VENV_EXE_ENV=env/bin/python

# Monitoring
ENABLE_GPU_MONITORING=true
SYSTEM_MONITOR_POLLING_INTERVAL=2000
WEBHOOK_MONITOR_INTERVAL=15
```

### Configuration WorkflowCommandsConfig

```python
# Accès à la configuration
config = WorkflowCommandsConfig()

# Commandes par étape
step1_config = config.get_step_config("step1")
step2_config = config.get_step_config("step2")
step3_config = config.get_step_config("step3")
```

## Architecture Technique

### Service Principal

```python
class WorkflowService:
    def __init__(self, 
                 filesystem: FilesystemService,
                 state: WorkflowState,
                 commands: WorkflowCommandsConfig,
                 performance: PerformanceService):
        self._fs = filesystem
        self._state = state
        self._commands = commands
        self._performance = performance
    
    def run_step(self, step_key: str, payload: dict = None) -> None:
        """Exécute une étape spécifique du pipeline."""
        
    def run_custom_sequence(self, steps: List[str]) -> None:
        """Exécute une séquence personnalisée d'étapes."""
        
    def get_step_status(self, step_key: str) -> dict:
        """Retourne le statutut d'une étape."""
        
    def get_sequence_status(self) -> dict:
        """Retourne le statut de la séquence en cours."""
        
    def get_step_log_file(self, step_key: str) -> str:
        """Retourne le chemin du fichier de logs pour une étape."""
```

## Trade-offs par Mode d'Orchestration

| Mode | Complexité | Testabilité | Performance | Quand l'utiliser |
|------|-----------|------------|-------------|-----------------|
| **Injection DI** | Modérée | Excellente | Légère | Production, tests unitaires |
| **Singleton** | Simple | Difficile | Optimale | Petits projets |
| **Factory** | Élevée | Excellente | Variable | Systèmes complexes |
| **Direct** | Minimale | Nulle | Maximale | Prototypage rapide |

## Trade-offs par Gestion d'Erreurs

| Stratégie | Résilience | Complexité | Risques | Quand l'utiliser |
|-----------|------------|------------|---------|-----------------|
| **Centralisée** | Haute | Moyenne | Point unique | Production |
| **Locale** | Faible | Simple | Isolée | Développement |
| **Hybrid** | Maximale | Élevée | Complexe | Systèmes critiques |
| **Silencieuse** | Nulle | Simple | Perte info | Tests non critiques |

## Analogie : Chef d'Orchestre vs Chef de Cuisine

Pense à l'orchestration comme un **chef d'orchestre** vs un **chef de cuisine**. Le **WorkflowService** est le chef d'orchestre : il coordonne tous les musiciens (étapes) avec une partition claire (WorkflowState), et chaque musicien joue dans son environnement spécialisé (venv). Les **services injectés** sont les chefs de partie : ils sont experts de leur domaine (fichiers, état, performance) et peuvent être remplacés pour les tests. L'**orchestration centralisée** garantit que tout le monde joue la même symphonie.

```python
def run_step_with_error_handling(step_key: str, payload: dict = None) -> None:
    try:
        workflow_service.run_step(step_key, payload)
    except ValidationError as e:
        logger.error(f"Validation failed for {step_key}: {e}")
        workflow_state.set_step_field(step_key, "error", str(e))
    except Exception as e:
        logger.error(f"Unexpected error in {step_key}: {e}")
        workflow_state.set_step_field(step_key, "error", str(e))
        workflow_state.set_step_status(step_key, "failed")
```

## Intégrations Pipeline

### WorkflowState Integration

```python
# Accès à l'état depuis n'importe
from services.workflow_state import get_workflow_state

# Utilisation dans les services
ws = get_workflow_state()
ws.update_step_status("STEP5", "running")
ws.set_step_field("STEP5", "current_video", "video1.mp4")
ws.update_step_progress("STEP5", current=1, total=5)
```

### PerformanceService Integration

```python
# Instrumentation automatique
@measure_api("/api/run/<step_key>")
def run_step(step_key: str):
    """Décorateur automatique des métriques de performance."""
    # Métriques automatiquement enregistrées
    return workflow_service.run_step(step_key)
```

### FilesystemService Integration

```python
# Utilisation sécurisée des fichiers
filesystem_service.open_path_in_explorer(path, "w") as f:
    """Écriture sécurisée avec validation des chemins."""
    # Validation des chemins et permissions
```

## Performance et Monitoring

### Métriques Clés

```python
# Temps d'exécution par étape
step_times = {
    'STEP1': 45.2,
    'STEP2': 120.8,
    'STEP3': 89.3,
    'STEP4': 156.7,
    'STEP5': 234.1,
    'STEP6': 12.3,
    'STEP7': 8.5
}

# Monitoring système
cpu_usage = performance_service.get_system_status()
gpu_usage = performance_service.get_gpu_usage()
memory_usage = performance_service.get_memory_usage()
```

### Patterns de Logging

```python
# Logs de progression
logger.info(f"STEP{step_key} started for {project_name}")
logger.info(f"STEP{step_key} completed in {elapsed:.2f}s")

# Logs d'erreurs
logger.error(f"STEP{step_key} failed: {error}")
logger.warning(f"STEP{step_key} retry in {retry_delay}s")
```

## Résolution de Problèmes

### Étape Échouée

```bash
# Diagnostic
curl http://localhost:5000/api/step_status/STEP3

# Solution
# 1. Vérifier les prérequis dans logs
# 2. Corriger les erreurs de validation
# 3. Relancer l'étape
```

### Environnement Manquant

```bash
# Diagnostic
echo $PYTHONPATH
which python
echo $VIRTUAL_ENV

# Solution
# Vérifier que les bons environnements sont activés
source env/bin/activate  # Pour l'application principale
source tracking_env_slim/bin/activate  # Pour STEP5
source audio_env/bin/activate      # Pour STEP4
source transnet_env/bin/activate     # Pour STEP3
```

### Permissions Insuffisantes

```bash
# Diagnostic
ls -la projets_extraits/
sudo chown -R $USER:$USER projets_extraits/
chmod -R 755 projets_extraits/

# Solution
# Le service utilise les permissions de l'utilisateur courant
source env/bin/python
# Les fichiers sont créés avec les permissions utilisateur par défaut
```

### Service Non Disponible

```bash
# Diagnostic
python -c "from services.workflow_service import WorkflowService; print('WorkflowService available')" || exit 1)

# Solution
# Vérifier que tous les services sont initialisés dans app_new.py
# Vérifier que `init_app()` est appelé avant toute utilisation
```

## Tests et Validation

### Test de Fonctionnement

```python
def test_workflow_service_integration():
    """Test l'intégration complète du service."""
    # Test initialisation
    service = create_workflow_service()
    
    # Test exécution étape
    service.run_step("STEP1")
    assert service.get_step_status("STEP1")["status"] == "completed"
    
    # Test séquence
    service.run_custom_sequence(["STEP1", "STEP2", "STEP3"])
    status = service.get_sequence_status()
    assert status["status"] == "completed"
    
    # Test état
    ws = get_workflow_state()
    assert ws.get_step_status("STEP1")["status"] == "completed"
```

### Test d'Intégration

```python
def test_pipeline_complete():
    """Test le pipeline complet de bout en bout."""
    # Initialisation
    service = create_workflow_service()
    
    # Exécution complète
    service.run_custom_sequence([
        "STEP1", "STEP2", "STEP3", "STEP4", "STEP5", "STEP6", "STEP7", "STEP8"
    ])
    
    # Validation finale
    final_status = service.get_sequence_status()
    assert final_status["status"] == "completed"
    
    # Vérification de la cohérence des données
    ws = get_workflow_state()
    for step in ["STEP1", "STEP2", "STEP3", "STEP4", "STEP5", "STEP6", "STEP7", "STEP8"]:
        assert ws.get_step_status(step)["status"] == "completed"
```

L'étape 8 transforme le chaos des étapes multiples en un système orchestré et fiable. Le service WorkflowService garantit que chaque étape s'exécute dans le bon environnement, avec un état cohérent et une instrumentation complète. Le système est maintenant prêt pour la section suivante de la migration.

---

## Golden Rule

**Injecte avant d'orchestrer ; sinon tu crées des dépendances impossibles à tester et tu rends le système fragile aux changements.**
