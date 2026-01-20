# Stratégie de Tests — Backend, Intégration et Frontend (ESM/Node)

## Vue d’ensemble
Cette stratégie vise une couverture robuste tout en restant légère côté frontend. Elle combine `pytest` pour Python et des tests ESM/Node ciblés pour des utilitaires frontend.

## Structure
- `tests/unit/` — Tests unitaires des services (e.g., `MonitoringService`, `MySQLService`).
- `tests/unit/test_step5_mp_seek_warmup.py` — Test de non-régression vérifiant le warmup OpenCV (`read` avant `set(CAP_PROP_POS_FRAMES)`) dans le worker multiprocessing STEP5.
- `test_step1_monthly_reset.py` — Tests de la réinitialisation mensuelle du fichier `processed_archives.txt` (cas même mois, changement de mois, initialisation). Import par chemin absolu pour éviter conflits de dépendances.
- `tests/integration/` — Tests des routes API (e.g., `/api/system_monitor`, CSV/Airtable).
- `tests/integration/test_double_encoded_urls.py` — Valide la déduplication CSV/Webhook avec URLs double-encodées, en forçant ponctuellement `DRY_RUN_DOWNLOADS=false` pour exécuter le worker dans un environnement isolé (`tmp_path`).
- `tests/frontend/` — Tests ESM/Node sans framework (e.g., `PollingManager`, `DOMUpdateUtils.escapeHtml`).
- `tests/validation/` — Tests de validation (e.g., MySQL credentials/config).

## Bonnes pratiques obligatoires
- Services uniquement: la logique métier réside dans `services/` (routes minces).
- Docstrings Google style sur fonctions publiques.
- Tests isolés et déterministes; mocks pour accès réseau/externe.

## Variables d’environnement clés
- `DRY_RUN_DOWNLOADS=true` pendant les tests d’intégration liés aux téléchargements pour éviter tout effet de bord disque.
- Exceptions contrôlées: certains tests d’intégration (`test_double_encoded_urls.py`) forcent temporairement `DRY_RUN_DOWNLOADS=false` à l’intérieur d’un sandbox `tmp_path` afin de valider le comportement du worker ; toujours restaurer `true` en fin de test.
- **Source de Données Unique**: Le système utilise exclusivement le Webhook pour le monitoring des téléchargements. Les tests doivent se concentrer sur le service Webhook sans simulation de fallback MySQL/Airtable/CSV.

## Exécution des tests
- Script: `scripts/run_tests.sh` — force `DRY_RUN_DOWNLOADS=true` et lance pytest + tests frontend Node.
- `pytest.ini` — limite la découverte pour éviter les collisions et accélérer la suite.

### Métriques récentes (2025-11-18)
- Total tests: 173
- Passants: 154 (89%)
- Nouveaux tests: 122 (100% ✅)
  - 102 unitaires (Phases 1 & 2)
  - 20 intégration (Priorité 1)

### Nouvelles suites d'intégration
- `tests/integration/test_workflow_integration.py` — 9 tests couvrant STEP5, parsing progression, gestion de séquence et concurrence `WorkflowState`.
- `tests/integration/test_download_integration.py` — 11 tests couvrant le workflow de téléchargement complet, normalisation d'URL, validation dossiers et cas d'erreurs.

## Frontend (ESM/Node)
- `static/utils/PollingManager.js` — backoff adaptatif, gestion d’erreurs et nettoyage.
- `static/utils/DOMBatcher.js` — batch des mises à jour et utilitaires `DOMUpdateUtils` (dont `escapeHtml`).
- Stratégie: scripts Node minimalistes, pas de framework, assertions natives pour vitesse et simplicité CI.

### Tests Frontend - Suite complète (v4.2)

#### Tests critiques ajoutés (Audit 2026-01-17)
- `test_dom_batcher_performance.mjs` — Performance batching avec nombreuses mises à jour
- `test_focus_trap.mjs` — Focus confinement dans modales et restauration élément déclencheur
- **Validation** : `npm run test:frontend` exécuté avec succès (exit code 0)

#### Export pour Tests Node
Les fonctions critiques sont désormais exportées pour permettre les tests de non-régression :

```javascript
// static/uiUpdater.js - export pour tests
export { parseAndStyleLogContent };

// Tests Node correspondants
// tests/frontend/test_log_safety.mjs
import { parseAndStyleLogContent } from '../../static/uiUpdater.js';
```

#### Tests de Non-Régression XSS
- **Objectif** : Valider que `DOMUpdateUtils.escapeHtml()` reste appliqué **avant** tout traitement HTML
- **Approche** : Tests Node injectant des payloads XSS et vérifiant l'échappement
- **Couverture** : `parseAndStyleLogContent()`, `DOMUpdateUtils.escapeHtml()`

#### Tests de Performance Frontend
- **DOMBatcher** : Validation du batching des mises à jour DOM
- **PollingManager** : Tests du backoff adaptatif et gestion d'erreurs
- **Métriques** : Temps de réponse UI, utilisation mémoire, garbage collection

#### Tests d'Intégration WorkflowService
- **Endpoints logs** : Tests de `/api/get_specific_log/*` via `WorkflowService`
- **Configuration** : Validation de `WorkflowCommandsConfig` vs ancien `COMMANDS_CONFIG`
- **Isolation** : Tests que les routes sont bien des "thin controllers"

## Cas de tests recommandés
- Nominal: réponses 200, structure JSON valide, valeurs numériques dans les bornes.
- Erreurs: indisponibilité GPU, erreurs réseau simulées, dépassement de `maxErrors` dans `PollingManager`.
- Limites: grands nombres de dossiers du jour pour Smart Upload, noms spéciaux (échappement), haute charge CPU/RAM.

## Maintenance
- Ajout de tests lors de toute évolution des services/logiciels clés.
- Revue périodique pour supprimer les tests redondants et garder la suite rapide.

## Notes v4.1 (MANDATORY)

- **DRY RUN Téléchargements**: Toujours exécuter la suite avec `DRY_RUN_DOWNLOADS=true` en CI/intégration pour empêcher tout téléchargement réel.
- **Tests Frontend ESM**: Conserver des tests Node ESM légers pour `static/utils/PollingManager.js` (backoff adaptatif) et `DOMUpdateUtils.escapeHtml` (via `static/utils/DOMBatcher.js`).
- **Source Webhook Unique**: Les tests doivent couvrir le service Webhook comme source unique de données, avec mocks/patch d'environnement pour `WEBHOOK_JSON_URL` et variables associées. Pas de cache module-scope pour la configuration.
- (Déprécié) **Tests Rapports Mensuels**: Suite à la suppression des fonctionnalités de rapport, ces tests ne sont plus requis.
- **Tests CSV récents (2026-01-09)**: `tests/integration/test_double_encoded_urls.py` et `test_csv_dry_run.py` couvrent désormais la politique "Dropbox-only" (liens non éligibles ignorés), la politique d’écriture conditionnelle (DRY_RUN vs succès réel) et la détection `_is_url_already_tracked()`. Ajouter des cas simulant des statuts `failed/cancelled/unknown_error` pour garantir que les réessais sont autorisés.

## Tests Lemonfox (v4.1) - Analyse Audio Alternative

### Tests Unitaires
- **`tests/unit/test_lemonfox_audio_service.py`** : Tests du service Lemonfox
  - Validation de la conversion Lemonfox → format STEP4
  - Tests des paramètres de smoothing (gap fill, min on)
  - Mock de l'API Lemonfox pour tests offline
  - Validation des erreurs (timeout, API key invalide)

### Tests d'Intégration
- **`tests/integration/test_lemonfox_wrapper.py`** : Tests du wrapper d'exécution
  - Validation du fallback automatique Lemonfox → Pyannote
  - Tests de configuration des variables d'environnement
  - Validation de l'isolation environnement (importlib)
  - Tests de compatibilité avec STEP5 en aval

### Configuration de Tests
```python
# Variables d'environnement pour tests Lemonfox
STEP4_USE_LEMONFOX=1
LEMONFOX_API_KEY=test_key_mock
LEMONFOX_TIMEOUT_SEC=30
DRY_RUN_DOWNLOADS=true  # Toujours actif en tests
```

### Scénarios de Tests Couverts
1. **Cas nominal** : API Lemonfox réussie, conversion correcte
2. **Erreur API** : Timeout, HTTP 500, clé invalide
3. **Fallback** : Bascule automatique vers Pyannote
4. **Configuration** : Variables manquantes ou invalides
5. **Compatibilité** : Sortie JSON compatible STEP5

### Mocks et Fixtures
```python
@pytest.fixture
def mock_lemonfox_response():
    return {
        "segments": [
            {"start": 1.0, "end": 3.0, "speaker": "A"},
            {"start": 4.0, "end": 6.0, "speaker": "B"}
        ],
        "words": [
            {"start": 1.0, "end": 1.5, "word": "bonjour", "speaker": "A"}
        ]
    }

@pytest.fixture
def lemonfox_service_mock():
    service = LemonfoxAudioService()
    service._call_lemonfox_api = Mock(return_value=mock_response)
    return service
```
