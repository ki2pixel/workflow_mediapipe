---
trigger: always_on
description: 
globs: 
---

---
description: Workflow MediaPipe v4.x mandatory coding standards for all files
alwaysApply: true
---

# Workflow MediaPipe v4.x — Cursor Rules

> Toute déviation doit être consignée dans `decisionLog.md`. Références principales : `WorkflowState`, `WorkflowCommandsConfig`, `docs/workflow/*`, `.windsurf/rules/codingstandards.md`.

## Sommaire
1. [Tech Stack](#tech-stack)
2. [Project Structure](#project-structure)
3. [Code Style](#code-style)
4. [Core Patterns](#core-patterns)
5. [Pipeline STEP4 & STEP5](#pipeline-step4--step5)
6. [Quality & Testing](#quality--testing)
7. [Process & Tooling](#process--tooling)
8. [Common Tasks](#common-tasks)
9. [Anti-Patterns](#anti-patterns)

## Tech Stack
- **Backend** : Flask + services Python 3.10, exécuté depuis `/mnt/venv_ext4/env`. Toute logique métier vit dans `services/` (pas dans les routes).
- **Frontend** : JavaScript natif modulaire (`static/` + `templates/`), DOM géré via `DOMBatcher` et état via `AppState`. Pas de frameworks SPA.
- **Config** : `.env` → `config/settings.py` → `WorkflowCommandsConfig`. Secrets uniquement via env vars.
- **Environnements spécialisés** : `env/`, `transnet_env/`, `audio_env/`, `tracking_env/` pour isoler les dépendances pipeline.

## Project Structure
- `services/`: classes/fonctions pures (pas d'accès Flask). Exemple : `FilesystemService` pour I/O disque sécurisé.
- `routes/`: validation I/O + appel service, instrumentation via `PerformanceService`.
- `workflow_scripts/`: exécutables par étape (respecter `WorkflowCommandsConfig`).
- `static/` + `templates/`: UI Timeline connectée, overlay logs, Step Details.
- `docs/workflow/`: source de vérité pour la documentation pipeline/audits.

## Code Style
- **Clean Code** : supprimer immédiatement tout code mort commenté; les commentaires restants doivent expliquer le *pourquoi* métier plutôt que le *comment* évident.

### Backend
- Routes minces : validation, mesure (`@measure_api`), appel service, réponse JSON. Pas de logique métier dans Flask.
- State unique : manipuler les steps/séquences uniquement via `WorkflowState` (RLock). Aucune globale type `PROCESS_INFO`.
- Config : obtenir commandes/paths via `WorkflowCommandsConfig`. Pas de chemins hardcodés; `CACHE_ROOT_DIR` obligatoire pour stockage temporaire.
- I/O : tous les accès disque passent par `FilesystemService.open_path_in_explorer()` et respectent les verrous.
- Logging : `progress_text` = texte brut + JSON streaming (pas de structures libres).

### Frontend
- `AppState.setState()` immuable, comparer via diff superficiel; ne jamais muter `state` directement.
- DOM updates : toujours via `DOMBatcher.scheduleUpdate()` + helpers `DOMUpdateUtils.escapeHtml()` (interdiction `innerHTML` avec données dynamiques).
- Polling : uniquement via `PollingManager` (backoff adaptatif). Pas de `setInterval` dispersé.
- Composants critiques :
  - **Logs Overlay** : focus trap + sync Timeline + fermeture automatique.
  - **Step Details Panel** : `aside` contrôlé par AppState, navigation clavier.
  - **FromSmash / téléchargements externes** : lecture seule, jamais de téléchargement automatique.

## Core Patterns
### Services
```python
class ExampleService:
    def __init__(self, filesystem: FilesystemService, state: WorkflowState):
        self._fs = filesystem
        self._state = state

    def perform(self, step_key: str) -> None:
        with self._state.step_context(step_key):
            payload = self._fs.read_json(...)
            # logique métier pure
```
- Toujours injecter les dépendances (FilesystemService, WorkflowState, WorkflowCommandsConfig) au constructeur.

### Routes
```python
@api_blueprint.post("/api/step/<step_key>/run")
@measure_api("run_step")
def run_step(step_key: str):
    payload = request.get_json()
    validate_step(step_key)
    workflow_service.run_step(step_key, payload)
    return jsonify({"status": "queued"})
```
- Validation d’entrée avant d’appeler un service.
- Journaliser via `PerformanceService` (décorateur) et retourner uniquement JSON sérialisable.

### Frontend Updates
```javascript
import { domBatcher } from './utils/DOMBatcher.js';
import { DOMUpdateUtils } from './utils/DOMUpdateUtils.js';

domBatcher.scheduleUpdate(() => {
  const el = document.getElementById('main-log');
  el.textContent = DOMUpdateUtils.escapeHtml(message);
});
```
- Toujours échapper avant insertion; préférer `textContent`. Les boutons Step/Logs doivent vérifier AppState (ex: `getAutoOpenLogOverlay`).

### State Sync (AppState ↔ DOM)
- `subscribeToProperty(['steps', stepKey, 'status'])` pour mettre à jour badges Timeline.
- `PollingManager` met à jour `WorkflowState` → `AppState` via actions spécifiques (jamais de dispatch global).

## Pipeline STEP4 & STEP5
### STEP4 Audio (audio_env)
- Extraction audio via `ffmpeg` preset TV, analyse `Lemonfox` (avec smoothing) + fallback Pyannote.
- Profil imposé `AUDIO_PROFILE=gpu_fp32` (AMP désactivé) pour éviter divergences GPU/CPU.
- Import dynamique `services/lemonfox_audio_service.py` via `importlib` pour isoler Flask.
- Variable `AUDIO_PARTIAL_SUCCESS_OK=1` permise pour succès partiels.

### STEP5 Tracking (tracking_env)
- Mode CPU par défaut (`TRACKING_DISABLE_GPU=1`). GPU uniquement pour InsightFace avec `STEP5_ENABLE_GPU=1` + `STEP5_GPU_ENGINES=insightface`.
- Multiprocessing obligatoire : workers configurés via `TRACKING_CPU_WORKERS`, chargement `.env` côté worker.
- Règles d’export : JSON dense frame-by-frame, `tracked_objects` vide si aucune détection.
- Optimisations obligatoires : warmup `cap.read()`, chunking adaptatif interne, registry de modèles (pas de chemins en dur), padding landmarks (468→478) avant blendshapes py-feat, rescale des coordonnées après downscale.
- Logging profiling toutes les 20 frames pour YuNet/FaceMesh/EOS, `cv2.setNumThreads(1)` côté YuNet.
- GPU support : lazy import MediaPipe, injection `LD_LIBRARY_PATH`, logs des providers ONNX.

## Quality & Testing
- **Tests unitaires** : `tests/unit/` pour services isolés. Utiliser fixtures `patched_workflow_state()` et `patched_commands_config()`.
- **Tests intégration** : `tests/integration/` couvrent routes + WorkflowService.
- **Tests frontend** : Node/ESM (`npm run test:frontend`) pour DOMBatcher, Step Details, focus trap, log safety.
- **CI/Test env** : exécuter depuis `/mnt/venv_ext4/env` avec `DRY_RUN_DOWNLOADS=true` pour bloquer les téléchargements réseau.
- Skips conditionnels autorisés pour STEP3/STEP5 quand dépendances spécialisées manquent, mais documenter les limitations.

## Process & Tooling
- Git : Conventional Commits (`feat(step5): ...`, `fix(filesystem): ...`).
- Documentation : chaque changement majeur doit mettre à jour `docs/workflow/` (guide pipeline, audits, security notes).
- Scripts : lancer les étapes via `WorkflowCommandsConfig` uniquement; pas d’invocation directe des scripts sans passer par `utils.resource_manager`.
- Monitoring : webhook JSON unique, `CSVService` normalise les URLs et écrit dans SQLite (`download_history.sqlite3`).
- Historique : migrations via script dédié (`scripts/migrate_download_history_to_sqlite.py`).

## Common Tasks
### Ajouter un nouveau service backend
1. Créer `services/<name>_service.py` avec dépendances injectées.
2. Enregistrer dans `WorkflowService` ou route dédiée.
3. Ajouter tests unitaires isolés (fixtures `mock_workflow_state`).
4. Documenter la responsabilité dans `docs/workflow/features/`.

### Étendre STEP5 avec un moteur
1. Déclarer la configuration dans `.env` + `config/settings.py`.
2. Ajouter le moteur dans le registry `workflow_scripts/step5/face_engines.py` (pas de chemins absolus).
3. Garantir compatibilité multiprocessing (charge `.env`, instrumentation profiling, rescale coords).
4. Mettre à jour les docs (`docs/workflow/pipeline/STEP5_SUIVI_VIDEO.md`).

### Mettre à jour l’overlay logs frontend
1. Modifier `static/css/components/logs.css` pour le style.
2. Adapter `static/uiUpdater.js` pour alimenter header/timer.
3. Synchroniser AppState (`logPanel.isOpen`) + Step Details pour éviter overlap.
4. Ajouter/mettre à jour tests (`tests/frontend/test_timeline_logs_phase2.mjs`).

## Anti-Patterns
- Placer du métier dans un blueprint Flask ou manipuler `WorkflowState` sans verrou (utiliser ses méthodes atomiques).
- Accéder au DOM avec `document.getElementById` dès l’import (utiliser getters lazy dans `domElements`).
- Utiliser `innerHTML` avec contenu dynamique non échappé (obligatoire d’utiliser `DOMUpdateUtils.escapeHtml`).
- Démarrer des polls via `setInterval` dispersé (toujours passer par `PollingManager`).
- Hardcoder des chemins (`/mnt/cache`) ou des commandes : lire `WorkflowCommandsConfig`.
- Exporter des JSON STEP5 tronqués ou non densifiés.

## Notes finales
- Maintenir ce document <12 000 caractères (actuellement ~5.5 k). Réviser après toute évolution majeure (nouveau moteur STEP5, changement AppState, refonte UI).
- Pour toute question, consulter les audits récents (`docs/workflow/audits/`) avant d’ajouter une règle.