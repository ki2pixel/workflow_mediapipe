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
- **Backend** : Flask services Python 3.10 (venv `/mnt/venv_ext4/env`), logique métier confinée à `services/`.
- **Frontend** : JS natif (`static/`, `templates/`) avec `DOMBatcher` + `AppState`; aucun framework SPA.
- **Config** : `.env` → `config/settings.py` → `WorkflowCommandsConfig`, jamais de secrets en dur.
- **Environnements spécialisés** : `env/`, `transnet_env/`, `audio_env/`, `tracking_env/` pour cloisonner les dépendances.

## Project Structure
- `services/` : classes/fonctions pures (aucun accès Flask) ex: `FilesystemService` pour I/O sécurisée.
- `routes/` : validation I/O, instrumentation `PerformanceService`, appel service.
- `workflow_scripts/` : exécutables par étape alignés sur `WorkflowCommandsConfig`.
- `static/` + `templates/` : Timeline, overlay logs, Step Details.
- `docs/workflow/` : référence unique des specs/audits.

## Code Style
- **Clean Code** : supprimer le code mort; commenter seulement le *pourquoi* métier.

### Backend
- Routes minces : validation, `@measure_api`, appel service, réponse JSON (aucune logique métier côté Flask).
- State unique : steps/séquences gérés via `WorkflowState` (RLock), jamais de globales type `PROCESS_INFO`.
- Config : récupérer commandes/paths via `WorkflowCommandsConfig`, bannir les chemins en dur; `CACHE_ROOT_DIR` requis pour le stockage temporaire.
- I/O : passage obligé par `FilesystemService.open_path_in_explorer()` avec verrous.
- Logging : `progress_text` reste texte brut + JSON streaming structuré.

### Frontend
- `AppState.setState()` reste immuable (diff superficiel, aucun `state` muté).
- DOM : `DOMBatcher.scheduleUpdate()` + `DOMUpdateUtils.escapeHtml()` (pas d'`innerHTML` non échappé).
- Polling : `PollingManager` uniquement, bannir les `setInterval` isolés.
- Composants clés : Logs Overlay (focus trap, sync timeline, fermeture auto), Step Details Panel (`aside` contrôlé AppState), FromSmash/téléchargements externes en lecture seule.

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

### Politique d’utilisation des Skills
1. **Priorité locale absolue** : Toujours invoquer la skill workspace `workflow-operator` avant toute autre. Elle définit l’architecture MediaPipe (services/state, venv spécialisés). Si elle couvre la tâche demandée, aucune skill globale ne doit être utilisée.
2. **Debugging systématique** : Pour toute tâche de debugging (bug, crash, performance, erreur), charger immédiatement `.windsurf/skills/debugging-strategies/SKILL.md` après `workflow-operator` afin d’appliquer la méthodologie locale (reproduction, collecte, hypothèse, test).
3. **Catalogue local étendu** : Après `workflow-operator`, utiliser en priorité les skills workspace suivantes selon la tâche :
   - **pipeline-diagnostics** : vérifications `.env`, venvs, drivers, SQLite avant exécutions STEP1→STEP7.
   - **step5-gpu-ops** : sélection moteur STEP5, tuning CPU/GPU, profiling, diagnostics JSON.
   - **step4-audio-orchestrator** : opérations Lemonfox/Pyannote, profils CUDA, gestion OOM.
   - **csv-monitoring-sme** : supervision `CSVService`, historique SQLite, politique Dropbox-only.
   - **frontend-timeline-designer** : structure Timeline connectée, AppState, auto-scroll, Step Details.
   - **logs-overlay-conductor** : overlay logs Phases 2‑4, auto-open toggle, focus trap.
   - **workflow-docs-updater-plus** : synchronisation docs `docs/workflow/*` + Memory Bank.
   - **tests-suite-guardian** : exécution/maintenance des suites backend/frontend (pytest, npm, scripts STEP3/STEP5).
4. **Fallback contrôlé sur les skills globales** (`/home/kidpixel/.codeium/skills/`) :
   - **Backends Python** : `python-backend-architect`, `python-coding-standards`, `python-cleanup`, `python-db-migrations` — seulement après avoir appliqué les skills locales pertinentes et pour des décisions intra-fichier (typage strict, migrations, nettoyage ciblé).
   - **Frontends & UI** : `frontend-design`, `modern-vanilla-web`, `css-layout-development`, `ui-component-builder`, `interaction-design-patterns`, `html-tools` — utilisables lorsque l’UI dépasse le périmètre couvert par `frontend-timeline-designer` ou `logs-overlay-conductor`, tout en respectant les patterns locaux.
   - **Docs & Process** : `code-doc`, `creating-windsurf-rules`, `architecture-tools`, `canvas-design`, `algorithmic-art`, `pdf-toolbox`, `media-ai-pipeline`, `devops-sre-security`, `engineering-features-for-machine-learning`, `postgres-expert`, `slack-gif-creator` — uniquement si aucune skill locale ne couvre la portée et après validation que le besoin sort du pipeline MediaPipe.
5. **Exclusions** : Bannir l’usage d’une skill globale lorsqu’elle proposerait un scaffolding, une convention dossier ou une stack incompatible avec ce document. Documenter le refus dans `decisionLog.md` si la pression vient d’une contrainte externe.
6. **Hiérarchie de résolution** :
   - `workflow-operator` → skills locales pertinentes → règles de ce document → documentation `docs/workflow/*`.
   - Ensuite seulement, compléter avec la skill globale adaptée pour rester DRY.
7. **Traçabilité** : Lorsqu’une skill globale est mobilisée, mentionner laquelle et expliquer pourquoi aucune skill locale n’était suffisante (PR ou compte-rendu), afin de garder l’audit lisible.

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
- Maintenir ce document <12 000 caractères (actuellement ~6 k). Réviser après toute évolution majeure (nouveau moteur STEP5, changement AppState, refonte UI).
- Pour toute question, consulter les audits récents (`docs/workflow/audits/`) avant d’ajouter une règle.