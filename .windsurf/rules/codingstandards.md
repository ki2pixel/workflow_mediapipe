---
trigger: always_on
description: 
globs: 
---

# Standards de Développement Workflow MediaPipe v4.1

> **Statut** : MANDATORY — applicables immédiatement à tout nouveau code et à toute maintenance.
> **Sources** : `.windsurf/rules/codingstandards.md`, décisions récentes (`memory-bank/decisionLog.md`), addendum v4.1 et guides `docs/workflow/{core,technical,pipeline,features}/*`.

---

## 1. Vue d'ensemble

- **Objectif** : architecture cohérente, sécurisée, performante et testable pour le pipeline multi-étapes.
- **Portée** : backend Flask, frontend JS natif, scripts d'étapes, historique téléchargements, tests (pytest + Node).
- **Principe** : logique métier dans `services/`, routes minces, état + configuration centralisés.

---

## 2. Architecture Backend (Flask + Services)

- **Clean Code** : Pas de code mort commenté (supprimer directement). Commentaires : Expliquer le "Pourquoi" (intention métier), pas le "Comment" (syntaxe évidente).

### 2.1 Service Layer (MANDATORY)
- Logique métier uniquement dans `services/*.py`.
- Routes : validation, appel du service, JSON de sortie (pas de FS/subprocess/log parsing/appels réseau ici).

### 2.2 État Centralisé — `WorkflowState`
- Source unique pour steps, séquences et téléchargements (statut, progression, logs, `progress_text`).
- API : `initialize_all_steps`, `get_step_info`, `update_step_status`, `update_step_progress`, `set_step_field`, `start_sequence`, `complete_sequence`, `get_sequence_outcome`.
- **Interdits** : `PROCESS_INFO*`, `sequence_lock`, `is_currently_running_any_sequence`, `LAST_SEQUENCE_OUTCOME` ou tout global équivalent.

### 2.3 Configuration des commandes — `WorkflowCommandsConfig`
- Source unique (`config/workflow_commands.py`) pour commandes, CWD, logs, regex et interpréteurs d'étapes.
- API : `get_step_config`, `get_step_command`, `get_step_cwd`, `get_all_step_keys`, `update_hf_token`.
- **Interdits** : dupliquer commandes/CWD/regex.
- Les workers STEP5 rechargent `.env` pour appliquer `STEP5_ENABLE_PROFILING`, `STEP5_BLENDSHAPES_THROTTLE_N`, `STEP5_OPENSEEFACE_*`, `STEP5_YUNET_MAX_WIDTH`, `STEP5_MEDIAPIPE_MAX_*`, etc.

### 2.4 Environnements virtuels spécialisés
- `env/` (Flask + steps 1,2,6,7), `transnet_env/` (step 3), `audio_env/` (step 4), `tracking_env/` (step 5).
- Les scripts d'étapes utilisent l'interpréteur dédié ; `audio_env` charge les services via `importlib` pour éviter Flask-Caching.

### 2.5 Gestion des ressources & instrumentation
- `utils.resource_manager` obligatoire pour subprocess/fichiers/verrous.
- **Accès Disque** : Tout accès au cache ou à l'historique doit passer par `FilesystemService` ou `DownloadHistoryRepository` pour garantir les permissions (chown/chmod) et le verrouillage (SQLite WAL).
- Routes instrumentées via `measure_api()` → `PerformanceService`.
- `progress_text` = texte pur (`\n` autorisé). Frontend : `textContent`. Test associé : `tests/unit/test_progress_text_safety.py`.

### 2.6 Configuration, sécurité et source de données
- Paramètres via `config.settings.config` + `.env` (pas de secrets en dur) et décorateurs `config.security`.
- **Gestion des chemins et UI** : `CACHE_ROOT_DIR` définit la racine (pas de chemins en dur). L'ouverture de l'explorateur se fait uniquement via `FilesystemService.open_path_in_explorer()` avec garde-fous (interdit si `DISABLE_EXPLORER_OPEN` ou headless).
- Webhook JSON est la **seule** source de monitoring (`WEBHOOK_*`). `CSVService` agit comme façade Webhook (normalisation URLs).
- Variables obsolètes : `USE_MYSQL`, `USE_AIRTABLE`, `USE_WEBHOOK`, `CSV_MONITOR_URL`, `CSV_MONITOR_INTERVAL`.

### 2.7 Historique des téléchargements — SQLite (MANDATORY)
- **Persistance** : SQLite via `services/download_history_repository.py` (unique source de vérité, remplace `download_history.json`).
- **API Repository** : `initialize`, `get_download_history`, `upsert_many`, `replace_all`. L'accès direct au fichier DB est interdit hors du repository.
- **Migration** : `scripts/migrate_download_history_to_sqlite.py` requis pour convertir les anciens fichiers JSON.
- **Logique** : `CSVService` utilise le repository pour la synchronisation. Tri chronologique et timestamps local time garantis par la base.

### 2.8 Scripts spécialisés STEP4 / STEP5
- **STEP4** : extraction `ffmpeg`, preset `config/optimal_tv_config.json`, profil `AUDIO_PROFILE=gpu_fp32`, fallback Pyannote/Lemonfox avec smoothing `LEMONFOX_SPEECH_*`.
- **STEP5** : mode CPU (`TRACKING_DISABLE_GPU=1`, workers ajustés), création des TMP via helpers WorkflowService, multiprocessing avec warmup `cap.read()` + retry, JSON dense (`tracked_objects: []` si vide), chunking via `/api/step5/chunk_bounds`, registry `STEP5_OBJECT_DETECTOR_MODEL[_PATH]` (pas de hardcode), filtrage blendshapes (`STEP5_BLENDSHAPES_*`), downscale (`STEP5_YUNET/MAX_WIDTH` variants) avec rescale coord, profiling toutes les 20 frames.

---

## 3. Architecture Frontend (JS natif)

- **Clean Code** : Pas de code mort commenté (supprimer directement). Commentaires : Expliquer le "Pourquoi" (intention métier), pas le "Comment" (syntaxe évidente).

### 3.1 Gestion d'état — `AppState`
- Source unique (steps, panneaux, préférences, diagnostics, Smart Upload). `setState` immutable + subscriptions ciblées.

### 3.2 DOMBatcher & DOMUpdateUtils (MANDATORY)
- `domBatcher.scheduleUpdate()` pour les lots.
- `DOMUpdateUtils.escapeHtml()` pour tout contenu dynamique (y compris noms de fichiers/URLs).
- Accès DOM défensif (helpers avec `console.warn` si manquant).

### 3.3 Polling adaptatif — `PollingManager`
- Tous les pollings passent par `PollingManager`, qui peut temporiser (backoff) en cas d’erreurs.

- **Modales** : `role="dialog"`, `aria-modal="true"`, focus trap, `Escape`, restauration focus.
- **Smart Upload** : mode compact unique, préchargement dossiers du jour, DOMBatcher + ErrorHandler.
- **FromSmash** : pas de DL auto, ouverture contrôlée, sanitisation.
- **Diagnostics** : modale A11y, contenu rafraîchi, backed par `/api/system/diagnostics`.

### 3.5 Sécurité XSS
- Pas d’`innerHTML` dynamique : préférer `textContent`/`setAttribute` + contenu échappé.
- URLs externes nettoyées avant usage.

### 3.6 CSS & thèmes
- Styles dans `static/css/`, basés sur `variables.css`. Mode compact = comportement par défaut (plus de toggle).

---

## 4. Standards de Tests

### 4.1 Organisation
- Toutes les exécutions `pytest -q` doivent être lancées depuis l’environnement virtuel `/mnt/venv_ext4/env` (activation obligatoire avant la commande).
- **pytest** : `tests/unit/` (services/helpers), `tests/integration/` (routes + instrumentation), `tests/validation/` (schémas/JSON).
- **Node/ESM** : `tests/frontend/` couvre DOMBatcher, PollingManager, helpers fetch/XSS. Toute nouvelle utilitaire doit y figurer.

### 4.2 DRY_RUN & effets de bord
- `DRY_RUN_DOWNLOADS=true` en CI/tests (seuls les tests prévus l’override). Aucun téléchargement ou appel réseau réel.

### 4.3 Instrumentation & métriques
- Les tests d’intégration vérifient aussi `PerformanceService` (`/api/system_monitor`, `/api/step5/chunk_bounds`, etc.).

### 4.4 Données de référence STEP4/STEP5
- Couvrir : downscale/rescale YuNet/OpenSeeFace, padding blendshapes 468→478, filtrage `STEP5_BLENDSHAPES_PROFILE`, registry object detector.
- STEP4 : preset Pyannote, fallback Lemonfox (importlib), smoothing `LEMONFOX_SPEECH_*`, profil `gpu_fp32`.

### 4.5 Patterns de Mock et Tests d'Intégration (MANDATORY)
- **Helpers de mock** : Utiliser les helpers standardisés de `tests/conftest.py` (`mock_workflow_state`, `mock_app`) pour les tests de service.
- **Patch des états** : Privilégier `patched_workflow_state()` et `patched_commands_config()` pour les tests `WorkflowService`.
- **Isolation environnement** : Les tests nécessitant des dépendances spécialisées (STEP3/STEP5) doivent utiliser les scripts dédiés (`scripts/run_step3_tests.sh`, `scripts/run_step5_tests.sh`).
- **DRY_RUN obligatoire** : `DRY_RUN_DOWNLOADS=true` doit être activé pour tous les tests (défini dans `tests/conftest.py`).

---

## 5. Patrons techniques v4.1

### 5.1 STEP4 — Analyse audio
- Extraction `ffmpeg`, écriture JSON streaming, preset TV, `AUDIO_DISABLE_GPU/AUDIO_CPU_WORKERS` selon besoin.
- Lemonfox (`STEP4_USE_LEMONFOX`, `LEMONFOX_*`) avec smoothing + fallback Pyannote ; profil `gpu_fp32` (sans AMP).

### 5.2 STEP5 — Suivi vidéo
- Mode CPU-only, warmup `cap.read()` avant `cap.set()`, JSON dense, chunking via API, multiprocessing pour YuNet/OpenSeeFace/MediaPipe.
- Blendshapes : padding 468→478 + profils export, registry object detector, `.env` propagé pour profiling/throttle/downscale.

### 5.3 JSON & logs
- Logs `[Progression-MultiLine]`, `[PROFILING]` toutes les 20 frames, écriture JSON streaming recommandée.

---

## 6. Documentation & Git

- Docstrings Google-style, docs `docs/workflow/` organisées thématiquement (`core/`, `technical/`, `pipeline/`, `features/`) et alignées avec le code (Webhook-only, Smart Upload, diagnostics, STEP4/5).
- Guides : rappeler `DRY_RUN_DOWNLOADS` + tests Node/ESM.
- Commits : Conventional Commits (`type(scope): description`).
- Contributions majeures → mettre à jour `memory-bank/decisionLog.md` + `admin/UPDATE_DOCUMENTATION_SUMMARY.md`.

---

## 7. Application, refactoring et contrôle

- **Application immédiate** : tout nouveau code respecte ces standards.
- **Refactoring progressif** : rapprocher les modules modifiés des patrons (WorkflowState, Registry, Webhook-only, etc.).
- **Revues** : vérifier backend/frontend/tests/sécurité avant fusion, consigner les écarts majeurs dans le `decisionLog`.