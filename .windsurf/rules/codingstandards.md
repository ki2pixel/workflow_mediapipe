---
trigger: always_on
description: 
globs: 
---

# Standards Workflow MediaPipe v4.1

> **Statut** : MANDATORY — Tout écart doit être justifié dans `decisionLog.md`.
> **Sources** : `.windsurf/rules/codingstandards.md`, `docs/workflow/*`.

---

## 1. Principes & Architecture

- **Structure** : Logique métier dans `services/` (pur Python), Routes minces (validation/I/O), Frontend JS natif.
- **Code Clean** : Pas de code mort. Commentaires = "Pourquoi" (intention), pas "Comment".
- **État Centralisé** :
  - **Backend** : `WorkflowState` est la source unique (Steps, Séquences, Logs). Interdiction de globales (`PROCESS_INFO`, `sequence_lock`).
  - **Frontend** : `AppState` est la source unique (Timeline, Logs, Préférences). `setState` immutable.
- **Config** : `WorkflowCommandsConfig` centralise commandes/CWD/Regex (pas de duplication). Secrets via `.env`.

## 2. Backend (Flask + Services)

### 2.1 I/O et Persistance
- **Disque** : Accès fichiers via `FilesystemService` uniquement (permissions, verrous). Explorateur via `open_path_in_explorer` (sécurisé).
- **Historique DL** : SQLite obligatoire via `DownloadHistoryRepository`. Migration via script dédié. `CSVService` se synchronise dessus.
- **Monitoring** : Webhook JSON unique source. `CSVService` normalise les URLs.

### 2.2 Exécution & Environnements
- **Envs** : Utiliser l'environnement dédié (`env/`, `transnet_env/`, `audio_env/`, `tracking_env/`).
- **Scripts** : `utils.resource_manager` requis pour subprocess/locks.
- **Instrumentation** : Routes mesurées via `PerformanceService`. Logs `progress_text` (texte pur) + JSON streaming.

## 3. Frontend (JS Natif)

- **DOM** : Mises à jour via `DOMBatcher.scheduleUpdate()`. Échappement obligatoire `DOMUpdateUtils.escapeHtml()` avant insertion (Anti-XSS). Pas d'`innerHTML` dynamique.
- **Polling** : Centralisé par `PollingManager` (avec backoff adaptatif).
- **Composants** :
  - **Logs Overlay** : Focus trap, sync Timeline, fermeture auto.
  - **Step Details** : `aside` contrôlé par AppState.
  - **FromSmash** : Lecture seule, sanitisation, pas de DL auto.

## 4. Spécificités Pipeline (Steps 4 & 5)

### 4.1 STEP 4 (Audio)
- **Engine** : Extraction `ffmpeg` (Preset TV), Analyse `Lemonfox` (Smoothing, Fallback Pyannote).
- **Config** : Profil `gpu_fp32` (sans AMP), `audio_env` charge services via `importlib`.

### 4.2 STEP 5 (Tracking Vidéo)
- **Exécution** : Mode CPU-only (`TRACKING_DISABLE_GPU=1`), Multiprocessing (YuNet/OpenSeeFace).
- **Process** : Warmup `cap.read()`, Chunking adaptatif interne, JSON dense (`tracked_objects: []` si vide).
- **Règles** : Registry pour modèles (pas de path en dur), Filtrage Blendshapes (Padding 468→478), Rescale coords post-downscale.

## 5. QA & Tests

- **Environnement** : Exécution depuis `/mnt/venv_ext4/env`.
- **DRY_RUN** : `DRY_RUN_DOWNLOADS=true` obligatoire en CI/Test (pas d'appels réseau).
- **Structure** :
  - `tests/unit/` : Services isolés (Mocks `conftest.py` standardisés).
  - `tests/integration/` : Routes + `PerformanceService`.
  - `tests/frontend/` : Node/ESM pour DOMBatcher/Utils.
- **Mocking** : Privilégier `patched_workflow_state()` et `patched_commands_config()`.

## 6. Processus

- **Git** : Conventional Commits (`feat(step5): ...`).
- **Docs** : Docstrings Google-style. Mettre à jour `docs/workflow/` lors de changements majeurs.