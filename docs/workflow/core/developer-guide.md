# Guide Développeur

**TL;DR** : Utilise les services centraux (`WorkflowService`, `WorkflowState`), respecte l'architecture thin controllers, et accède à l'état via `AppState` côté frontend. Zéro variables globales, tout passe par les services.

## L'Architecture en Bref

### Le Principe Fondamental

Tu construis sur une **architecture orientée services** où toute la logique métier vit dans `/services`. Les routes Flask sont des contrôleurs minces qui ne font que valider et déléguer.

### État Centralisé Obligatoire

Oublie les variables globales. Tout passe par `WorkflowState` :

### ✅ WorkflowState (pattern recommandé)
```python
# Approche v4.2 - thread-safe et centralisée
from services.workflow_state import get_workflow_state
ws = get_workflow_state()

# Étapes (atomiques et thread-safe)
ws.update_step_status("STEP5", "running")
ws.update_step_info("STEP5", progress_current=1, progress_total=6)
ws.set_step_field("STEP5", "progress_text", "video1.mp4")

# Séquences (avec RLock intégré)
ws.start_sequence("Full")
ws.complete_sequence(success=True, message="OK")
```

### ❌ Variables globales (anti-pattern)
```python
# Ancienne approche obsolète
PROCESS_INFO = {}
PROCESS_INFO_LOCK = threading.Lock()

def update_step_status(step_key, status):
    with PROCESS_INFO_LOCK:
        PROCESS_INFO[step_key] = status  # Non thread-safe !
```

### Environnements Relocalisables

`VENV_BASE_DIR` te permet de déplacer tous les environnements virtuels :

```python
from config.settings import config
python_env = config.get_venv_python("tracking_env_slim")
subprocess.run([python_env, "workflow_scripts/step5/run_tracking_manager.py"])
```

> **Pourquoi `tracking_env_slim` ?** Depuis la décision du 2026‑02‑03, l'environnement `tracking_env` a été officiellement remplacé par `tracking_env_slim` pour MediaPipe CPU. InsightFace GPU reste dans `insightface_env`. Voir `decisionLog.md` pour l'historique complet.

Aucun chemin `env/bin/python` en dur dans le code.

## Services Centraux - Tes Points d'Entrée

### WorkflowService - Le Chef d'Orchestre

```python
from services.workflow_service import WorkflowService

# Exécution
WorkflowService.run_step("STEP1")  # Lance une étape
WorkflowService.run_custom_sequence(["STEP1", "STEP2"])  # Séquence personnalisée
WorkflowService.stop_sequence()  # Arrêt d'urgence

# État
status = WorkflowService.get_step_status("STEP1")
sequence_status = WorkflowService.get_sequence_status()
log_file = WorkflowService.get_step_log_file("STEP1", 0)
```

**Pattern à suivre** : Toute route appelle `WorkflowService`, jamais directement les scripts.

### MonitoringService - Surveillance Système

```python
from services.monitoring_service import MonitoringService

# Métriques système
system_status = MonitoringService.get_system_status()
gpu_usage = MonitoringService.get_gpu_usage()
cpu_usage = MonitoringService.get_cpu_usage()
memory_info = MonitoringService.get_memory_usage()
```

### CacheService - Cache Intelligent

```python
from services.cache_service import CacheService

# Cache avec TTL
CacheService.set("key", data, ttl=300)
cached_data = CacheService.get("key")

# Cache frontend
cache_stats = CacheService.get_cache_stats()
```

### CSVService - Monitoring Webhook

```python
from services.csv_service import CSVService

# Source unique : webhook JSON
monitor_status = CSVService.get_monitor_status()
download_history = CSVService.get_download_history()
is_downloaded = CSVService.is_url_downloaded(url)

# Normalisation URLs (automatique)
normalized = CSVService._normalize_url(dropbox_url)
```

### LemonfoxAudioService - Alternative Audio

```python
from services.lemonfox_audio_service import LemonfoxAudioService

result = LemonfoxAudioService.process_video_with_lemonfox(
    project_name="mon_projet",
    video_name="videos/ma_video.mp4",
    language="fr",
    speaker_labels=True,
    min_speakers=1,
    max_speakers=4
)

if result.success:
    print(f"Fichier généré: {result.output_path}")
```

## Frontend - État Centralisé et Performance

### AppState - État Immutable

```javascript
import { appState } from './state/AppState.js';

// Lecture
const { activeStepKeyForLogsPanel, stepTimers } = appState.getState();

// Mise à jour (immutabilité garantie)
appState.setState({
    stepTimers: {
        ...stepTimers,
        STEP3: { startTime: Date.now(), elapsedMs: 0 }
    }
}, 'step_timer_start');

// Abonnement ciblé
const unsubscribe = appState.subscribe((next, prev) => {
    if (next.activeStepKeyForLogsPanel !== prev.activeStepKeyForLogsPanel) {
        updateLogsPanel(next.activeStepKeyForLogsPanel);
    }
});
```

### ❌ DOM direct (anti-pattern)
```javascript
// Ancienne approche - risques XSS et performance
function updateLog(content) {
    const element = document.getElementById('log-content');
    element.innerHTML = content;  // XSS danger !
    // Pas de batching = reflows multiples
}
```

### ✅ DOMBatcher + AppState (pattern recommandé)
```javascript
// Approche v4.2 - sécurisée et performante
import { domBatcher } from './utils/DOMBatcher.js';
import { DOMUpdateUtils } from './utils/DOMUpdateUtils.js';
import { appState } from './state/AppState.js';

// Mises à jour groupées et sécurisées
domBatcher.scheduleUpdate(() => {
    const element = document.getElementById('log-content');
    if (element) {
        element.textContent = DOMUpdateUtils.escapeHtml(logContent);
    }
});

// État immutable garantissant la cohérence
appState.setState({ activeStepKeyForLogsPanel: 'STEP5' }, 'logs_panel_open');
```

**Règle XSS** : Tout contenu dynamique doit passer par `DOMUpdateUtils.escapeHtml()`.

## Patterns de Développement Obligatoires

### Thin Controllers + Service Layer

**Principe** : Les routes ne font que valider et déléguer.

```python
# ❌ Ancienne approche (obsolète)
@api_bp.route('/api/get_specific_log/<step_key>/<log_index>')
def get_specific_log(step_key, log_index):
    config = COMMANDS_CONFIG[step_key.upper()]
    log_file = os.path.join(config['log_dir'], f"specific_log_{log_index}.txt")
    return {"file_path": log_file}

# ✅ Nouvelle approche (v4.2)
@api_bp.route('/api/get_specific_log/<step_key>/<log_index>')
@measure_api('/api/get_specific_log/<step_key>/<log_index>')
def get_specific_log(step_key, log_index):
    return WorkflowService.get_step_log_file(step_key, int(log_index))
```

### Performance + Sécurité

**Principe** : Optimise sans compromettre la sécurité XSS.

```javascript
function parseAndStyleLogContent(content) {
    // 1. Échappement XSS OBLIGATOIRE
    const escapedContent = DOMUpdateUtils.escapeHtml(content);
    
    // 2. Optimisations (regex pré-compilées)
    const patterns = {
        error: /\[ERROR\]|\[ERREUR\]/gi,
        warning: /\[WARNING\]|\[AVERTISSEMENT\]/gi,
        progress: /\[Progression\]/gi
    };
    
    // 3. Traitement linéaire
    return escapedContent
        .replace(/\n/g, '<br>')
        .replace(patterns.error, '<span class="log-error">$&</span>')
        .replace(patterns.warning, '<span class="log-warning">$&</span>')
        .trim();
}
```

### Configuration Centralisée

```python
# ❌ Ancienne approche
from config.workflow_commands import COMMANDS_CONFIG
command = COMMANDS_CONFIG["STEP5"]["command"]

# ✅ Nouvelle approche
from config.workflow_commands import WorkflowCommandsConfig
config = WorkflowCommandsConfig()
command = config.get_step_command("STEP5")
cwd = config.get_step_cwd("STEP5")
```

## API Endpoints Essentiels

### Diagnostics Système

```bash
GET /api/system/diagnostics
```

**Réponse** :
```json
{
  "python": {"version": "3.10.12", "implementation": "CPython"},
  "ffmpeg": {"version": "4.4.0"},
  "gpu": {"available": true, "name": "NVIDIA GTX 1650"},
  "config_flags": {
    "ENABLE_GPU_MONITORING": true,
    "DRY_RUN_DOWNLOADS": false,
    "FLASK_DEBUG": false
  },
  "timestamp": "2025-11-18T16:45:00+01:00"
}
```

## STEP5 - Tracking Spécifique

### Moteurs Supportés

```bash
# MediaPipe (défaut, CPU)
STEP5_TRACKING_ENGINE=          # vide = MediaPipe
TRACKING_CPU_WORKERS=15

# InsightFace (GPU optionnel)
STEP5_ENABLE_GPU=1
STEP5_TRACKING_ENGINE=insightface
STEP5_GPU_ENGINES=insightface
STEP5_GPU_MAX_VRAM_MB=2048
```

### Variables Clés

```bash
# Optimisations
STEP5_MEDIAPIPE_MAX_FACES=4
STEP5_MEDIAPIPE_JAWOPEN_SCALE=1.0
STEP5_MEDIAPIPE_MAX_WIDTH=960

# Object detection (optionnel)
STEP5_ENABLE_OBJECT_DETECTION=0
STEP5_OBJECT_DETECTOR_MODEL=efficientdet_lite2

# Profiling
STEP5_ENABLE_PROFILING=0
```

### Fallback GPU

```bash
STEP5_GPU_FALLBACK_AUTO=1  # Bascule CPU auto si GPU échoue
```

## Composants Frontend Supprimés

Ne plus utiliser ces fonctions (retirées le 2026-01-18) :

```javascript
// ❌ Supprimés - ne plus utiliser
- initializeStep5AdvancedControls()
- setStep5ChunkBoundsAPI()
- showDiagnosticsModal()
- showStatisticsModal()
- initializeSmartUpload()
```

**Alternatives** :
- Diagnostics : `GET /api/system/diagnostics`
- Chunking : valeurs par défaut automatiques
- Mode compact : maintenu sans fonctionnalités avancées

## Trade-offs par Moteur STEP5

| Moteur STEP5 | Avantages | Risques | Environnement Requis |
|--------------|-----------|---------|----------------------|
| **MediaPipe (CPU)** | Stable, pas de GPU requis, 478 landmarks | Plus lent sur vidéos longues | `tracking_env_slim` (Python 3.10) |
| **InsightFace (GPU)** | 5-10× plus rapide, précision supérieure | Nécessite GPU NVIDIA, VRAM limitée | `insightface_env` (CUDA 11.x) |
| **Hybrid** | Flexibilité maximale, fallback auto | Complexité configuration | Les deux + validation GPU |

## Trade-offs par Profile de Test

| Profile | Temps d'exécution | Risques couverts | Quand l'utiliser |
|---------|------------------|------------------|-----------------|
| **Unit tests only** | 2-5 min | Logique métier pure | Pull request, validation rapide |
| **Integration tests** | 10-15 min | Routes + services complets | Pre-release, staging |
| **Frontend tests** | 1-2 min | Sécurité XSS, performance | Changements UI/UX |
| **Full suite** | 20-30 min | Pipeline complet | Release candidate |

## Analogie : Tour de Contrôle

Pense au développement comme une **tour de contrôle aérienne**. **WorkflowState** est le radar principal qui voit tous les avions (étapes). **AppState** est l'écran des contrôleurs avec les vols prioritaires. **DOMBatcher** est le système de communication qui coordonne les messages sans brouillage (reflows). Les **tests** sont les simulations d'urgence qui vérifient que même si un moteur (STEP5) tombe en panne, les autres continuent de fonctionner.

## Tests et Validation

### Tests Frontend

```bash
npm run test:frontend
npm run test:dom-batcher      # Performance batching
npm run test:focus-trap      # A11y focus management
npm run test:xss-safety      # Sécurité XSS
npm run test:step-details    # Timeline Connectée
```

### Tests Backend

```bash
# Activer DRY_RUN pour éviter les téléchargements réels
DRY_RUN_DOWNLOADS=true pytest

# Validation configuration
python -c "from config.settings import config; config.validate(); print('Config OK')"
```

## Pièges Courants et Solutions

### Piège #1 : Logique métier dans les routes
**Solution** : Délègue tout à `WorkflowService`. Les routes ne font que valider et formater.

### Piège #2 : Variables globales pour l'état
**Solution** : Utilise uniquement `WorkflowState`. C'est thread-safe et centralisé.

### Piège #3 : Paths en dur dans les commandes
**Solution** : Utilise `config.get_venv_python()` et `WorkflowCommandsConfig`.

### Piège #4 : Oublier l'échappement XSS
**Solution** : Tout contenu dynamique passe par `DOMUpdateUtils.escapeHtml()`.

### Piège #5 : Polling non géré
**Solution** : Utilise `PollingManager` pour tout polling (nettoyage automatique).

## Sécurité et Performance

### Instrumentation API

Tous les endpoints doivent être décorés :

```python
@api_bp.route('/api/mon_endpoint')
@measure_api('/api/mon_endpoint')
def mon_endpoint():
    return WorkflowService.some_method()
```

### Tokens de Sécurité

```bash
# Obligatoires dans .env
FLASK_SECRET_KEY=your-secret
INTERNAL_WORKER_COMMS_TOKEN=your-worker-token
RENDER_REGISTER_TOKEN=your-render-token
```

### Cache Performance

```javascript
// Cache-busting CSS/JS
const cacheBuster = _CACHE_BUSTER;  // Généré automatiquement
```

## Références Utiles

- Architecture complète : `docs/workflow/core/architecture.md`
- Démarrage rapide : `docs/workflow/core/quickstart.md`
- Tests strategy : `docs/workflow/ops/testing-strategy.md`
- API instrumentation : `docs/workflow/ops/api-routes.md`

En suivant ces patterns, tu maintiendras une architecture propre, testable et performante. Le système est conçu pour évoluer sans dette technique.

---

## Golden Rule

**Injecte, mesure, jamais coder dans les routes ; sinon tu crées des dépendances non testables.**
