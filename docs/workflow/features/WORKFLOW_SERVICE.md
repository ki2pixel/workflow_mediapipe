# WorkflowService — Orchestrateur Central du Pipeline

## Vue d'Ensemble
`WorkflowService` est le service principal qui orchestre toutes les étapes du pipeline MediaPipe. Il centralise la logique métier et coordonne les interactions entre les différents services.

## Responsabilités
- Exécution des étapes du pipeline (STEP1-STEP7)
- Gestion de l'état du workflow via `WorkflowState`
- Coordination des services spécialisés (Download, CSV, Tracking)
- Monitoring et instrumentation via `PerformanceService`

## Complexité
- **Score Radon** : C (112 lignes)
- **Méthodes critiques** : `get_step_log_file()`, gestion des logs et états

## Patterns d'Usage
```python
# Injection des dépendances
workflow_service = WorkflowService(
    filesystem=filesystem_service,
    state=workflow_state,
    commands=workflow_commands_config
)

# Exécution d'une étape
workflow_service.run_step('step3', payload)
```

## Intégrations
- **WorkflowState** : Gestion thread-safe de l'état
- **WorkflowCommandsConfig** : Configuration centralisée
- **FilesystemService** : Opérations I/O sécurisées
- **PerformanceService** : Métriques et monitoring

## Architecture

### Point d'Entrée Principal
Le service est conçu comme un orchestrateur centralisé qui :
1. **Valide** les requêtes d'étapes via `WorkflowCommandsConfig`
2. **Exécute** les scripts de pipeline dans les environnements virtuels dédiés
3. **Surveille** la progression via `WorkflowState`
4. **Instrumente** les performances via `PerformanceService`

### Gestion des Erreurs
- Validation des préconditions avant chaque étape
- Gestion centralisée des logs et erreurs
- Rollback automatique en cas d'échec critique

### Patterns de Conception
- **Injection de dépendances** : Tous les services sont injectés au constructeur
- **Thin Controllers** : La logique métier est dans les services, pas dans les routes Flask
- **State Management** : Utilisation de `WorkflowState` pour la cohérence multi-thread

## Méthodes Clés

### `run_step(step_key: str, payload: dict) -> None`
Exécute une étape spécifique du pipeline avec validation et monitoring.

### `get_step_log_file(step_key: str) -> str`
Retourne le chemin du fichier de logs pour une étape donnée (complexité C).

### `prepare_step_execution(step_key: str) -> dict`
Prépare l'environnement et valide les préconditions pour l'exécution.

## Configuration
La configuration est gérée via `WorkflowCommandsConfig` :
- Chemins des scripts par étape
- Variables d'environnement spécialisées
- Patterns de logs et fichiers de sortie

## Performance et Monitoring
- Instrumentation via `@measure_api` sur les routes
- Métriques de temps d'exécution par étape
- Surveillance des ressources système

## Sécurité
- Validation des entrées utilisateur
- Gestion sécurisée des chemins de fichiers
- Isolation des environnements virtuels

## Tests
- Tests unitaires pour chaque méthode critique
- Tests d'intégration pour les workflows complets
- Tests de performance sous charge

## Évolution
Le service est conçu pour être évolutif :
- Ajout de nouvelles étapes via configuration
- Support de nouveaux services via injection
- Extension des métriques de monitoring
