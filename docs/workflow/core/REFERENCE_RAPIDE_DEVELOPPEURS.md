### Addendum v4.1 — Points MANDATORY ✅ **AUDIT COMPLET**

- **Instrumentation API**: ✅ Implémenté - Tous les endpoints Flask décorés via `measure_api()`
- **A11y Modales**: ✅ **AUDIT COMPLET** - Focus trap + restauration sur toutes les modales (statsViewer, reportViewer, diagnostics)
- **XSS Frontend**: ✅ **AUDIT COMPLET** - Échappement systématique via `DOMUpdateUtils.escapeHtml()`, zéro injection XSS P0
- **Polling**: ✅ Implémenté - `PollingManager` avec backoff adaptatif
- **Tests/CI**: Activer `DRY_RUN_DOWNLOADS=true` pour empêcher tout téléchargement réel durant les tests d’intégration/CI.
# Référence Rapide pour Développeurs - Workflow MediaPipe v4.2

## Architecture en un Coup d'Œil

### Principe Fondamental
**Service-Oriented Architecture** : Toute logique métier dans les services, routes comme contrôleurs légers.

### Virtualenvs relocalisables (`VENV_BASE_DIR`) — Nouveau (2025-12-20)

- `VENV_BASE_DIR` définit la racine **unique** de tous les environnements (`env`, `tracking_env`, `audio_env`, `transnet_env`, `eos_env`).  
- **Ordre de résolution** : valeur déjà exportée dans l'environnement > entrée `.env` > dossier du projet (fallback).  
- `start_workflow.sh` lit automatiquement la valeur, la nettoie (guillemets) puis exporte `PYTHON_VENV_EXE_ENV` attendu par `app_new.py`.  
- Utiliser exclusivement les helpers `Config.get_venv_path()` / `Config.get_venv_python()` pour construire les commandes (cf. `WorkflowCommandsConfig`). Aucun chemin `env/bin/python` ne doit être hardcodé.

```python
from config.settings import config

python_env = config.get_venv_python("tracking_env")
subprocess.run([python_env, "workflow_scripts/step5/run_tracking_manager.py"])
```

> **Impact** : On peut déplacer l'ensemble des virtualenvs sur un SSD ou un dossier partagé (`/mnt/cache/venv/workflow_mediapipe`) sans modifier le code ni les scripts.

### État centralisé (WorkflowState) — Obligatoire

Les services et routes doivent interagir avec l'état via `WorkflowState` uniquement.

API minimale disponible (extraits):

```python
from services.workflow_state import get_workflow_state
ws = get_workflow_state()

# Étapes
ws.initialize_all_steps(["STEP1", "STEP2", ...])
ws.update_step_status("STEP5", "running")
ws.update_step_info("STEP5", progress_current=1, progress_total=6)
ws.set_step_field("STEP5", "progress_text", "video1.mp4")
info = ws.get_step_info("STEP5")

# Séquences
ws.start_sequence("Full")
running = ws.is_sequence_running()
ws.complete_sequence(success=True, message="OK", sequence_type="Full")
outcome = ws.get_sequence_outcome()

# Accès performances (boucles):
log_deque = ws.get_step_log_deque("STEP5")  # Attention: référence directe (performance)
```

### Anciennes variables globales (ne plus utiliser) :
- ❌ `PROCESS_INFO`, `PROCESS_INFO_LOCK`
- ❌ `sequence_lock`, `is_currently_running_any_sequence`, `LAST_SEQUENCE_OUTCOME`

**Statut actuel** : La migration vers `WorkflowState` est terminée. Tous les composants utilisent désormais `WorkflowState` comme source unique de vérité pour l'état du workflow.

### Services Centraux

#### WorkflowService (services/workflow_service.py)
```python
# Exécution des étapes et séquences
WorkflowService.run_step("STEP1")  # Exécute une étape spécifique
WorkflowService.run_custom_sequence(["STEP1", "STEP2"])  # Exécute une séquence personnalisée
WorkflowService.stop_sequence()  # Arrête la séquence en cours

# Récupération d'état
WorkflowService.get_step_status("STEP1")  # Statut d'une étape
WorkflowService.get_sequence_status()     # Statut de la séquence en cours
```

#### Monitoring & Cache
```python
# services/monitoring_service.py - Surveillance système  
MonitoringService.get_system_status()  # État global du système
MonitoringService.get_gpu_usage()      # Utilisation GPU

# services/cache_service.py - Cache intelligent
CacheService.set("key", data, ttl=300)  # Mise en cache avec expiration
CacheService.get("key")                 # Récupération depuis le cache

# Cache front / statiques (v4.1+)
# _STATIC_CACHE_BUSTER est un timestamp généré au démarrage du serveur
# pour forcer le rechargement des assets CSS/JS après un redémarrage.
# Voir routes/workflow_routes.py et templates/index_new.html
_CACHE_BUSTER = str(int(time.time()))  # Généré automatiquement
```

# services/performance_service.py - Métriques
PerformanceService.track_api_call("/api/system_monitor", 150)

# services/csv_service.py - Monitoring téléchargements (Webhook)
CSVService.get_monitor_status()  # Statut du monitoring
CSVService.get_download_history()  # Historique des téléchargements

# Normalisation avancée des URLs
normalized_url = CSVService._normalize_url("https://www.dropbox.com/s/abc123/video.mp4?dl=0&amp;dl=1")
# Retourne: "https://www.dropbox.com/s/abc123/video.mp4?dl=1"

# services/webhook_service.py - Source JSON externe (source unique)
from services.webhook_service import fetch_records, get_service_status
webhook_records = fetch_records()
webhook_status = get_service_status()

# services/lemonfox_audio_service.py - Analyse audio alternative (v4.1)
from services.lemonfox_audio_service import LemonfoxAudioService

# Traitement vidéo avec Lemonfox
result = LemonfoxAudioService.process_video_with_lemonfox(
    project_name="mon_projet",
    video_name="videos/ma_video.mp4",
    language="fr",
    speaker_labels=True,
    min_speakers=1,
    max_speakers=4
)

# Vérification du résultat
if result.success:
    print(f"Fichier généré: {result.output_path}")
    print(f"FPS: {result.fps}, Frames: {result.total_frames}")
else:
    print(f"Erreur: {result.error}")

# Configuration via variables d'environnement
# STEP4_USE_LEMONFOX=1 pour activer
# LEMONFOX_API_KEY obligatoire si activé
```

**Note sur les sources de données** :
- Le système utilise exclusivement le Webhook configuré via `WEBHOOK_JSON_URL`
- Les variables obsolètes suivantes ne sont plus utilisées :
  - `USE_MYSQL`, `USE_AIRTABLE`, `USE_WEBHOOK`
  - `CSV_MONITOR_URL`, `CSV_MONITOR_INTERVAL`

**Note sur Lemonfox** :
- Alternative à Pyannote.audio pour l'analyse audio
- Fallback automatique vers Pyannote en cas d'échec
- Configuration via variables `LEMONFOX_*` dans `.env`
- Nécessite une connexion internet et une clé API Lemonfox

### Frontend - Components Removed (2026-01-18)

Les composants suivants ont été supprimés pour simplifier l'interface :

```javascript
// Supprimés - ne plus utiliser
- initializeStep5AdvancedControls()  // Configuration dynamique des chunks
- setStep5ChunkBoundsAPI()           // API endpoint /api/step5/chunk_bounds
- showDiagnosticsModal()             // Bouton Diagnostics retiré
- showStatisticsModal()              // Bouton Statistiques retiré
- initializeSmartUpload()             // Smart Upload avancé retiré
```

**Impact** :
- Le chunking adaptatif fonctionne avec des valeurs par défaut
- Les diagnostics sont accessibles via `/api/system/diagnostics` uniquement
- Le mode compact unifié est maintenu sans les fonctionnalités avancées

### Frontend État Centralisé
```javascript
// static/state/AppState.js
import { appState } from './state/AppState.js';

// Lecture
const status = appState.getState().stepStatuses;

// Modification (immutable)
appState.setState({ stepStatuses: newStatus });

// Abonnement
appState.subscribe('stepStatuses', callback);
```

### Références complémentaires
- Smart Upload (feature retirée le 18 janvier 2026 — historique dans `memory-bank/decisionLog.md` et archives `docs/workflow/legacy/SMART_UPLOAD_FEATURE.md`)
- Monitoring Système & Instrumentation API → [SYSTEM_MONITORING_ENHANCEMENTS.md](SYSTEM_MONITORING_ENHANCEMENTS.md)
- Stratégie de tests (pytest + ESM/Node) → [TESTING_STRATEGY.md](TESTING_STRATEGY.md)
- Diagnostics Système (modale + API) → [DIAGNOSTICS_FEATURE.md](DIAGNOSTICS_FEATURE.md)
- Instrumentation des API (measure_api + PerformanceService) → [API_INSTRUMENTATION.md](API_INSTRUMENTATION.md)

## API Endpoints

### /api/system/diagnostics

**Méthode** : GET

**Description** : Fournit des informations de diagnostics système pour le dépannage, incluant versions logicielles, disponibilité GPU et flags de configuration filtrés.

**Paramètres** : Aucun

**Réponse** (200) :
```json
{
  "python": {
    "version": "string",
    "implementation": "string"
  },
  "ffmpeg": {
    "version": "string"
  },
  "gpu": {
    "available": boolean,
    "name": "string|null"
  },
  "config_flags": {
    "ENABLE_GPU_MONITORING": boolean,
    "DRY_RUN_DOWNLOADS": boolean,
    "FLASK_DEBUG": boolean
  },
  "timestamp": "string (ISO 8601)"
}
```

**Erreurs** :
- 500 : Erreur interne du serveur

**Instrumentation** : Oui, via `measure_api()` dans `routes/api_routes.py`.

**Service Backend** : `MonitoringService.get_environment_info()` dans `services/monitoring_service.py`.

### /api/visualization/projects

**Méthode** : GET

**Description** : Liste tous les projets disponibles avec indication de la provenance des données (projet actif ou archives).

**Paramètres** : Aucun

**Réponse (200)** :
```json
{
  "projects": [
    {
      "name": "projet_camille_001",
      "path": "/path/to/projets_extraits/projet_camille_001",
      "videos": ["video1.mp4", "video2.mov"],
      "has_scenes": true,
      "has_audio": true,
      "has_tracking": true,
      "video_count": 2,
      "source": "projects", 
      "display_base": "projet_camille_001",
      "archive_timestamp": "2025-10-06 16:20:15"
    }
  ],
  "count": 1,
  "timestamp": "2025-11-18T16:45:00+01:00"
}
```

**Instrumentation** : Oui, via `measure_api()`.

**Service Backend** : `VisualizationService.get_available_projects()`.

**Note (Step5 — tracking)** :
- La détection ignore les fichiers `*_audio.json` et considère une vidéo comme « déjà traitée » uniquement si un JSON sibling de même nom de base existe (ex: `video.mp4` ↔ `video.json`). Voir `app_new.py::_find_videos_for_tracking()`.
- Les workers multiprocessing chargent automatiquement le `.env` et propagent les limites `STEP5_OPENCV_MAX_FACES`, `STEP5_MEDIAPIPE_MAX_FACES`, `STEP5_*_JAWOPEN_SCALE`, `STEP5_MEDIAPIPE_MAX_WIDTH`, `STEP5_YUNET_MAX_WIDTH` ainsi que la hiérarchie des modèles STEP5 (`workflow_scripts/step5/models/`). Renseigner ces variables dans `.env` est recommandé pour éviter la saturation CPU ou des incohérences d’analyse.
- Le fallback object detection MediaPipe s’appuie sur `workflow_scripts/step5/object_detector_registry.py`. Les variables à déclarer : `STEP5_ENABLE_OBJECT_DETECTION`, `STEP5_OBJECT_DETECTOR_MODEL` (parmi `efficientdet_lite0/1/2`, `ssd_mobilenet_v3`, `yolo11n_onnx`, `nanodet_plus`) et, optionnellement, `STEP5_OBJECT_DETECTOR_MODEL_PATH`. La résolution suit `override_path` > env > `workflow_scripts/step5/models/object_detectors/<backend>/`. Voir `STEP5_SUIVI_VIDEO.md` pour la table détaillée.
  - Les moteurs supportés sont MediaPipe (défaut), OpenCV Haar/YuNet (+ PyFeat), OpenSeeFace et EOS. `create_face_engine()` lève une erreur si `STEP5_TRACKING_ENGINE` reçoit une valeur non listée.
  - Chaque moteur dispose de ses variables dédiées (`STEP5_YUNET_MODEL_PATH`, `STEP5_OPENSEEFACE_MODELS_DIR`, `STEP5_EOS_*`, etc.). Vérifiez qu’elles sont définies avant d’exécuter `run_tracking_manager.py` pour éviter les échecs de chargement.
  - Les interpréteurs sont récupérés via `config.get_venv_python()` ; `start_workflow.sh` exporte `VENV_BASE_DIR` (env > `.env` > dossier projet) et `PYTHON_VENV_EXE_ENV` pour garantir la cohérence, y compris lorsque les venvs résident sur un SSD externe.
  - Pour `STEP5_TRACKING_ENGINE=eos`, le gestionnaire route automatiquement vers `eos_env` (override possible via `STEP5_EOS_ENV_PYTHON`). Les autres moteurs restent sur `tracking_env`.
  - `TRACKING_CPU_WORKERS` vaut 15 par défaut (défini dans `app_new.py`), et est propagé jusqu’aux workers via `--mp_num_workers_internal`. Même quand InsightFace tourne sur GPU, cette valeur est réutilisée pour dimensionner le pool de fallback object detection (MediaPipe Tasks en `RunningMode.IMAGE`).
  - `TRACKING_DISABLE_GPU=1` reste le comportement par défaut pour garantir la stabilité v4.1 ; depuis la décision du 27/12/2025, seul InsightFace peut activer le GPU si `STEP5_ENABLE_GPU=1` et `STEP5_GPU_ENGINES` contient `insightface`. MediaPipe, OpenSeeFace, OpenCV YuNet/PyFeat et EOS sont exécutés exclusivement en mode CPU.
  - `STEP5_GPU_FALLBACK_AUTO=1` autorise la bascule automatique en mode CPU lorsque `Config.check_gpu_availability()` échoue (VRAM insuffisante, providers CUDA manquants). Mettre `0` pour forcer un arrêt immédiat.
  - `STEP5_EOS_ENV_PYTHON` permet de relocaliser l’environnement InsightFace GPU-only lorsque `VENV_BASE_DIR` pointe hors du repo. `STEP5_TF_GPU_ENV_PYTHON` a été retiré : MediaPipe/OpenSeeFace ne supportent plus le GPU.
  - Les logs `[Progression]|…`, `[Progression-MultiLine] …` et `[Gestionnaire] Succès/Échec …` sont contractuels avec `app_new.py`/`WorkflowState`. Ne modifiez pas leur format sans mettre à jour le parsing.

### Timeline Connectée - Pipeline Manager (v4.2)

#### Méthodes principales
```javascript
// Gestion des détails contextuels
pipelineTimelineManager.showStepDetails(stepKey)
pipelineTimelineManager.hideStepDetails()
pipelineTimelineManager.toggleStepDetails(stepKey)

// Gestion des séquences personnalisées
pipelineTimelineManager.attachCustomSequenceListeners()
pipelineTimelineManager.handleCustomSequenceChange(event)
pipelineTimelineManager.updateCustomSequenceButtons()
pipelineTimelineManager.runCustomSequence()
pipelineTimelineManager.clearCustomSequence()

// Synchronisation AppState
pipelineTimelineManager.syncWithAppState()
pipelineTimelineManager.refreshStepStatus(stepKey)
```

#### Tests associés
- `tests/frontend/test_step_details_panel.mjs` : Tests Given/When/Then du panneau de détails
- `tests/frontend/test_custom_sequence_timeline.mjs` : Tests des séquences personnalisées
- `npm run test:frontend` : Suite complète incluant Timeline Connectée

---

## Patterns de Développement v4.2

### Thin Controllers + Service Layer (MANDATORY)

**Principe** : Les routes Flask doivent être des contrôleurs légers qui délèguent toute logique métier aux services.

```python
# ❌ Ancienne approche (obsolète)
@api_bp.route('/api/get_specific_log/<step_key>/<log_index>')
def get_specific_log(step_key, log_index):
    # Logique métier directement dans la route
    config = COMMANDS_CONFIG[step_key.upper()]
    log_file = os.path.join(config['log_dir'], f"specific_log_{log_index}.txt")
    return {"file_path": log_file}

# ✅ Nouvelle approche (v4.2)
@api_bp.route('/api/get_specific_log/<step_key>/<log_index>')
@measure_api('/api/get_specific_log/<step_key>/<log_index>')
def get_specific_log(step_key, log_index):
    return WorkflowService.get_step_log_file(step_key, int(log_index))
```

**Bénéfices** :
- Testabilité unitaire des services
- Réutilisation de la logique métier
- Séparation claire des responsabilités
- Instrumentation centralisée

### Performance with Security Pattern

**Principe** : Optimiser les performances sans compromettre la sécurité XSS.

```javascript
// ✅ Approche optimisée ET sécurisée
function parseAndStyleLogContent(content) {
    // 1. Échappement XSS OBLIGATOIRE en premier
    const escapedContent = DOMUpdateUtils.escapeHtml(content);
    
    // 2. Optimisations de performance (regex pré-compilées)
    const patterns = {
        error: /\[ERROR\]|\[ERREUR\]/gi,
        warning: /\[WARNING\]|\[AVERTISSEMENT\]/gi,
        progress: /\[Progression\]/gi
    };
    
    // 3. Traitement linéaire optimisé
    return escapedContent
        .replace(/\n/g, '<br>')
        .replace(patterns.error, '<span class="log-error">$&</span>')
        .replace(patterns.warning, '<span class="log-warning">$&</span>')
        .trim();
}

// Export pour tests Node
export { parseAndStyleLogContent };
```

### Gestion Centralisée des Erreurs

**Principe** : Utiliser `WorkflowService` comme point d'entrée unique pour la gestion des erreurs et l'état.

```python
# ✅ Pattern centralisé
try:
    result = WorkflowService.run_step(step_key)
    if result["status"] == "failed":
        # Gestion centralisée via WorkflowState
        ws = get_workflow_state()
        ws.set_step_field(step_key, "error_details", result.get("message"))
except Exception as e:
    # Logging structuré et état cohérent
    logger.error(f"Step {step_key} failed: {e}")
    WorkflowService.handle_step_failure(step_key, e)
```

### Configuration Centralisée (WorkflowCommandsConfig)

**Principe** : Toute configuration des commandes via `WorkflowCommandsConfig` (plus de globals).

```python
# ❌ Ancienne approche (obsolète)
from config.workflow_commands import COMMANDS_CONFIG
command = COMMANDS_CONFIG["STEP5"]["command"]

# ✅ Nouvelle approche (v4.2)
from config.workflow_commands import WorkflowCommandsConfig
config = WorkflowCommandsConfig()
command = config.get_step_command("STEP5")
cwd = config.get_step_cwd("STEP5")
```
