---
name: Workflow MediaPipe v4.x Coding Standards
description: Mandatory coding standards for all files in the workflow_mediapipe project
alwaysApply: true
---

# Workflow MediaPipe v4.x — Cursor Rules

> Toute déviation doit être consignée dans `decisionLog.md`. Références principales : `WorkflowState`, `WorkflowCommandsConfig`, `docs/workflow/*`, `.continue/rules/codingstandards.md`.

## Sommaire
1. [Tech Stack](#tech-stack)
2. [Project Structure](#project-structure)
3. [Code Style](#code-style)
4. [Core Patterns](#core-patterns)
5. [Pipeline STEP4, STEP5 & STEP7](#pipeline-step4--step5--step7)
6. [Quality & Testing](#quality--testing)
7. [Process & Tooling](#process--tooling)
8. [Common Tasks](#common-tasks)
9. [Anti-Patterns](#anti-patterns)

## Tech Stack
- **Backend** : Flask services Python 3.10 (venv `/mnt/venv_ext4/env`), logique métier confinée à `services/`.
- **Frontend** : JS natif (`static/`, `templates/`) avec `DOMBatcher` + `AppState`; aucun framework SPA.
- **Config** : `.env` → `config/settings.py` → `WorkflowCommandsConfig`, jamais de secrets en dur.
- **Environnements spécialisés** :
  - `transnet_env/` : Découpage scènes (PyTorch/TensorFlow).
  - `audio_env/` : Analyse audio (Whisper/Lemonfox).
  - `tracking_env_slim/` : Tracking MediaPipe (CPU-optimized, sans GPU torch).
  - `insightface_env/` : Tracking InsightFace (GPU-only, ONNX Runtime).

## Project Structure
- `services/` : classes/fonctions pures (aucun accès Flask) ex: `FilesystemService` pour I/O sécurisée.
- `routes/` : validation I/O, instrumentation `PerformanceService`, appel service.
- `workflow_scripts/` : exécutables par étape alignés sur `WorkflowCommandsConfig`.
- `static/` + `templates/` : Timeline, overlay logs et settings consolidés.
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
- Composants clés : Logs Overlay (focus trap, sync timeline, fermeture auto), Timeline connectée (badges d'état dynamiques, auto-scroll structurel) et FromSmash/téléchargements externes en lecture seule. (Le panneau Step Details a été retiré le 2026-02-04.)

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
- Validation d'entrée avant d'appeler un service.
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

## Pipeline STEP4, STEP5 & STEP7
### STEP4 Audio (audio_env)
- Extraction audio via `ffmpeg` preset TV, analyse `Lemonfox` (avec smoothing) + fallback Pyannote.
- Profil imposé `AUDIO_PROFILE=gpu_fp32` (AMP désactivé) pour éviter divergences GPU/CPU.
- Import dynamique `services/lemonfox_audio_service.py` via `importlib` pour isoler Flask.

### STEP5 Tracking (tracking_env_slim / insightface_env)
- **Architecture Simplifiée** (Decision 2026-02-03) :
  1. **MediaPipe** (Défaut, CPU) : Utilise `tracking_env_slim`. Multiprocessing obligatoire (`TRACKING_CPU_WORKERS`).
  2. **InsightFace** (Optionnel, GPU) : Utilise `insightface_env`. Activé uniquement si `STEP5_ENABLE_GPU=1`.
- **Interdit** : YuNet, EOS, OpenSeeFace, py-feat et OpenCV Haar sont supprimés.
- **Règles d'export** : JSON dense frame-by-frame, `tracked_objects` vide si aucune détection.
- **Optimisations** : Warmup `cap.read()`, chunking adaptatif interne.
- **GPU** : Réservé strictement à InsightFace (ONNX Runtime). MediaPipe tourne toujours sur CPU.

### STEP7 Pré-traitement AE (env)
- **Objectif** : Optimiser les données JSON pour After Effects en pré-traitant les sorties STEP6.
- **Entrée** : Fichiers `*_tracking.json` (sortie STEP6) et JSON audio associés.
- **Sortie** : Fichiers `*_ae.json` optimisés pour AE avec structures pré-indexées.
- **Patterns** : Utiliser les patterns de progression définis dans `WorkflowCommandsConfig._get_step7_config()`.
- **After Effects Integration** : Le script AE `Analyse-Écart-X...jsx` priorise les `*_ae.json` avec fallback sur STEP6/STEP5.

## Quality & Testing
- **Tests unitaires** : `tests/unit/` pour services isolés. Utiliser fixtures `patched_workflow_state()` et `patched_commands_config()`.
- **Tests intégration** : `tests/integration/` couvrent routes + WorkflowService.
- **Tests frontend** : Node/ESM (`npm run test:frontend`) pour DOMBatcher, Step Details, focus trap, log safety.
- **CI/Test env** : exécuter depuis `/mnt/venv_ext4/env` avec `DRY_RUN_DOWNLOADS=true` pour bloquer les téléchargements réseau.
- Skips conditionnels autorisés pour STEP3/STEP5 quand dépendances spécialisées manquent, mais documenter les limitations.

## Process & Tooling

### Mises à jour de la Documentation
- Toute création ou modification de documentation (README, docs/, guides Markdown) **doit** appliquer la méthodologie définie dans `.continue/rules/documentation.md` (TL;DR en premier, ouverture problem-first, blocs ❌/✅, trade-offs, Golden Rule). Considérer ce fichier skill comme la checklist obligatoire avant toute rédaction.
- Git : Conventional Commits (`feat(step5): ...`, `fix(filesystem): ...`).
- Documentation : chaque changement majeur doit mettre à jour `docs/workflow/` (guide pipeline, audits, security notes).
- Scripts : lancer les étapes via `WorkflowCommandsConfig` uniquement; pas d'invocation directe des scripts sans passer par `utils.resource_manager`.
- Monitoring : webhook JSON unique, `CSVService` normalise les URLs et écrit dans SQLite (`download_history.sqlite3`).
- Historique : migrations via script dédié (`scripts/migrate_download_history_to_sqlite.py`).

### Politique d'utilisation des Skills
1. **Priorité locale absolue** : Toujours invoquer la skill workspace `workflow-operator` avant toute autre.
2. **Debugging systématique** : Charger `.continue/rules/debugging-strategies.md` pour bug/crash.
3. **Catalogue local** : Utiliser `pipeline-diagnostics`, `step5-gpu-ops`, `frontend-timeline-designer`, `after-effects-scripts`, `after-effects-cep-panel`, `logs-overlay-conductor`, `workflow-docs-updater-plus`, `csv-monitoring-sme`, `debugging-strategies`, `step4-audio-orchestrator`, `tests-suite-guardian`, `workflow-operator`, `documentation` selon la tâche.
4. **Fallback contrôlé** : Skills globales uniquement si aucune skill locale ne couvre le besoin.
5. **Hiérarchie** : `workflow-operator` > Skills locales > Règles ce doc > Docs > Skills globales.

## Common Tasks
### Ajouter un nouveau service backend
1. Créer `services/<name>_service.py` avec dépendances injectées.
2. Enregistrer dans `WorkflowService` ou route dédiée.
3. Ajouter tests unitaires isolés (fixtures `mock_workflow_state`).
4. Documenter la responsabilité dans `docs/workflow/features/`.

### Configuration Moteurs STEP5
- **MediaPipe** : Ajuster `TRACKING_CPU_WORKERS` dans `.env` selon cœurs disponibles.
- **InsightFace** : Vérifier `STEP5_ENABLE_GPU=1` et la présence des modèles dans `~/.insightface/`. Ne jamais modifier le code pour hardcoder un chemin.

### Mettre à jour l'overlay logs frontend
1. Modifier `static/css/components/logs.css` pour le style.
2. Adapter `static/uiUpdater.js` pour alimenter header/timer.
3. Synchroniser AppState (`logPanel.isOpen`) + Step Details pour éviter overlap.

## Anti-Patterns
- Placer du métier dans un blueprint Flask ou manipuler `WorkflowState` sans verrou.
- Accéder au DOM avec `document.getElementById` dès l'import (utiliser getters lazy).
- Utiliser `innerHTML` sans `DOMUpdateUtils.escapeHtml`.
- Démarrer des polls via `setInterval` dispersé (utiliser `PollingManager`).
- Hardcoder des chemins (`/mnt/cache`) ou des commandes.
- Tenter d'activer le GPU sur MediaPipe (non supporté dans cette stack).

## Notes finales
- Maintenir ce document <12 000 caractères. Réviser après toute évolution majeure.
- Pour toute question, consulter les audits récents (`docs/workflow/audits/`).
