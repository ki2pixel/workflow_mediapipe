# Dataset Strategy for Mistral Fine-Tuning

**TL;DR**: Un dataset de 100 exemples techniques ciblés (40% architecture, 35% opérations, 15% After Effects, 10% best practices) surpasse un modèle générique pour les questions spécifiques au pipeline.

Vous essayez d'utiliser ChatGPT ou Claude pour obtenir de l'aide sur votre pipeline workflow_mediapipe, mais ils vous donnent des commandes Python incorrectes et ne comprennent pas vos 5 environnements virtuels isolés. C'est le "Generic Model Gap" - des modèles qui connaissent Python mais pas votre architecture.

## 🎯 Objectif du Dataset

Créer un ensemble de données qui transforme Mistral en un véritable expert du pipeline :

### Distribution Cible (100 exemples)

| Catégorie | Pourcentage | Nombre | Focus Principal |
|-----------|-------------|--------|----------------|
| **Architecture knowledge** | 40% | ~40 | Services, patterns, environnements, frontend |
| **Pipeline operations** | 35% | ~35 | Commandes STEP1-STEP8, erreurs, optimisations |
| **After Effects integration** | 15% | ~15 | ExtendScript, ponts Python↔AE, workflows |
| **Best practices/security** | 10% | ~10 | Sécurité, tests, déploiement, monitoring |

## 📊 Structure des Données

### Format JSONL (Mistral Chat Completions)

```json
{
  "messages": [
    {
      "role": "system",
      "content": "Tu es un expert senior du pipeline workflow_mediapipe..."
    },
    {
      "role": "user", 
      "content": "Comment exécuter STEP5 avec MediaPipe CPU ?"
    },
    {
      "role": "assistant",
      "content": "Pour STEP5 MediaPipe CPU, utilisez l'environnement tracking_env_slim...\n\nCommande exacte :\n/mnt/venv_ext4/tracking_env_slim/bin/python workflow_scripts/step5/run_tracking_manager.py --videos videos_to_track.json --engine mediapipe\n\nVariables importantes :\n- TRACKING_DISABLE_GPU=1 (force CPU)\n- TRACKING_CPU_WORKERS=4 (multiprocessing obligatoire)\n\n..."
    }
  ]
}
```

## 🏗️ Architecture Knowledge Examples

### Patterns Essentiels

**Service Layer Pattern**
```python
# ❌ Mauvais : Logique métier dans la route Flask
@api_blueprint.post("/api/step/<step_key>/run")
def run_step(step_key: str):
    # Logique métier ici (interdit)
    workflow_service.run_step(step_key)
    return jsonify({"status": "queued"})

# ✅ Bon : Route mince, service injecté
class WorkflowService:
    def __init__(self, filesystem: FilesystemService, state: WorkflowState):
        self._fs = filesystem
        self._state = state
    
    def run_step(self, step_key: str) -> None:
        with self._state.step_context(step_key):
            # Logique métier pure
```

**Multi-Environment Discipline**
```bash
# ❌ Mauvais : Utiliser system Python
python workflow_scripts/step5/run_tracking_manager.py

# ✅ Bon : Environnement spécifique
/mnt/venv_ext4/tracking_env_slim/bin/python workflow_scripts/step5/run_tracking_manager.py
```

## 🔧 Pipeline Operations Examples

### Commandes STEP5

**MediaPipe CPU (Défaut)**
```bash
TRACKING_DISABLE_GPU=1 \
TRACKING_CPU_WORKERS=4 \
/mnt/venv_ext4/tracking_env_slim/bin/python \
workflow_scripts/step5/run_tracking_manager.py \
--videos videos_to_track.json \
--engine mediapipe
```

**InsightFace GPU (Optionnel)**
```bash
STEP5_ENABLE_GPU=1 \
/mnt/venv_ext4/insightface_env/bin/python \
workflow_scripts/step5/run_tracking_manager.py \
--videos videos_to_track.json \
--engine insightface
```

### Erreurs Communes

**Environment Mismatch Error**
```
ModuleNotFoundError: No module named 'mediapipe'
```
**Solution** : Vous utilisez le mauvais environnement. MediaPipe est dans `tracking_env_slim`, pas `env`.

**GPU Activation Error**  
```
RuntimeError: MediaPipe GPU not supported in this build
```
**Solution** : MediaPipe tourne toujours sur CPU. Pour GPU, utilisez InsightFace dans `insightface_env`.

## 🎬 After Effects Integration Examples

### ExtendScript Bridge

```javascript
// ❌ Mauvais : Appel direct Python depuis AE
system.callSystem("python /path/to/script.py");

// ✅ Bon : Pont sécurisé via media_solution_bridge.py
var bridge = new MediaSolutionBridge();
var trackingData = bridge.loadTrackingData("video1_tracking.json");
```

### JSON Structure pour AE

```json
{
  "metadata": {
    "video_name": "video1.mp4",
    "fps": 30,
    "duration_frames": 900
  },
  "tracking": {
    "face_landmarks": [
      {
        "frame": 0,
        "landmarks": [[x1,y1,z1], [x2,y2,z2], ...],
        "confidence": 0.98
      }
    ]
  },
  "audio": {
    "segments": [
      {
        "start_frame": 0,
        "end_frame": 300,
        "speaker": "SPEAKER_00",
        "text": "Bonjour et bienvenue..."
      }
    ]
  }
}
```

## 🛡️ Best Practices Examples

### Sécurité

```python
# ❌ Mauvais : Secrets en dur
API_KEY = "sk-1234567890abcdef"

# ✅ Bon : Variables d'environnement
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("MISTRAL_API_KEY")
if not API_KEY:
    raise ValueError("MISTRAL_API_KEY requis")
```

### Tests

```python
# ❌ Mauvais : Tests sans fixtures
def test_workflow_service():
    service = WorkflowService()  # Pas de contrôle

# ✅ Bon : Tests avec fixtures contrôlées
@pytest.fixture
def patched_workflow_state():
    with patch('services.workflow_state.WorkflowState') as mock:
        yield mock.return_value

def test_workflow_service(patched_workflow_state):
    service = WorkflowService(mock_fs, patched_workflow_state)
    # Test contrôlé
```

## 📈 État Actuel

### Progression par Catégorie

#### ✅ Architecture Knowledge (17/40 exemples)
- Architecture globale du pipeline
- 5 environnements virtuels et utilisation  
- Exécution STEP5 MediaPipe CPU
- Exécution STEP5 InsightFace GPU
- Configuration STEP4 Audio
- Fonctionnement WorkflowState
- Différence STEP6/STEP7 et JSON générés
- Intégration After Effects
- Bonnes pratiques sécurité
- Démarrage application et vérification services
- Structure dossiers et fichiers importants
- Système configuration centralisée
- Pattern Service Layer
- AppState et réactivité frontend
- DOMBatcher optimisation DOM
- Responsabilités chaque étape pipeline
- Monitoring et logging

**Manquants** : 23 exemples

#### 🔄 Pipeline Operations (0/35 exemples)
**Manquants** : 35 exemples

#### ❌ After Effects Integration (0/15 exemples)  
**Manquants** : 15 exemples

#### ❌ Best Practices/Security (0/10 exemples)
**Manquants** : 10 exemples

## 🎯 Golden Rule

**Dataset spécialisé > modèle générique** : 100 exemples techniques ciblés sur votre pipeline valent mieux qu'un modèle 10x plus grand mais générique. La précision technique sur vos commandes d'environnement vaut plus que la créativité verbale.

---

*Voir [Project Overview](../project/overview.md) pour l'état global et [Dataset Creation Guide](../guides/dataset-creation.md) pour les instructions pratiques.*
