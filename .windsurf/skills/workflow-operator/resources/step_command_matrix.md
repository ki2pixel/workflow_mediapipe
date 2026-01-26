# Step Command Matrix (Workflow Operator)

> **Usage**: lancer les commandes depuis la racine du dépôt **tout en utilisant les interpréteurs situés sous `/mnt/venv_ext4/<venv>/bin/python`**. Toujours vérifier `.env` avant et ne jamais mélanger les environnements virtuels.

| Étape | Objectif | Interpréteur | Commande standard | Logs à surveiller | Pré-requis critiques |
| --- | --- | --- | --- | --- | --- |
| STEP1 | Extraction sécurisée archives | `env/bin/python` | `env/bin/python workflow_scripts/step1/extract_archives.py --source-dir <dir>` | `logs/step1/*.log` | `CACHE_ROOT_DIR` accessible, espace disque suffisant |
| STEP2 | Conversion vidéo 25 FPS | `env/bin/python` | `env/bin/python workflow_scripts/step2/convert_videos.py` | `logs/step2/*.log` | `FFMPEG_BINARY` pointant vers binaire valide |
| STEP3 | Détection de scènes (TransNetV2) | `transnet_env/bin/python` | `transnet_env/bin/python workflow_scripts/step3/run_transnet.py --videos videos_to_track.json` | `logs/step3/*.log` | `transnet_env` provisionné (`torch`, `transnetv2_pytorch`) |
| STEP4 | Analyse audio Lemonfox + fallback Pyannote | `audio_env/bin/python` | `audio_env/bin/python workflow_scripts/step4/run_audio_analysis_lemonfox.py --log_dir logs/step4` | `logs/step4/*.log` | `AUDIO_PROFILE=gpu_fp32`, drivers CUDA 11.x |
| STEP5 | Tracking multi-moteurs | `tracking_env/bin/python` | `tracking_env/bin/python workflow_scripts/step5/run_tracking_manager.py --videos_json_path <path> --tracking_engine <engine>` | `logs/step5/manager_*.log`, `logs/step5/worker_*.log` | `TRACKING_DISABLE_GPU`/`STEP5_ENABLE_GPU` cohérents, modèles présents |
| STEP6 | Réduction JSON | `env/bin/python` | `env/bin/python workflow_scripts/step6/json_reducer.py --log_dir logs/step6 --work_dir projets_extraits` | `logs/step6/*.log` | `STEP6_*` vars définies, fichiers JSON disponibles |
| STEP7 | Finalisation + archivage | `env/bin/python` | `env/bin/python workflow_scripts/step7/finalize_and_copy.py` | `logs/step7/*.log`, `archives/*/metadata.json` | `OUTPUT_DIR`, `ARCHIVES_DIR` et `ResultsArchiver` configurés |

## Rappels critiques
- **Pas de `python3` système** : chaque commande doit utiliser l’interpréteur de l’étape.
- **Logs spécifiques** : utiliser `services/filesystem_service.py` pour ouvrir un dossier de logs depuis l’UI; en CLI, rester en lecture seule.
- **Cache et archives** : vérifier que `CACHE_ROOT_DIR` et `ARCHIVES_DIR` pointent vers des emplacements montés avec suffisamment d’espace (>=200 Go recommandés pour STEP5/STEP7).
