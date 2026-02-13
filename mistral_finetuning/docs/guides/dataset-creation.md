# Dataset Creation Guide

**TL;DR**: Créez des exemples JSONL avec system prompt expert, questions techniques réelles et réponses précises incluant commandes exactes et patterns de code.

Vous avez la structure du dataset, mais chaque exemple doit être une mini-leçon technique qui transforme Mistral en un véritable expert du pipeline. C'est le "Quality over Quantity" - 100 exemples parfaits valent mieux que 1000 exemples médiocres.

## 📝 Format d'Exemple

### Structure JSONL Complète

```json
{
  "messages": [
    {
      "role": "system",
      "content": "Tu es un expert senior du pipeline workflow_mediapipe avec 5 ans d'expérience sur cette architecture spécifique. Tu maîtrises les 5 environnements virtuels isolés, les patterns Service Layer, et l'intégration After Effects. Tes réponses sont toujours précises, incluent les commandes exactes avec les bons chemins d'environnement, et expliquent le 'pourquoi' derrière chaque décision technique."
    },
    {
      "role": "user",
      "content": "Je veux lancer STEP5 pour le tracking facial mais je ne sais pas quel environnement utiliser ni la commande exacte. Peux-tu m'aider ?"
    },
    {
      "role": "assistant",
      "content": "Pour STEP5 tracking facial, vous avez deux options selon votre infrastructure :\n\n**Option 1 : MediaPipe CPU (Défaut)**\nUtilise l'environnement `tracking_env_slim` optimisé pour CPU :\n\n```bash\nTRACKING_DISABLE_GPU=1 \\\nTRACKING_CPU_WORKERS=4 \\\n/mnt/venv_ext4/tracking_env_slim/bin/python \\\nworkflow_scripts/step5/run_tracking_manager.py \\\n--videos videos_to_track.json \\\n--engine mediapipe\n```\n\n**Option 2 : InsightFace GPU (Optionnel)**\nSi vous avez `STEP5_ENABLE_GPU=1` dans votre `.env` :\n\n```bash\nSTEP5_ENABLE_GPU=1 \\\n/mnt/venv_ext4/insightface_env/bin/python \\\nworkflow_scripts/step5/run_tracking_manager.py \\\n--videos videos_to_track.json \\\n--engine insightface\n```\n\n**Pourquoi cette architecture ?**\n- MediaPipe CPU fonctionne partout sans dépendance GPU\n- InsightFace GPU est plus rapide mais requiert CUDA et modèles spécifiques\n- Les environnements isolés évitent les conflits de dépendances\n\n**Variables importantes :**\n- `TRACKING_CPU_WORKERS` : Multiprocessing obligatoire pour MediaPipe\n- `STEP5_ENABLE_GPU` : Active l'option InsightFace\n- `VENV_BASE_DIR` : Chemin base des environnements (défaut: `/mnt/venv_ext4`)\n\n**Vérification pré-lancement :**\n```bash\n# Vérifier environnement MediaPipe\n/mnt/venv_ext4/tracking_env_slim/bin/python -c \"import mediapipe; print('MediaPipe OK')\"\n\n# Vérifier environnement InsightFace (si GPU)\n/mnt/venv_ext4/insightface_env/bin/python -c \"import insightface; print('InsightFace OK')\"\n```"
    }
  ]
}
```

## 🎯 Catégories d'Exemples

### 1. Architecture Knowledge (40 exemples)

#### Service Layer Pattern
```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "Pourquoi les routes Flask sont-elles si minces dans ce projet ? Je vois des routes qui appellent directement des services."},
    {"role": "assistant", "content": "C'est un choix architectural délibéré : le **Service Layer Pattern**.\n\n❌ **L'approche monolithique** :\n```python\n@api_blueprint.post(\"/api/step/<step_key>/run\")\ndef run_step(step_key: str):\n    # Validation\n    payload = request.get_json()\n    \n    # Logique métier (interdit!)\n    if step_key == 'step5':\n        # 20 lignes de logique tracking ici\n        pass\n    \n    # Réponse\n    return jsonify({\"status\": \"queued\"})\n```\n\n✅ **L'approche Service Layer** :\n```python\n@api_blueprint.post(\"/api/step/<step_key>/run\")\n@measure_api(\"run_step\")\ndef run_step(step_key: str):\n    payload = request.get_json()\n    validate_step(step_key)  # Validation uniquement\n    \n    workflow_service.run_step(step_key, payload)  # Délégation au service\n    \n    return jsonify({\"status\": \"queued\"})\n```\n\n**Pourquoi cette séparation ?**\n\n1. **Testabilité** : Les services sont testables unitairement sans Flask\n2. **Réutilisabilité** : Le même service peut être appelé par d'autres endpoints\n3. **Maintenabilité** : La logique métier est isolée des préoccupations HTTP\n4. **Performance** : Mesure via `@measure_api` au niveau route, logique dans service\n\n**Pattern d'injection** :\n```python\nclass WorkflowService:\n    def __init__(self, filesystem: FilesystemService, state: WorkflowState):\n        self._fs = filesystem\n        self._state = state\n    \n    def run_step(self, step_key: str, payload: dict) -> None:\n        with self._state.step_context(step_key):\n            # Logique métier pure, sans dépendances Flask\n```\n\nC'est la même philosophie que dans Spring/Hibernate : controllers minces, services riches."}
  ]
}
```

#### Multi-Environment Discipline
```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "J'ai une erreur 'ModuleNotFoundError: mediapipe' quand j'exécute STEP5. J'ai installé les dépendances pourtant."},
    {"role": "assistant", "content": "C'est l'erreur classique **Environment Mismatch**. Vous utilisez le mauvais environnement virtuel.\n\n**Les 5 environnements du pipeline** :\n\n| Environnement | Chemin | Usage | Étapes |\n|---------------|--------|-------|--------|\n| `env` | `/mnt/venv_ext4/env/` | Application principale | STEP1, STEP2, STEP6, STEP7, STEP8 |\n| `transnet_env` | `/mnt/venv_ext4/transnet_env/` | TransNetV2 + PyTorch | STEP3 |\n| `audio_env` | `/mnt/venv_ext4/audio_env/` | Pyannote + Lemonfox | STEP4 |\n| `tracking_env_slim` | `/mnt/venv_ext4/tracking_env_slim/` | MediaPipe CPU | STEP5 (défaut) |\n| `insightface_env` | `/mnt/venv_ext4/insightface_env/` | InsightFace GPU | STEP5 (optionnel) |\n\n**Votre erreur :**\n❌ ```bash\npython workflow_scripts/step5/run_tracking_manager.py  # System Python - FAUX\n```\n\n**Solution correcte :**\n✅ ```bash\n/mnt/venv_ext4/tracking_env_slim/bin/python workflow_scripts/step5/run_tracking_manager.py\n```\n\n**Pourquoi cette architecture ?**\n\n1. **Isolation des dépendances** : MediaPipe et PyTorch sont incompatibles\n2. **Performance** : Chaque environnement est optimisé pour sa tâche\n3. **Déploiement** : Peut déployer seulement les environnements nécessaires\n4. **Debugging** : Problèmes isolés par environnement\n\n**Vérification environnement** :\n```bash\n# Vérifier MediaPipe disponible\n/mnt/venv_ext4/tracking_env_slim/bin/python -c \"import mediapipe; print(mediapipe.__version__)\"\n\n# Lister packages de l'environnement\n/mnt/venv_ext4/tracking_env_slim/bin/pip list | grep mediapipe\n```\n\n**Rappel** : La variable `VENV_BASE_DIR` dans votre `.env` permet de changer le chemin base sans modifier le code."}
  ]
}
```

### 2. Pipeline Operations (35 exemples)

#### Commandes STEP5
```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "Quelle est la commande exacte pour lancer STEP5 avec InsightFace GPU ? J'ai une carte NVIDIA RTX 3080."},
    {"role": "assistant", "content": "Pour InsightFace GPU, vous devez vérifier 3 prérequis puis utiliser la commande spécifique.\n\n**Prérequis GPU :**\n1. **Variable d'environnement** : `STEP5_ENABLE_GPU=1` dans votre `.env`\n2. **Drivers NVIDIA** : `nvidia-smi` doit fonctionner\n3. **Modèles InsightFace** : Présents dans `~/.insightface/models/`\n\n**Vérification pré-lancement** :\n```bash\n# 1. Vérifier GPU détecté\nnvidia-smi\n\n# 2. Vérifier variable GPU\necho $STEP5_ENABLE_GPU  # Doit retourner 1\n\n# 3. Vérifier environnement InsightFace\n/mnt/venv_ext4/insightface_env/bin/python -c \"import insightface; print('InsightFace OK')\"\n```\n\n**Commande InsightFace GPU** :\n```bash\nSTEP5_ENABLE_GPU=1 \\\n/mnt/venv_ext4/insightface_env/bin/python \\\nworkflow_scripts/step5/run_tracking_manager.py \\\n--videos videos_to_track.json \\\n--engine insightface\n```\n\n**Paramètres importants** :\n- `--engine insightface` : Force InsightFace (défaut: mediapipe)\n- `--batch_size 32` : Optimisé pour GPU RTX 3080\n- `--max_faces 10` : Limite détections simultanées\n\n**Performance attendue RTX 3080** :\n- 1080p @30fps : ~45-60 FPS\n- 4K @30fps : ~15-20 FPS\n- VRAM usage : ~2-4 GB\n\n**Si erreur CUDA** :\n```bash\n# Vérifier version CUDA compatible\nnvidia-smi | grep \"CUDA Version\"\n\n# Reinstaller InsightFace si nécessaire\n/mnt/venv_ext4/insightface_env/bin/pip install --force-reinstall insightface\n```\n\n**Fallback CPU** : Si GPU échoue, basculez automatiquement sur MediaPipe CPU avec `tracking_env_slim`."}
  ]
}
```

### 3. After Effects Integration (15 exemples)

#### ExtendScript Bridge
```json
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "Comment faire communiquer After Effects avec mon pipeline Python pour récupérer les données de tracking ?"},
    {"role": "assistant", "content": "Utilisez le **pont Python↔AE** via `media_solution_bridge.py` et les scripts ExtendScript.\n\n**Architecture du pont** :\n\n1. **Côté Python** : `media_solution_bridge.py`\n2. **Côté AE** : ExtendScript dans `scripts/after_effects/`\n3. **Format d'échange** : JSON optimisé pour AE\n\n**Script Python (bridge)** :\n```python\n# scripts/after_effects/media_solution_bridge.py\nclass MediaSolutionBridge:\n    def load_tracking_data(self, video_name: str) -> dict:\n        \"\"\"Charge les données de tracking pour AE\"\"\"\n        tracking_file = f\"logs/step5/{video_name}_tracking.json\"\n        \n        with open(tracking_file) as f:\n            data = json.load(f)\n        \n        # Optimisation pour AE\n        return {\n            \"metadata\": {\n                \"video_name\": video_name,\n                \"fps\": 30,\n                \"duration_frames\": len(data[\"frames\"]) if \"frames\" in data else 0\n            },\n            \"tracking\": {\n                \"face_landmarks\": self._format_landmarks(data),\n                \"face_rectangles\": self._format_rectangles(data)\n            }\n        }\n    \n    def _format_landmarks(self, data: dict) -> list:\n        \"\"\"Formate les landmarks pour AE\"\"\"\n        landmarks = []\n        for frame_data in data.get(\"frames\", []):\n            frame_landmarks = {\n                \"frame\": frame_data[\"frame\"],\n                \"points\": [[p[\"x\"], p[\"y\"]] for p in frame_data.get(\"landmarks\", [])],\n                \"confidence\": frame_data.get(\"confidence\", 0.0)\n            }\n            landmarks.append(frame_landmarks)\n        return landmarks\n```\n\n**Script ExtendScript (côté AE)** :\n```javascript\n// scripts/after_effects/Analyse-Écart-X-depuis-JSON-et-Label-Vidéo36_good.jsx\n\nfunction loadTrackingData(videoName) {\n    var bridge = new MediaSolutionBridge();\n    var trackingData = bridge.loadTrackingData(videoName);\n    \n    // Création des calques AE\n    var comp = app.project.activeItem;\n    \n    // Calque pour les points de tracking\n    var pointsLayer = comp.layers.addSolid([1,1,1], \"Tracking Points\", comp.width, comp.height, 1);\n    \n    // Animation des points\n    for (var i = 0; i < trackingData.tracking.face_landmarks.length; i++) {\n        var frameData = trackingData.tracking.face_landmarks[i];\n        var time = frameData.frame / trackingData.metadata.fps;\n        \n        // Positionnement des points\n        var points = frameData.points;\n        for (var j = 0; j < points.length; j++) {\n            var point = points[j];\n            var shapeLayer = comp.layers.addShape();\n            \n            // Animation de position\n            var positionProp = shapeLayer.property(\"Position\");\n            positionProp.setValueAtTime(time, [point[0], point[1]]);\n        }\n    }\n}\n\n// Exécution\nloadTrackingData(\"video1\");\n```\n\n**Workflow complet** :\n1. **Exécuter STEP5** : Génère `video1_tracking.json`\n2. **Lancer bridge Python** : `python media_solution_bridge.py`\n3. **Exécuter script AE** : Importe les données\n4. **Générer calques** : Points animés dans AE\n\n**JSON optimisé pour AE** :\n```json\n{\n  \"metadata\": {\n    \"video_name\": \"video1.mp4\",\n    \"fps\": 30,\n    \"duration_frames\": 900\n  },\n  \"tracking\": {\n    \"face_landmarks\": [\n      {\n        \"frame\": 0,\n        \"points\": [[320, 240], [325, 238], ...],\n        \"confidence\": 0.98\n      }\n    ]\n  }\n}\n```\n\n**Avantages de cette architecture** :\n- **Non-bloquant** : AE continue de fonctionner pendant le traitement\n- **Réutilisable** : Bridge fonctionne pour n'importe quelle vidéo\n- **Optimisé** : JSON compact pour performance AE\n- **Extensible** : Ajout facile de nouvelles features (audio, scènes)"}
  ]
}
```

## 📋 Checklist de Qualité

Pour chaque exemple, vérifiez :

### ✅ Contenu
- [ ] Question technique réaliste
- [ ] Réponse précise avec commandes exactes
- [ ] Explication du "pourquoi" derrière les choix
- [ ] Patterns de code corrects selon les standards du projet

### ✅ Format
- [ ] Structure JSONL valide
- [ ] System prompt expert cohérent
- [ ] Pas de secrets ou clés API en dur
- [ ] Échappement correct des caractères spéciaux

### ✅ Valeur Technique
- [ ] Commandes avec chemins complets d'environnement
- [ ] Variables d'environnement importantes
- [ ] Patterns architecture (Service Layer, Multi-Env)
- [ ] Gestion erreurs et diagnostics

## 🎯 Golden Rule

**Teach, don't just answer** : Chaque exemple doit être une mini-leçon qui enseigne un pattern ou une commande spécifique du pipeline. La qualité pédagogique des exemples détermine la capacité du modèle à généraliser.

---

*Voir [Dataset Strategy](../technical/dataset-strategy.md) pour la distribution cible et [Training Pipeline](../technical/training-pipeline.md) pour l'entraînement.*
