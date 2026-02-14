---
description: Operate and debug STEP5 tracking with MediaPipe (CPU) or InsightFace (GPU-only). Use when selecting engines, tuning multiprocessing, or validating STEP5 GPU env vars/logs.
alwaysApply: false
---

# STEP5 GPU Ops Skill

## Préparation

1. Lire `.env` → vérifier `STEP5_TRACKING_ENGINE`, `STEP5_ENABLE_GPU`, `STEP5_INSIGHTFACE_*`, `STEP5_MEDIAPIPE_*`, `STEP5_BLENDSHAPES_THROTTLE_N`, `STEP5_EXPORT_VERBOSE_FIELDS`.
2. Confirmer la présence du venv `tracking_env_slim` (CPU) et `insightface_env` (GPU).
3. S'assurer que les modèles sont présents dans `workflow_scripts/step5/models/engines/*` (ex: `insightface`, object detectors).
4. Utiliser `.windsurf/skills/step5-gpu-ops/resources/engine_diagnostics.md` pour choisir le moteur, vérifier les providers ONNX, activer le profiling ou valider la densité JSON.

## Lancer STEP5

### Exemple standard CPU (MediaPipe) - via tracking_env_slim
```bash
TRACKING_DISABLE_GPU=1 tracking_env_slim/bin/python workflow_scripts/step5/run_tracking_manager.py \
  --videos_json_path /tmp/videos.json \
  --cpu_internal_workers 15
```

### Exemple GPU (InsightFace) - via insightface_env
```bash
STEP5_ENABLE_GPU=1 STEP5_TRACKING_ENGINE=insightface insightface_env/bin/python workflow_scripts/step5/run_tracking_manager.py \
  --videos_json_path /tmp/videos.json \
  --tracking_engine insightface
```

## Checklist Diagnostic

### 1. **Env Vars** : `STEP5_ENABLE_GPU=1` requis pour InsightFace + `STEP5_TRACKING_ENGINE=insightface`. MediaPipe CPU via `tracking_env_slim` ignore ces flags et utilise multiprocessing.
   - `STEP5_TRACKING_ENGINE=mediapipe` (défaut CPU)
   - `STEP5_TRACKING_ENGINE=insightface` (GPU optionnel)
   - `TRACKING_CPU_WORKERS` : nombre de workers pour MediaPipe

### 2. **LD_LIBRARY_PATH** : confirmé via logs `run_tracking_manager.py` (helper `_collect_cuda_lib_paths` + `_apply_ld_library_path`).
   - Vérifier les logs pour les chemins CUDA
   - Assurer que les bibliothèques GPU sont trouvées

### 3. **Multiprocessing** : `--cpu_internal_workers` ≤ nombre de cœurs disponibles.
   - Vérifier `TRACKING_CPU_WORKERS` côté manager
   - Utiliser `nproc` ou `lscpu` pour connaître le nombre de cœurs

## Configuration des Moteurs

### MediaPipe (CPU - Défaut)
```bash
# Configuration optimale
TRACKING_DISABLE_GPU=1
TRACKING_CPU_WORKERS=8  # Ajuster selon CPU
STEP5_TRACKING_ENGINE=mediapipe

# Vérification
tracking_env_slim/bin/python -c "
import mediapipe
print(f'MediaPipe version: {mediapipe.__version__}')
"
```

### InsightFace (GPU - Optionnel)
```bash
# Configuration requise
STEP5_ENABLE_GPU=1
STEP5_TRACKING_ENGINE=insightface
STEP5_INSIGHTFACE_MODEL=buf_500_14_2024-02-14
STEP5_INSIGHTFACE_PROVIDERS=['CUDAExecutionProvider', 'CPUExecutionProvider']

# Vérification GPU
insightface_env/bin/python -c "
import onnxruntime as ort
print(f'ONNX providers: {ort.get_available_providers()}')
print(f'GPU available: {ort.get_device() == \"GPU\"}')
"
```

## Dépannage Commun

### Erreurs CUDA
```bash
# Si erreur CUDA
export CUDA_VISIBLE_DEVICES=0
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Test CUDA
insightface_env/bin/python -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA device: {torch.cuda.get_device_name(0)}')
"
```

### Erreurs Modèles
```bash
# Vérifier modèles InsightFace
ls -la ~/.insightface/models/
ls -la workflow_scripts/step5/models/engines/

# Télécharger modèle manquant
wget -P ~/.insightface/models/ https://github.com/deepinsight/insightface/releases/download/v0.2.0/insightface-0.2.0-py3-none-any.whl
```

### Performance Tuning
```bash
# MediaPipe : optimiser workers
TRACKING_CPU_WORKERS=$(nproc)
echo "Using $TRACKING_CPU_WORKERS workers"

# InsightFace : optimiser batch
export STEP5_INSIGHTFACE_BATCH_SIZE=4
export STEP5_INSIGHTFACE_DETECTION_THRESHOLD=0.5
```

## Validation des Outputs

### Fichiers générés
```bash
# Vérifier outputs finaux
ls -la logs/step5/*_tracking.json
ls -la logs/step5/tracking_summary.json

# Vérifier densité JSON
python3 -c "
import json
with open('logs/step5/video_name_tracking.json', 'r') as f:
    data = json.load(f)
print(f'Tracked frames: {len(data)}')
print(f'Objects per frame: {sum(1 for frame in data if frame.get(\"tracked_objects\"))}')
"
```

### Logs de performance
```bash
# Surveillance en temps réel
tail -f logs/step5/run_tracking_manager.log | grep -E "(FPS|ERROR|WARN|GPU|CUDA)"

# Utilisation GPU
watch -n 1 'nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits'
```

## Scripts de Test

### Test moteur MediaPipe
```bash
tracking_env_slim/bin/python -c "
import mediapipe as mp
mp_drawing = mp.solutions.drawing_utils
print('MediaPipe import: OK')
"
```

### Test moteur InsightFace
```bash
insightface_env/bin/python -c "
import insightface
print(f'InsightFace version: {insightface.__version__}')
"
```

## Configuration Recommandée

```bash
# .env optimal pour STEP5
# Pour MediaPipe CPU (défaut)
TRACKING_DISABLE_GPU=1
TRACKING_CPU_WORKERS=8

# Pour InsightFace GPU (optionnel)
STEP5_ENABLE_GPU=1
STEP5_TRACKING_ENGINE=insightface
STEP5_INSIGHTFACE_MODEL=buf_500_14_2024-02-14
```

Utilisez ce prompt en tapant `/step5-gpu-ops` dans Continue.
