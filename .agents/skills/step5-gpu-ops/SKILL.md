---
name: step5-gpu-ops
description: Operate and debug STEP5 tracking with MediaPipe (CPU) or InsightFace (GPU-only). Use when selecting engines, tuning multiprocessing, or validating STEP5 GPU env vars/logs.
---

# STEP5 GPU Ops Skill

## Préparation
1. Lire `.env` → vérifier `STEP5_TRACKING_ENGINE`, `STEP5_ENABLE_GPU`, `STEP5_INSIGHTFACE_*`, `STEP5_MEDIAPIPE_*`, `STEP5_BLENDSHAPES_THROTTLE_N`, `STEP5_EXPORT_VERBOSE_FIELDS`.
2. Confirmer la présence du venv `tracking_env_slim` (CPU) et `insightface_env` (GPU).
3. S'assurer que les modèles sont présents dans `workflow_scripts/step5/models/engines/*` (ex: `insightface`, object detectors).
4. Utiliser `resources/engine_diagnostics.md` pour choisir le moteur, vérifier les providers ONNX, activer le profiling ou valider la densité JSON.

## Lancer STEP5
```bash
# Exemple standard CPU (MediaPipe) - via tracking_env_slim
TRACKING_DISABLE_GPU=1 tracking_env_slim/bin/python workflow_scripts/step5/run_tracking_manager.py \
  --videos_json_path /tmp/videos.json \
  --cpu_internal_workers 15

# Exemple GPU (InsightFace) - via insightface_env
STEP5_ENABLE_GPU=1 STEP5_TRACKING_ENGINE=insightface insightface_env/bin/python workflow_scripts/step5/run_tracking_manager.py \
  --videos_json_path /tmp/videos.json \
  --tracking_engine insightface
```

## Checklist Diagnostic
1. **Env Vars** : `STEP5_ENABLE_GPU=1` requis pour InsightFace + `STEP5_TRACKING_ENGINE=insightface`. MediaPipe CPU via `tracking_env_slim` ignore ces flags et utilise multiprocessing.
2. **LD_LIBRARY_PATH** : confirmé via logs `run_tracking_manager.py` (helper `_collect_cuda_lib_paths` + `_apply_ld_library_path`).
3. **Multiprocessing** : `--cpu_internal_workers` ≤ nombre de cœurs disponibles. Vérifier `TRACKING_CPU_WORKERS` côté manager.
4. **Profiling** : activer `STEP5_ENABLE_PROFILING=1` pour logs `[PROFILING] frame ...` toutes les 20 frames.
5. **MediaPipe CPU** : utilise `tracking_env_slim` (allégé), multiprocessing obligatoire via `process_video_worker_multiprocessing.py` (`TRACKING_CPU_WORKERS`).
6. **Modèles Interdits** : YuNet, EOS, OpenSeeFace, py-feat et OpenCV Haar sont strictement interdits. Le pipeline cloud (Lightning/Vultr) est abandonné.
7. **Export JSON** : L'utilisation de `StreamingJSONOutput` est obligatoire pour écrire le JSON en flux O(1) RAM. `tracked_objects` vide si aucune détection.

## Résolution des incidents
- **Crash InsightFace FileExistsError** : supprimer/renommer le dossier modèle `~/.insightface/models/antelopev2` (ou laisser le helper `quarantine_model_dir()` dans `InsightFaceEngine` le faire) puis relancer.
- **GPU non détecté** : valider `nvidia-smi`, puis lancer `insightface_env/bin/python - <<'PY'` pour importer `onnxruntime` et vérifier `get_available_providers()`.
- **Frames manquantes** : s'assurer que `cv2.VideoCapture` warmup est actif (`process_video_worker`), sinon relancer après `opencv-python` update.
- **Blendshapes tronqués** : confirmer `STEP5_EXPORT_VERBOSE_FIELDS=true` pour debug, sinon landmarks 468 sont supprimés pour réduire la taille.
- **MediaPipe CPU lent** : réduire `--cpu_internal_workers` ou activer `STEP5_ENABLE_OBJECT_DETECTION=1` pour fallback object detector.
- **tracking_env_slim manquant** : créer l'environnement via `requirements-tracking-env-lite.txt` et vérifier que `config.WorkflowCommandsConfig` pointe vers `tracking_env_slim`.

## Références
- `memory-bank/systemPatterns.md` (sections STEP5 Tracking, Profiling & GPU Support).
- `docs/workflow/pipeline/STEP5_SUIVI_VIDEO.md` pour les tableaux moteurs/env vars.

**Locking Instruction:** NE PAS essayer de lire les fichiers de la memory-bank via le filesystem (outil read_text_file). Utilise EXCLUSIVEMENT les outils du serveur MCP 'fast-filesystem' (outils fast_*) pour lire ou écrire dans la Memory Bank avec des chemins absolus.
