---
name: workflow-operator
description: Expert Opérateur certifié v4.1. Lance, monitore et débogue le pipeline MediaPipe en respectant strictement l'architecture Services/State et les environnements virtuels dédiés.
---

# Workflow MediaPipe Operator (v4.1 Standards Compliant)

Cette skill permet d'opérer le pipeline en respectant les règles définies dans `codingstandards.md`.

## 1. Architecture & Environnements

Le pipeline est segmenté. **Règle d'or :** Toujours utiliser l'interpréteur Python spécifique à l'étape. Ne jamais utiliser `python3` système.

| Étape | Dossier | Environnement (VENV) | Service Clé |
| :--- | :--- | :--- | :--- |
| **STEP 1** (Extract) | `step1/` | `env/` | `FilesystemService` |
| **STEP 2** (Convert) | `step2/` | `env/` | `ffmpeg` (via subprocess) |
| **STEP 3** (TransNet) | `step3/` | `transnet_env/` | `WorkflowService` |
| **STEP 4** (Audio) | `step4/` | `audio_env/` | `LemonfoxAudioService` |
| **STEP 5** (Tracking) | `step5/` | `tracking_env/` | `ObjectDetectorRegistry` |
| **STEP 6** (Reducer) | `step6/` | `env/` | N/A |
| **STEP 7** (Finalize) | `step7/` | `env/` | `ResultsArchiver` |

**Chemins des Venvs (interpréteurs montés sous `/mnt/venv_ext4`) :**
- Base : `env/bin/python`
- TransNet : `transnet_env/bin/python`
- Audio : `audio_env/bin/python`
- Tracking : `tracking_env/bin/python`

## 2. Commandes d'Exécution Manuelle (Standard v4.1)

Ces commandes doivent être lancées depuis la racine du projet **tout en ciblant les interpréteurs situés dans `/mnt/venv_ext4/<venv>/bin/python`** (pas le Python système).

> 🔎 **Raccourci** : consultez `resources/step_command_matrix.md` pour une vue tabulaire des 7 étapes (interpréteur, commande, logs, prérequis). Gardez le fichier ouvert pendant les interventions d'astreinte.

### Step 1 : Extraction Sécurisée
```bash
env/bin/python workflow_scripts/step1/extract_archives.py --source-dir "/chemin/vers/downloads"
```

### Step 2 : Conversion (Standard: 25fps)
```bash
env/bin/python workflow_scripts/step2/convert_videos.py
```

### Step 3 : Analyse Scènes (TransNetV2)
```bash
transnet_env/bin/python workflow_scripts/step3/run_transnet.py
```

### Step 4 : Analyse Audio (Standard: Lemonfox)
Le standard v4.1 privilégie Lemonfox avec fallback Pyannote. Le script détecte la config via `config/settings.py`.
```bash
audio_env/bin/python workflow_scripts/step4/run_audio_analysis_lemonfox.py --log_dir logs/step4
```

### Step 5 : Tracking (Standard: CPU Multiprocessing, GPU optionnel InsightFace)
**Standard CPU** : Mode CPU par défaut avec multiprocessing (15 workers) pour MediaPipe/YuNet/OpenSeeFace.
**GPU InsightFace** : Mode GPU requis exclusivement pour InsightFace (`STEP5_ENABLE_GPU=1`, `STEP5_GPU_ENGINES=insightface`).
**Process** : Warmup `cap.read()`, chunking adaptatif interne, JSON dense (`tracked_objects: []` si vide).

```bash
# Mode CPU standard (MediaPipe/YuNet/OpenSeeFace)
echo '["/chemin/absolu/vers/video.mp4"]' > temp_tracking.json
TRACKING_DISABLE_GPU=1 tracking_env/bin/python workflow_scripts/step5/run_tracking_manager.py \
  --videos_json_path temp_tracking.json \
  --cpu_internal_workers 15 \
  --disable_gpu

# Mode GPU InsightFace (uniquement si moteur InsightFace sélectionné)
echo '["/chemin/absolu/vers/video.mp4"]' > temp_tracking.json
STEP5_ENABLE_GPU=1 STEP5_GPU_ENGINES=insightface tracking_env/bin/python workflow_scripts/step5/run_tracking_manager.py \
  --videos_json_path temp_tracking.json \
  --tracking_engine insightface
```

### Step 6 : Réduction JSON
```bash
env/bin/python workflow_scripts/step6/json_reducer.py --log_dir logs/step6 --work_dir projets_extraits
```

### Step 7 : Finalisation (Avec Archivage)
```bash
# Vérifier OUTPUT_DIR dans .env avant
env/bin/python workflow_scripts/step7/finalize_and_copy.py
```

## 3. Diagnostic & État

### Source de Vérité (State)
L'état n'est pas dans les fichiers logs, mais dans la mémoire du backend via `WorkflowState`.
Pour diagnostiquer un état incohérent :
1. Interroger l'API : `curl http://localhost:5000/api/step_status/STEP5`
2. Vérifier si `is_any_sequence_running` est cohérent avec les logs.

### Logs & Monitoring
- **Performance** : Vérifier `/api/performance/metrics` (géré par `PerformanceService`).
- **Logs Fichiers** :
  - `logs/app.log` (Global Flask/Services)
  - `logs/stepX/*.log` (Workers spécifiques)

### Points de Vigilance (Coding Standards)
1. **I/O** : Vérifier que les chemins passent par `FilesystemService` (sécurité).
   - **Exemples d'usage** : 
     - Ouvrir un répertoire dans l'explorateur : `FilesystemService.open_path_in_explorer(path)` (sécurisé, vérif headless/prod).
     - Lire/écrire un fichier : utiliser les helpers de `FilesystemService` pour valider les permissions et verrous.
     - **Jamais** de manipulation directe du disque sans passer par ce service.
2. **Historique** : Si problème de téléchargement, vérifier `download_history.sqlite3` (pas le JSON déprécié).
3. **Tracking** : Si le tracking plante, vérifier que `config.settings.py` charge bien les modèles depuis le `ObjectDetectorRegistry` et non des chemins en dur.
4. **Scripts** : Les subprocess doivent utiliser `utils.resource_manager` pour la gestion des verrous et ressources.
5. **Tests** : Environnement de test `/mnt/venv_ext4/env` avec `DRY_RUN_DOWNLOADS=true` pour CI.

## 4. Frontend & UX Rappels (Standards §3)

Si vous intervenez sur l'interface ou devez valider un comportement UI :
- **DOM** : Les mises à jour doivent passer par `DOMBatcher.scheduleUpdate()`. Jamais d'insertion directe `innerHTML` sans échappement.
- **Sécurité** : Toujours échapper avec `DOMUpdateUtils.escapeHtml()` avant toute insertion dynamique (Anti-XSS).
- **Polling** : Utiliser le `PollingManager` centralisé (backoff adaptatif) pour les requêtes périodiques.
- **Composants** : 
  - Logs Overlay : focus trap, synchronisation Timeline, fermeture auto.
  - Step Details : `aside` contrôlé par `AppState`.
  - FromSmash : lecture seule, sanitisation, pas de DL automatique.
- **État** : `AppState` est la source unique (Timeline, Logs, Préférences). `setState` immutable.

## 5. Tests & Processus (Standards §5-6)

Pour toute action de validation, de débogage avancé ou de contribution :
- **Environnement de test** : Exécution depuis `/mnt/venv_ext4/env`.
- **DRY_RUN** : `DRY_RUN_DOWNLOADS=true` obligatoire en CI/Test (pas d'appels réseau).
- **Structure des tests** :
  - `tests/unit/` : Services isolés (Mocks `conftest.py` standardisés).
  - `tests/integration/` : Routes + `PerformanceService`.
  - `tests/frontend/` : Node/ESM pour DOMBatcher/Utils.
- **Mocking** : Privilégier `patched_workflow_state()` et `patched_commands_config()`.
- **Git** : Conventional Commits (`feat(step5): ...`).
- **Documentation** : Docstrings Google-style. Mettre à jour `docs/workflow/` lors de changements majeurs.