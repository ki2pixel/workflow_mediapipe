---
description: Workflow MediaPipe v4.x mandatory coding standards for all files
alwaysApply: true
---

# Workflow MediaPipe v4.x — Cursor Rules

> Toute déviation doit être consignée dans `decisionLog.md`. Références principales : `WorkflowState`, `WorkflowCommandsConfig`, `docs/workflow/*`, `.agents/rules/codingstandards.md`.

## Sommaire
1. [Tech Stack](#tech-stack)
2. [Project Structure](#project-structure)
3. [Code Style](#code-style)
4. [Core Patterns](#core-patterns)
5. [Pipeline (STEP2, STEP3, STEP4, STEP5, STEP6 & STEP7)](#pipeline-step2-step3-step4-step5-step6--step7)
6. [After Effects & CEP (ExtendScript ES3)](#after-effects--cep-extendscript-es3)
7. [Quality & Testing](#quality--testing)
8. [Process & Tooling](#process--tooling)
9. [Common Tasks](#common-tasks)
10. [Anti-Patterns](#anti-patterns)

## Tech Stack
- **Backend** : Flask services Python 3.10 (venv `/mnt/venv_ext4/env`), logique métier confinée à `services/`.
- **Frontend** : JS natif (`static/`, `templates/`) avec `DOMBatcher` + `AppState`; aucun framework SPA.
- **Config** : `.env` → `config/settings.py` → `WorkflowCommandsConfig`, jamais de secrets en dur.
- **Data Management** : Streaming JSON omniprésent (`ijson`, `StreamingJSONOutput`) pour garantir une empreinte RAM O(1). SQLite (`download_history.sqlite3`) est l'unique base de données active via `CSVService`. MySQL est obsolète et confiné dans `services.deprecated.mysql_service` (`USE_MYSQL=false` par défaut).
- **Environnements spécialisés** :
  - `transnet_env/` : Découpage scènes (PyTorch/TensorFlow).
  - `audio_env/` : Analyse audio (Whisper/Lemonfox).
  - `tracking_env_slim/` : Tracking MediaPipe (CPU-optimized, sans GPU torch).
  - `insightface_env/` : Tracking InsightFace (GPU-only, ONNX Runtime).
  - *Note: Environnements créés dynamiquement via `setup_dev_environment.sh`, répertoire `envs/` non peuplé.*

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
- **DOMDiff** : Toujours envelopper les listes dynamiques (ex: `<li>`) dans un conteneur (`<ul>`) avant d'appliquer `DOMDiff.morph` pour éviter la casse du polling.
- Polling : `PollingManager` uniquement, bannir les `setInterval` isolés.
- Composants clés : Logs Overlay (focus trap, sync timeline, fermeture auto), Timeline connectée (badges d'état dynamiques, auto-scroll structurel) et FromSmash/téléchargements externes en lecture seule.

## Core Patterns
### Services
```python
class ExampleService:
    """Service utilisant le pattern singleton pour l'accès aux dépendances."""
    
    @staticmethod
    def perform(step_key: str) -> None:
        workflow_state = get_workflow_state()  # Accès singleton
        # logique métier pure
```
- Pattern singleton privilégié pour `WorkflowState` et `FilesystemService` (accès via `get_workflow_state()`, méthodes statiques).

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
- Journaliser via `PerformanceService` (décorateur) et retourner JSON sérialisable.

### Frontend Updates
```javascript
import { domBatcher } from './utils/DOMBatcher.js';
import { DOMUpdateUtils } from './utils/DOMUpdateUtils.js';

domBatcher.scheduleUpdate(() => {
  const el = document.getElementById('main-log');
  el.textContent = DOMUpdateUtils.escapeHtml(message);
});
```
- Toujours échapper avant insertion; préférer `textContent`. Les boutons Step/Logs vérifient AppState.

### State Sync (AppState ↔ DOM)
- `subscribeToProperty(['steps', stepKey, 'status'])` pour badges Timeline.
- `PollingManager` met à jour `WorkflowState` → `AppState` (jamais de dispatch global).

## Pipeline (STEP2, STEP3, STEP4, STEP5, STEP6 & STEP7)
### STEP2 Conversion
- **Transcodage Parallèle** : Architecture en passe unique via GPU NVENC (jusqu'à 3 workers) avec parallélisation `ffprobe`.
- **Robustesse** : Analyse audio prédictive et fallback CPU automatique (`libx264`).

### STEP3 Transitions (transnet_env)
- **Détection des Scènes** : Modèle TransNetV2 pour identifier les changements de plans.
- **Optimisation GPU & RAM** : Inférence par lot configurable (`batch_size=8`, `mixed_precision=true`, `ffmpeg_threads=1`) et I/O asynchrone pour une empreinte RAM O(1).

### STEP4 Audio (audio_env)
- Extraction via `ffmpeg` preset TV, analyse `Lemonfox` (smoothing) + fallback Pyannote.
- `AUDIO_PROFILE=gpu_fp32` (AMP désactivé) pour éviter divergences GPU/CPU.
- **Isolation GPU** : `AUDIO_GPU_ISOLATION=1` requis. Exécution en sous-processus (`--analyze_single_video`) pour prévenir les fuites VRAM/PyTorch et crash SIGSEGV.
- Import dynamique `services/lemonfox_audio_service.py` via `importlib` pour isoler Flask.

### STEP5 Tracking (tracking_env_slim / insightface_env)
- **Architecture Simplifiée** (Decision 2026-02-03) :
  1. **MediaPipe** (Défaut, CPU) : `tracking_env_slim`. Multiprocessing obligatoire (`TRACKING_CPU_WORKERS`) combiné à `cv2.setNumThreads(0)` pour éviter la contention CPU. Utilisation d'un `frame_buffer` asynchrone.
  2. **InsightFace** (Optionnel, GPU) : `insightface_env`. Activé si `STEP5_ENABLE_GPU=1`.
- **Interdit** : YuNet, EOS, OpenSeeFace, py-feat et OpenCV Haar supprimés.
- **Export Streaming O(1)** : L'utilisation de `StreamingJSONOutput` est obligatoire pour l'export (écriture continue).

### STEP6 Réduction JSON (env)
- **Optimisation O(1)** : Utilisation de `ijson` obligatoire pour lire itérativement les gros JSON.

### STEP7 Pré-traitement AE (env)
- **Entrée/Sortie** : Lit `*_tracking.json` via `ijson` -> génère `*_ae.json` optimisés pour AE.
- **After Effects Integration** : Script AE `Analyse-Écart-X...jsx` priorise les `*_ae.json`.

## After Effects & CEP (ExtendScript ES3)
- **Contraintes Moteur ES3 (.jsx)** : L'environnement AE ExtendScript est limité à ECMAScript 3. 
  - **Interdit** : `const`, `let`, fonctions fléchées `=>`, `map()`, `filter()`, `forEach()`, template literals.
  - **Obligatoire** : Déclarer avec `var`, utiliser des boucles `for` classiques, inclure un polyfill `JSON2` pour le parsing.
  - **Memory Management** : Encapsuler systématiquement les scripts dans des IIFE `(function() { ... })();` pour éviter les fuites globales.
- **Sécurité `system.callSystem()` (Ponts Python)** : Les appels shell vers Python doivent être ultra-sécurisés.
  - Bannir la concaténation brute (ex: `callSystem("python script.py " + userInput)`).
  - Nettoyer systématiquement les chemins Windows et valider les arguments contre l'injection de commandes shell.
- **Performance Batching AE** : Toute mutation de la timeline (calques, keyframes) doit être groupée :
  - Utiliser `app.beginUndoGroup("Action");` ... `app.endUndoGroup();`.
  - Désactiver le rafraîchissement d'interface superflu pendant les exécutions de scripts batchs.
- **Contrats d'Échange CEP/ExtendScript** : 
  - Formats JSON stricts et unifiés (`{ "status": "ok", "data": ... }`).
  - Standardisation des erreurs préfixées : `[JS] Error: ...` ou `[PY] Error: ...` pour simplifier le debugging.

## Quality, Testing & Security
- **Tests** : `tests/unit/` (context managers `patched_workflow_state()`), `tests/integration/`, et `npm run test:frontend` (DOMBatcher, Logs Overlay).
- **CI/Test env** : Exécuter depuis `/mnt/venv_ext4/env` avec `DRY_RUN_DOWNLOADS=true`.
- **Sécurité au Démarrage** : `validate_startup.py` obligatoire. En production (`DEBUG=False`), crash immédiat si secrets `dev-*` détectés.

## Process & Tooling
### Mises à jour de la Documentation
- Appliquer méthodologie `.agents/skills/documentation/SKILL.md` (TL;DR, problem-first, trade-offs).
- Git : Conventional Commits (`feat(step5): ...`, `fix(filesystem): ...`).
- Mettre à jour `docs/workflow/` pour tout changement majeur.
- Monitoring : webhook JSON unique, `CSVService` écrit dans SQLite (`download_history.sqlite3`).

### Politique d’utilisation des Skills
1. **Priorité locale absolue** : Toujours invoquer la skill workspace `workflow-operator` avant toute autre.
2. **Debugging systématique** : Charger `.agents/skills/debugging-strategies/SKILL.md` pour bug/crash.
3. **Catalogue local** : Utiliser les skills locales de `.agents/skills/` (pipeline-diagnostics, step5-gpu-ops, after-effects-scripts, etc.) selon la tâche.
4. **Fallback contrôlé** : Skills globales uniquement si aucune skill locale ne couvre le besoin.
5. **Hiérarchie** : `workflow-operator` > Skills locales > Règles ce doc > Docs > Skills globales.

## Common Tasks
### Ajouter un nouveau service backend
1. Créer `services/<name>_service.py` avec dépendances injectées.
2. Enregistrer dans `WorkflowService` ou route dédiée.
3. Ajouter tests unitaires isolés (fixtures `mock_workflow_state`).

### Configuration Moteurs STEP5
- **MediaPipe** : Ajuster `TRACKING_CPU_WORKERS` dans `.env` selon cœurs disponibles.
- **InsightFace** : Vérifier `STEP5_ENABLE_GPU=1` et la présence des modèles dans `~/.insightface/`. Ne jamais modifier le code pour hardcoder un chemin.

## Anti-Patterns
- Placer du métier dans un blueprint Flask ou manipuler `WorkflowState` sans verrou.
- Accéder au DOM avec `document.getElementById` dès l'import. Utiliser `innerHTML` sans `DOMUpdateUtils.escapeHtml`.
- Démarrer des polls via `setInterval` dispersé (utiliser `PollingManager`).
- Hardcoder des chemins (`/mnt/cache`) ou des commandes.
- Tenter d'activer le GPU sur MediaPipe (non supporté).
- Charger entièrement de gros JSON en RAM avec `json.load()` (utiliser `ijson` et `StreamingJSONOutput` pour un export O(1) RAM).
- JS moderne (ES6+) dans ExtendScript (.jsx) ou appels `callSystem()` non échappés.
- Lancer l'application en production (`DEBUG=False`) avec des secrets/tokens par défaut (`dev-*`).
- Réactiver ou utiliser MySQL en production (déprécié au profit de SQLite/Webhook, confiné dans `services/deprecated/`).

## Notes finales
- Maintenir ce document <12 000 caractères. Réviser après toute évolution majeure.
- Pour toute question, consulter les audits récents (`docs/workflow/audits/`).