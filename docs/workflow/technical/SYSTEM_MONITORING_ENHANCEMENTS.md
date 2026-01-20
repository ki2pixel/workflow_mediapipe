# Améliorations du Monitoring Système (CPU/RAM/GPU) et Instrumentation API

## Résumé
Ce document détaille les améliorations apportées au monitoring système, côté backend et frontend, ainsi que l’instrumentation des routes API pour la mesure des performances.

## Backend
- Service: `services/monitoring_service.py`
  - `get_system_status()` agrège CPU, mémoire, GPU et disque, et retourne un horodatage ISO.
  - `get_process_info()` corrigé pour le calcul d’uptime via `time.time() - process.create_time()`.
  - Support GPU conditionnel via `pynvml` si `config.ENABLE_GPU_MONITORING` est activé.
  - Endpoint `/api/system_monitor` (contrôleur mince) délègue à `MonitoringService.get_system_status()`.
  - Décorateur `measure_api('/api/system_monitor')` instrumente le temps de réponse et enregistre via `PerformanceService.record_api_response_time`.
  - Détails sur l’instrumentation: voir [API_INSTRUMENTATION.md](API_INSTRUMENTATION.md)

## Frontend

### Composant de Monitoring

## Bonnes pratiques
- Routes Flask « minces »: aucune logique métier — uniquement appel du service + sérialisation JSON.
- Batching DOM: réduire les reflows/repaints pour un rendu fluide.
- Journalisation: logs de debug non verbeux en production; erreurs envoyées vers `ErrorHandler` côté UI.

## Tests
- Tests unitaires pour `MonitoringService.get_process_info()` (vérification de l’uptime et des métriques de base).
- Tests d’intégration pour `/api/system_monitor` (statut 200 et structure JSON attendue).

## Sécurité
- Aucun secret dans le code; config via `config.settings.config`.
- Aucune commande dangereuse déclenchée par `/api/system_monitor`.

## Points d’extension
- Ajout d’agrégations temporelles dans `PerformanceService` (p95, p99).
- Exposition de métriques Prometheus/Grafana si nécessaire.

## Notes v4.1

- **Backoff adaptatif confirmé**: les callbacks de polling peuvent retourner un délai (ms) pour suspendre puis reprendre automatiquement (`PollingManager.startPolling`).
- **Batching DOM**: conserver `domBatcher.scheduleUpdate()` pour toutes les mises à jour du widget afin d’éviter les reflows.
- **Cache-busting CSS**: pour garantir l’actualisation immédiate des styles du widget, les `<link rel="stylesheet">` dans `templates/index_new.html` utilisent `?v={{ cache_buster }}`.

### Mode Minimizé du Widget
Le widget de monitoring système supporte désormais un mode minimisé pour réduire son empreinte visuelle :
- **Bouton de réduction** : Bouton × pour basculer entre mode normal et compact.
- **Ligne compacte** : Affichage des informations essentielles (CPU %, RAM % + utilisée/totale, GPU % + température) sur une seule ligne.
- **Gestion d'état** : État persisté via `AppState` et `localStorage`.
- **Standards respectés** : Utilisation de `DOMBatcher` pour les mises à jour, accessibilité ARIA, sécurité XSS via `DOMUpdateUtils.escapeHtml`.
- **Instrumentation API**: voir [API_INSTRUMENTATION.md](API_INSTRUMENTATION.md) pour les détails du décorateur `measure_api()` appliqué aux endpoints `/api/system_monitor` et `/api/system/diagnostics`.
