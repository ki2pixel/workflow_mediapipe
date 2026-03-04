# STEP5 Engines — Diagnostics & Switchovers

## 1. Matrice moteurs (v4.2 simplifiée)
| Moteur | Env var clé | GPU support | Logs à vérifier | Notes |
| --- | --- | --- | --- | --- |
| `mediapipe` | `STEP5_TRACKING_ENGINE=""` (défaut) | CPU via `tracking_env_slim` | `logs/step5/manager_*`, `[PROFILING] MediaPipe` | Import lazy via `importlib`; vérifier `STEP5_MEDIAPIPE_MAX_WIDTH` |
| `insightface` | `STEP5_TRACKING_ENGINE=insightface` + `STEP5_ENABLE_GPU=1` | GPU obligatoire via `insightface_env` | `logs/step5/worker_*INSIGHTFACE*` | Vérifier modèles `~/.insightface`, FileExistsError → quarantine |

## 2. Script de validation providers
```bash
# Pour InsightFace (GPU)
insightface_env/bin/python - <<'PY'
import onnxruntime as ort
print('Providers:', ort.get_available_providers())
PY
```
- Attendu : `['CUDAExecutionProvider', 'CPUExecutionProvider']` lorsque GPU actif.

```bash
# Pour MediaPipe (CPU) - tracking_env_slim
tracking_env_slim/bin/python - <<'PY'
import mediapipe as mp
print('MediaPipe version:', mp.__version__)
PY
```

## 3. Switch CPU ↔ GPU (InsightFace)
```bash
# Basculer en GPU InsightFace
export STEP5_TRACKING_ENGINE=insightface
export STEP5_ENABLE_GPU=1
# Utiliser insightface_env/bin/python pour l'exécution

# Revenir CPU MediaPipe (par défaut)
export STEP5_TRACKING_ENGINE=""
export STEP5_ENABLE_GPU=0
export TRACKING_DISABLE_GPU=1
# Utiliser tracking_env_slim/bin/python pour l'exécution
```
- Toujours supprimer `temp_tracking.json` après exécution (`rm -f temp_tracking.json`).
- Les anciens moteurs (opencv_*, openseeface, eos) ont été supprimés en Phase 2 (décision 2026-02-03).

## 4. Checks JSON densité
```bash
python - <<'PY'
import json, sys
from pathlib import Path
path = Path('results/step5/output.json')
data = json.loads(path.read_text())
frames = data['frames']
print('Frames count:', len(frames))
missing = [i for i, frame in enumerate(frames, start=1) if frame['frame_index'] != i]
print('Missing indices:', missing[:10])
PY
```
- Si `missing` non vide → vérifier warmup `cap.read()` et chunking.

## 5. Profiling hooks
- Activer `STEP5_ENABLE_PROFILING=1` puis inspecter `logs/step5/worker_*` pour `[PROFILING] frame` toutes les 20 frames.
- Ajuster `STEP5_BLENDSHAPES_THROTTLE_N` pour réduire la pression CPU lors des runs longue durée.
- Pour `tracking_env_slim`, utiliser `requirements-tracking-env-lite.txt` (packages allégés, pas de GPU).
