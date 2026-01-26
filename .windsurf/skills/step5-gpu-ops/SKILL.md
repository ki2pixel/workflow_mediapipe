---
name: step5-gpu-ops
description: Operate and debug STEP5 tracking with CPU/GPU engines (MediaPipe, YuNet, OpenSeeFace, EOS). Use when selecting engines, tuning multiprocessing, or validating STEP5 GPU env vars/logs.
---

# STEP5 GPU Ops Skill

## Préparation
1. Lire `.env` → vérifier `STEP5_TRACKING_ENGINE`, `STEP5_ENABLE_GPU`, `STEP5_GPU_ENGINES`, `TRACKING_CPU_WORKERS`, `STEP5_EXPORT_VERBOSE_FIELDS`.
2. Confirmer la présence du venv `tracking_env` (et `eos_env` si moteur EOS).
3. S'assurer que les modèles sont présents dans `workflow_scripts/step5/models/engines/*` (ex: `insightface`, `eos`).
4. Utiliser `resources/engine_diagnostics.md` pour choisir le moteur, vérifier les providers ONNX, activer le profiling ou valider la densité JSON.

## Lancer STEP5
```bash
# Exemple standard CPU (MediaPipe)
TRACKING_DISABLE_GPU=1 tracking_env/bin/python workflow_scripts/step5/run_tracking_manager.py \
  --videos_json_path /tmp/videos.json \
  --tracking_engine mediapipe \
  --cpu_internal_workers 15

# Exemple GPU (InsightFace)
STEP5_ENABLE_GPU=1 STEP5_GPU_ENGINES=insightface tracking_env/bin/python workflow_scripts/step5/run_tracking_manager.py \
  --videos_json_path /tmp/videos.json \
  --tracking_engine insightface
```

## Checklist Diagnostic
1. **Env Vars** : `STEP5_ENABLE_GPU=1` requis pour InsightFace + `STEP5_GPU_ENGINES` contenant le moteur. Les autres moteurs restent CPU.
2. **LD_LIBRARY_PATH** : confirmé via logs `run_tracking_manager.py` (helper `_inject_cuda_ld_library_path`).
3. **Multiprocessing** : `--cpu_internal_workers` ≤ nombre de cœurs disponibles. Vérifier `TRACKING_CPU_WORKERS` côté manager.
4. **Profiling** : activer `STEP5_ENABLE_PROFILING=1` pour logs `[PROFILING] frame ...` toutes les 20 frames.
5. **YuNet Downscale** : `STEP5_YUNET_MAX_WIDTH` (défaut 640). Toujours rescaler bbox/centroid dans les logs.
6. **Export JSON** : JSON dense (frames 1..N). `tracked_objects` vide si aucune détection.

## Résolution des incidents
- **Crash InsightFace FileExistsError** : supprimer/renommer le dossier modèle `~/.insightface/models/antelopev2` (ou laisser le helper `quarantine_model_dir()` le faire) puis relancer.
- **GPU non détecté** : valider `nvidia-smi`, puis lancer `tracking_env/bin/python - <<'PY'` pour importer `onnxruntime` et vérifier `get_available_providers()`.
- **Frames manquantes** : s'assurer que `cv2.VideoCapture` warmup est actif (`process_video_worker`), sinon relancer après `opencv-python` update.
- **Blendshapes tronqués** : confirmer `STEP5_EXPORT_VERBOSE_FIELDS=true` pour debug, sinon landmarks 478 sont supprimés pour réduire la taille.

## Références
- `memory-bank/systemPatterns.md` (sections STEP5 Tracking, Profiling & GPU Support).
- `docs/workflow/pipeline/STEP5_SUIVI_VIDEO.md` pour les tableaux moteurs/env vars.
