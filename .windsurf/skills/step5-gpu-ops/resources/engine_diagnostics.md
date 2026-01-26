# STEP5 Engines — Diagnostics & Switchovers

## 1. Matrice moteurs
| Moteur | Env var clé | GPU support | Logs à vérifier | Notes |
| --- | --- | --- | --- | --- |
| `mediapipe` | `STEP5_TRACKING_ENGINE=mediapipe` | CPU par défaut (GPU expérimental via `STEP5_GPU_ENGINES=mediapipe`) | `logs/step5/manager_*`, `[PROFILING] MediaPipe` | Import lazy via `importlib`; vérifier `STEP5_MEDIAPIPE_MAX_WIDTH` |
| `opencv_yunet` | `STEP5_TRACKING_ENGINE=opencv_yunet` | CPU | `logs/step5/worker_*YUNET*` | `STEP5_YUNET_MAX_WIDTH` pour downscale + rescale bbox |
| `opencv_yunet_pyfeat` | `STEP5_TRACKING_ENGINE=opencv_yunet_pyfeat` | CPU | `logs/step5/worker_*PYFEAT*` | Nécessite FaceMesh ONNX + py-feat; `STEP5_EXPORT_VERBOSE_FIELDS=true` pour landmarks |
| `openseeface` | `STEP5_TRACKING_ENGINE=openseeface` | CPU | `logs/step5/worker_*OPENSEEFACE*` | Vérifier `STEP5_OPENSEEFACE_MAX_WIDTH`, throttle |
| `eos` | `STEP5_TRACKING_ENGINE=eos` | CPU (GPU via object detector) | `logs/step5/worker_*EOS*` | Requiert `eos_env`; assets `workflow_scripts/step5/models/engines/eos/share` |
| `insightface` | `STEP5_TRACKING_ENGINE=insightface` + `STEP5_ENABLE_GPU=1` | GPU obligatoire | `logs/step5/worker_*INSIGHTFACE*` | Vérifier modèles `~/.insightface`, FileExistsError → quarantine |

## 2. Script de validation providers
```bash
tracking_env/bin/python - <<'PY'
import onnxruntime as ort
print('Providers:', ort.get_available_providers())
PY
```
- Attendu : `['CUDAExecutionProvider', 'CPUExecutionProvider']` lorsque GPU actif.

## 3. Switch CPU ↔ GPU (InsightFace)
```bash
# Basculer en GPU InsightFace
export STEP5_TRACKING_ENGINE=insightface
export STEP5_ENABLE_GPU=1
export STEP5_GPU_ENGINES=insightface
unset TRACKING_DISABLE_GPU

# Revenir CPU MediaPipe
export STEP5_TRACKING_ENGINE=mediapipe
export STEP5_ENABLE_GPU=0
export TRACKING_DISABLE_GPU=1
```
- Toujours supprimer `temp_tracking.json` après exécution (`rm -f temp_tracking.json`).

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
