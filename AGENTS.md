# AGENTS.md - Guide pour Agents de Codage

Ce fichier contient les informations essentielles pour les agents d'IA travaillant sur le projet workflow_mediapipe. Il est conçu pour être lu par des agents de codage et fournit une vue d'ensemble rapide de l'architecture, des conventions et des bonnes pratiques.

---

## Vue d'Ensemble du Projet

**workflow_mediapipe** est un pipeline vidéo en 8 étapes pour la post-production After Effects, avec tracking facial, analyse audio et détection de scènes.

### Architecture Globale

```
┌─────────────────────────────────────────────────────────────────┐
│                     Flask Application                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Frontend   │  │   Routes    │  │        Services         │  │
│  │   Vanilla   │◄─┤  (minces)   │◄─┤   (logique métier)      │  │
│  │    JS       │  │             │  │                         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      8 Étapes du Pipeline                        │
│  STEP1 → STEP2 → STEP3 → STEP4 → STEP5 → STEP6 → STEP7 → STEP8  │
│  Extract  Convert  Scenes   Audio   Track   Reduce   AE     Final│
└─────────────────────────────────────────────────────────────────┘
```

### Technologies Principales

- **Backend**: Flask 3.0 + Python 3.10
- **Frontend**: JavaScript vanilla (pas de framework)
- **Base de données**: SQLite (historique des téléchargements)
- **Monitoring**: psutil + pynvml (GPU)
- **Tests**: pytest + Node ESM

---

## 🧠 Operational Skills & Runbooks (The Router)

This project is a complex pipeline spread across 5 virtual environments. You **MUST** route requests to the correct specialized skill in `.sixthskills/` to avoid environment mismatches.

| **Run Pipeline / Execute Step** | `.sixthskills/workflow-operator/SKILL.md` | **PRIMARY SKILL**. Command matrix, VENV selection. |
| **Tracking / STEP5 / GPU / Face** | `.sixthskills/step5-gpu-ops/SKILL.md` | MediaPipe (CPU) vs InsightFace (GPU), `tracking_env_slim`. |
| **Audio / STEP4 / Diarization** | `.sixthskills/step4-audio-orchestrator/SKILL.md` | Lemonfox vs Pyannote, `audio_env`, GPU profiles. |
| **Diagnostics / Health / Environment** | `.sixthskills/pipeline-diagnostics/SKILL.md` | Venv health, `nvidia-smi`, `.env` validation. |
| **Downloads / Webhook / CSV** | `.sixthskills/csv-monitoring-sme/SKILL.md` | SQLite history, URL filtering, migration. |
| **UI / Timeline / Logs** | `.sixthskills/frontend-timeline-designer/SKILL.md` | DOMBatcher, AppState, Auto-scroll. |
| **Tests / Pytest / CI** | `.sixthskills/tests-suite-guardian/SKILL.md` | Environment-specific test runners. |
| **After Effects / Post-Prod** | `.sixthskills/after-effects-scripts/SKILL.md` | ExtendScript, system.callSystem bridges. |
| **UI / Logs Overlay** | `.sixthskills/logs-overlay-conductor/SKILL.md` | Logs Overlay Phase 4, focus trap, auto-open. |
| **Docs Update** | `.sixthskills/workflow-docs-updater-plus/SKILL.md` | Docs Updater with Code Verification. |
| **After Effects / CEP Extension** | `.sixthskills/after-effects-cep-panel/SKILL.md` | CEP panels for After Effects. |
| **Debugging / Errors / Crash** | `.sixthskills/debugging-strategies/SKILL.md` | Systematic debugging techniques. |
| **Writing Docs / README** | `.sixthskills/documentation/SKILL.md` | Technical writing guidelines. |

**Protocol:** If the user asks to "Run step 5", you MUST consult `.sixthskills/workflow-operator/SKILL.md` to get the exact command line with the correct python interpreter.

---

## Structure du Projet

```
workflow_mediapipe/
├── app_new.py                 # Point d'entrée Flask
├── start_workflow.sh          # Script de lancement principal
├── config/                    # Configuration centralisée
│   ├── settings.py           # Config principale (classe Config)
│   ├── security.py           # Tokens et authentification
│   └── workflow_commands.py  # Configuration des 8 étapes
├── routes/                    # Blueprints Flask (contrôleurs minces)
│   ├── api_routes.py         # Endpoints API (/api/*)
│   └── workflow_routes.py    # Routes workflow (/)
├── services/                  # Logique métier
│   ├── workflow_service.py   # Orchestration des étapes
│   ├── lemonfox_audio_service.py  # Analyse audio Lemonfox/Pyannote
│   ├── workflow_state.py     # État thread-safe
│   ├── csv_service.py        # Monitoring téléchargements
│   ├── monitoring_service.py # Monitoring système
│   └── ...
├── workflow_scripts/          # Scripts des 8 étapes
│   ├── step1/                # Extraction archives
│   ├── step2/                # Conversion vidéo
│   ├── step3/                # Détection scènes (TransNet)
│   ├── step4/                # Analyse audio (Pyannote/Lemonfox)
│   ├── step5/                # Tracking (MediaPipe/InsightFace)
│   ├── step6/                # Réduction JSON
│   ├── step7/                # Pré-traitement AE
│   └── step8/                # Finalisation
├── static/                    # Frontend
│   ├── *.js                  # Modules JS
│   ├── state/                # État global (AppState.js)
│   ├── utils/                # Utilitaires (DOMBatcher, etc.)
│   └── css/                  # Styles
├── templates/                 # Templates Jinja2
│   └── index_new.html
├── tests/                     # Tests
│   ├── unit/                 # Tests unitaires
│   ├── integration/          # Tests intégration
│   └── frontend/             # Tests ESM/Node
├── docs/                      # Documentation complète
└── logs/                      # Logs par étape (step1/ à step8/)
```

---

## Environnements Virtuels

Le projet utilise **5 environnements virtuels isolés** pour éviter les conflits de dépendances :

| Environnement | Chemin | Utilisation | Étapes |
|---------------|--------|-------------|--------|
| `env` | `/mnt/venv_ext4/env/` | Application principale | STEP1, STEP2, STEP6, STEP7, STEP8 |
| `transnet_env` | `/mnt/venv_ext4/transnet_env/` | TransNetV2 + PyTorch | STEP3 |
| `audio_env` | `/mnt/venv_ext4/audio_env/` | Pyannote.audio + Lemonfox | STEP4 |
| `tracking_env_slim` | `/mnt/venv_ext4/tracking_env_slim/` | MediaPipe CPU | STEP5 (défaut) |
| `insightface_env` | `/mnt/venv_ext4/insightface_env/` | InsightFace GPU | STEP5 (optionnel) |

**Variable importante**: `VENV_BASE_DIR` (dans `.env`) permet de déplacer tous les venvs sans modifier le code.

---

## 🛠️ Execution & Diagnostics

### Starting the App
```bash
./start_workflow.sh
# OR manually:
/mnt/venv_ext4/env/bin/python app_new.py
```

### Running Specific Steps (Operator Mode)
*Refer to `.sixthskills/workflow-operator/resources/step_command_matrix.md` for the complete list.*

```bash
# Example: Run Step 3 (TransNet) - REQUIRES SPECIFIC ENV
/mnt/venv_ext4/transnet_env/bin/python workflow_scripts/step3/run_transnet.py --videos videos_to_track.json

# Example: Run Step 5 (MediaPipe CPU)
TRACKING_DISABLE_GPU=1 /mnt/venv_ext4/tracking_env_slim/bin/python workflow_scripts/step5/run_tracking_manager.py ...
```

### Health Checks
- **Env Validity**: `python - <<'PY' ...` (See `.sixthskills/pipeline-diagnostics/SKILL.md`)
- **Database**: `sqlite3 download_history.sqlite3 "PRAGMA integrity_check;"`

---

## 🛡️ Critical Implementation Rules (Non-Negotiable)

### 1. Multi-Environment Discipline (Strict)
This project uses **5 isolated Virtual Environments**. NEVER use the system python.
- **App/General**: `/mnt/venv_ext4/env/bin/python` (Step 1, 2, 6, 7, 8)
- **TransNet (Step 3)**: `/mnt/venv_ext4/transnet_env/bin/python` 
- **Audio (Step 4)**: `/mnt/venv_ext4/audio_env/bin/python` 
- **Tracking CPU (Step 5)**: `/mnt/venv_ext4/tracking_env_slim/bin/python` (MediaPipe)
- **Tracking GPU (Step 5)**: `/mnt/venv_ext4/insightface_env/bin/python` (InsightFace)

### 2. Backend Architecture
- **Service Layer**: Business logic lives in `services/`. Routes are thin wrappers.
- **State Truth**: `WorkflowState` is the single source of truth (thread-safe). Never parse log files to determine app state.
- **I/O Safety**: Use `FilesystemService` for all file operations. Never use `os.system` (use `subprocess` with full paths).

### 3. Frontend (Vanilla JS)
- **No Frameworks**: Pure ESM Modules.
- **DOM Batching**: All updates via `domBatcher.scheduleUpdate()`.
- **State**: `AppState` is immutable. Use `subscribeToProperty` for reactivity.
- **Composants actifs** : Timeline connectée (badges d'état dynamiques, auto-scroll structurel) et Logs Overlay (focus trap, sync timeline, fermeture auto). **Note** : Le panneau Step Details a été retiré le 2026-02-04 pour alléger l'interface.

# Pipeline STEP4, STEP5 & STEP7

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

---

## 📋 Documentation & Process

### Méthodologie Documentation
- Toute création ou modification de documentation **doit** appliquer la méthodologie définie dans `.sixthskills/documentation/SKILL.md` : TL;DR en premier, ouverture problem-first, blocs ❌/✅, trade-offs, Golden Rule.
- Git : Conventional Commits (`feat(step5): ...`, `fix(filesystem): ...`).
- Documentation : chaque changement majeur doit mettre à jour `docs/workflow/` (guide pipeline, audits, security notes).

### Politique d'utilisation des Skills
1. **Priorité locale absolue** : Toujours invoquer la skill workspace `workflow-operator` avant toute autre.
2. **Debugging systématique** : Charger `.sixthskills/debugging-strategies/SKILL.md` pour bug/crash.
3. **Catalogue local** : Utiliser `pipeline-diagnostics`, `step5-gpu-ops`, `frontend-timeline-designer`, `after-effects-scripts`, `after-effects-cep-panel`, `logs-overlay-conductor`, `workflow-docs-updater-plus`, `csv-monitoring-sme`, `debugging-strategies`, `step4-audio-orchestrator`, `tests-suite-guardian`, `workflow-operator`, `documentation` selon la tâche.
4. **Fallback contrôlé** : Skills globales uniquement si aucune skill locale ne couvre le besoin.
5. **Hiérarchie** : `workflow-operator` > Skills locales > Règles ce doc > Docs > Skills globales.

---

## ⚠️ Anti-Patterns Critiques

- Placer du métier dans un blueprint Flask ou manipuler `WorkflowState` sans verrou.
- Accéder au DOM avec `document.getElementById` dès l'import (utiliser getters lazy).
- Utiliser `innerHTML` sans `DOMUpdateUtils.escapeHtml`.
- Démarrer des polls via `setInterval` dispersé (utiliser `PollingManager`).
- Hardcoder des chemins (`/mnt/cache`) ou des commandes.
- Tenter d'activer le GPU sur MediaPipe (non supporté dans cette stack).

---

### Fichier `.env` (Obligatoire)

```bash
# Application Flask
FLASK_SECRET_KEY=votre-cle-secrete
DEBUG=false
HOST=0.0.0.0
PORT=5000

# Sécurité
INTERNAL_WORKER_COMMS_TOKEN=token-interne
RENDER_REGISTER_TOKEN=token-render

# Webhook (source unique de données)
WEBHOOK_JSON_URL=https://webhook.kidpixel.fr/webhook_proxy.php
WEBHOOK_TIMEOUT=10
WEBHOOK_CACHE_TTL=60

# Pipeline STEP5 (Tracking)
STEP5_TRACKING_ENGINE=insightface  # ou vide pour MediaPipe (défaut)
STEP5_ENABLE_GPU=1
TRACKING_CPU_WORKERS=15

# Pipeline STEP4 (Audio)
HF_AUTH_TOKEN=token-hugging-face
STEP4_USE_LEMONFOX=0  # 1 pour utiliser Lemonfox
LEMONFOX_API_KEY=cle-lemonfox

# Monitoring
ENABLE_GPU_MONITORING=true
SYSTEM_MONITOR_POLLING_INTERVAL=5000
```

### Configuration Centralisée

Toute la configuration passe par `config/settings.py` (classe `Config`):

```python
from config.settings import config

# Accès aux valeurs
python_exe = config.get_venv_python("env")
step_config = config.WORKFLOW_COMMANDS.get_step_config("STEP5")
```

---

## Sécurité

### Tokens d'Authentification

Deux tokens sont requis pour les endpoints sensibles :

1. **INTERNAL_WORKER_COMMS_TOKEN**: Pour les workers internes
2. **RENDER_REGISTER_TOKEN**: Pour l'enregistrement des renders

### Décorateurs de Protection

```python
from config.security import require_internal_worker_token, require_render_register_token

@api_bp.route('/sensitive-endpoint')
@require_internal_worker_token
def sensitive_endpoint():
    # Nécessite le header X-Worker-Token
    pass
```

### Validation des Entrées

- **Chemins de fichiers**: Validation via `validate_file_path()`
- **Clés d'étape**: Validation via `WorkflowCommandsConfig.validate_step_key()`
- **XSS**: Échappement systématique avec `DOMUpdateUtils.escapeHtml()`

---

## Stratégie de Tests

### Types de Tests

1. **Tests Unitaires** (`tests/unit/`): Services isolés avec mocks
2. **Tests d'Intégration** (`tests/integration/`): Workflows complets
3. **Tests Frontend** (`tests/frontend/`): Utilitaires ESM/Node

### Zones Critiques à Tester

| Composant | Priorité | Fichiers de test |
|-----------|----------|------------------|
| STEP5 Workers | Haute | `test_step5_*.py` |
| CSV Service | Haute | `test_csv_service*.py` |
| Workflow Service | Haute | `test_workflow_service.py` |
| Lemonfox Audio Service | Haute | `test_lemonfox_audio_service*.py` |

### Marqueurs Pytest

```python
# Tests nécessitant GPU
@pytest.mark.gpu
def test_step5_gpu_fallback():
    pass

# Tests d'intégration
@pytest.mark.integration
def test_workflow_full_pipeline():
    pass
```

---

## Déploiement et Exécution

### Script de Lancement Principal

```bash
./start_workflow.sh
```

Ce script :
1. Définit `VENV_BASE_DIR` depuis `.env` ou défaut
2. Configure les logs rotatifs (`logs/app.log`, `logs/startup.log`)
3. Lance Flask avec capture unifiée des logs
4. Ouvre le navigateur par défaut

### Logs

- **Log unifié**: `logs/app.log` (tous les logs Flask + stdout/stderr)
- **Log de démarrage**: `logs/startup.log` (événements de démarrage/arrêt)
- **Logs par étape**: `logs/step1/` à `logs/step8/`

### Arrêt Propre

```bash
Ctrl+C  # Déclenche cleanup_on_exit() dans start_workflow.sh
```

---

## Points d'Attention Importants

### 1. Environnements Virtuels

**Ne jamais** installer des dépendances directement dans les venvs sans mettre à jour les fichiers `requirements*.txt`.

### 2. État Thread-Safe

Toute modification de `WorkflowState` passe par les méthodes atomiques :

```python
state = get_workflow_state()
state.update_step_status('STEP5', 'running')  # Thread-safe
```

### 3. Gestion des Processus

Les étapes du pipeline s'exécutent dans des sous-processus. Ne jamais utiliser `shell=True` :

```python
# ✅ Correct
subprocess.Popen(cmd_list, cwd=working_dir)

# ❌ Dangereux
subprocess.Popen(command_string, shell=True)
```

### 4. Webhook-Only

Toutes les données externes arrivent via le webhook configuré (`WEBHOOK_JSON_URL`). Pas d'autres sources de données.

### 5. Fallback GPU/CPU

Le STEP5 a un fallback automatique CPU si GPU indisponible. Ne pas supprimer cette logique.

---

## Documentation Complémentaire

- `docs/workflow/README.md`: Vue d'ensemble
- `docs/workflow/core/architecture.md`: Architecture détaillée
- `docs/workflow/core/developer-guide.md`: Guide développeur
- `docs/workflow/ops/testing-strategy.md`: Stratégie de tests
- `docs/workflow/pipeline/`: Documentation de chaque étape (01 à 08)

---

## Contacts et Support

- **Documentation**: Voir le dossier `docs/`
- **Tests**: Voir `pytest.ini` et `tests/`
- **Configuration**: Voir `.env.example`

---

## Règle d'Or

> **Garde les services lourds, les routes légères, et l'état unique ; sinon tu crées des dépendances croisées.**

Respecte la hiérarchie : Pipeline → Services → Frontend. Ne crée pas d'angles morts en court-circuitant les couches.

---

## 💾 Memory Bank Protocol

1.  **Start**: Check `memory-bank/activeContext.md` and `productContext.md` (Pipeline Definitions).
2.  **During**: If you change a `.env` variable or a dependency, log it in `decisionLog.md`.
3.  **End**: Update `progress.md` with the specific steps debugged or features added.
