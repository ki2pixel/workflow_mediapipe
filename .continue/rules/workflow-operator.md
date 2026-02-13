---
description: Expert Opérateur certifié v4.1. Lance, monitore et débogue le pipeline MediaPipe en respectant strictement l'architecture Services/State et les environnements virtuels dédiés.
globs: 
  - "**/*.{py,js,md}"
alwaysApply: true
---

# Workflow MediaPipe Operator (v4.1 Standards Compliant)

Cette skill permet d'opérer le pipeline en respectant les règles définies dans `codingstandards.md`.

## 1. Architecture & Environnements

Le pipeline est segmenté. **Règle d'or :** Toujours utiliser l'interpréteur Python spécifique à l'étape. Ne jamais utiliser `python3` système.

| Étape | Dossier | Environnement (VENV) | Service Clé |
| :--- | :--- | :--- | :--- |
| **STEP 1** (Extract) | `step1/` | `env/` | `FilesystemService` |
| **STEP 2** (Convert) | `step2/` | `env/` | `ffmpeg` (via subprocess) |
| **STEP 3** (TransNet) | `step3/` | `transnet_env/` | `WorkflowService` |
| **STEP 4** (Audio) | `step4/` | `audio_env/` | `LemonfoxAudioService` |
| **STEP 5** (Tracking) | `step5/` | `tracking_env_slim/` (CPU) / `insightface_env/` (GPU) | `InsightFaceEngine (GPU-only) + factory` |
| **STEP 6** (Reducer) | `step6/` | `env/` | N/A |
| **STEP 7** (AE Preprocess) | `step7/` | `env/` | N/A |
| **STEP 8** (Finalize) | `step8/` | `env/` | `ResultsArchiver` |

**Chemins des Venvs (interpréteurs montés sous `/mnt/venv_ext4`) :**
- Base : `env/bin/python`
- TransNet : `transnet_env/bin/python`
- Audio : `audio_env/bin/python`
- Tracking : `tracking_env_slim/bin/python` (MediaPipe CPU, allégé)
- InsightFace : `insightface_env/bin/python` (GPU-only)

## 2. Commandes par Étape

Ces commandes doivent être lancées depuis la racine du projet **tout en ciblant les interpréteurs situés dans `/mnt/venv_ext4/<venv>/bin/python`** (pas le Python système).

> 🔎 **Raccourci** : consultez `.windsurf/skills/workflow-operator/resources/step_command_matrix.md` pour une vue tabulaire des 8 étapes (interpréteur, commande, logs, prérequis). Gardez le fichier ouvert pendant les interventions d'astreinte.

### STEP 1-2 (Base env)
```bash
/mnt/venv_ext4/env/bin/python workflow_scripts/step1/extract_archives.py --input videos_to_track.json
/mnt/venv_ext4/env/bin/python workflow_scripts/step2/convert_videos.py --videos videos_to_track.json
```

### STEP 3 (TransNet)
```bash
/mnt/venv_ext4/transnet_env/bin/python workflow_scripts/step3/run_transnet.py --videos videos_to_track.json
```

### STEP 4 (Audio)
```bash
/mnt/venv_ext4/audio_env/bin/python workflow_scripts/step4/run_audio_analysis.py --videos videos_to_track.json
```

### STEP 5 (Tracking)
```bash
# MediaPipe CPU (défaut)
TRACKING_DISABLE_GPU=1 /mnt/venv_ext4/tracking_env_slim/bin/python workflow_scripts/step5/run_tracking_manager.py --videos videos_to_track.json

# InsightFace GPU (si STEP5_ENABLE_GPU=1)
/mnt/venv_ext4/insightface_env/bin/python workflow_scripts/step5/run_tracking_manager.py --videos videos_to_track.json
```

### STEP 6-8 (Base env)
```bash
/mnt/venv_ext4/env/bin/python workflow_scripts/step6/reduce_tracking_data.py --videos videos_to_track.json
/mnt/venv_ext4/env/bin/python workflow_scripts/step7/preprocess_for_ae.py --videos videos_to_track.json
/mnt/venv_ext4/env/bin/python workflow_scripts/step8/finalize_results.py --videos videos_to_track.json
```

## 3. Variables d'Environnement Clés

- `VENV_BASE_DIR` : Base des environnements virtuels (défaut: `/mnt/venv_ext4`)
- `STEP5_ENABLE_GPU` : Active InsightFace GPU (défaut: 0)
- `TRACKING_CPU_WORKERS` : Nombre de workers MediaPipe (défaut: 4)
- `AUDIO_PROFILE` : Profil audio GPU (défaut: `gpu_fp32`)
- `CACHE_ROOT_DIR` : Racine du cache temporaire

## 4. Debugging & Monitoring

### Vérifier l'état du pipeline
```bash
curl -s http://localhost:5000/api/status | jq .
```

### Logs par étape
- `logs/step1/` à `logs/step8/` : Logs détaillés par étape
- `logs/step5/tracking_*.log` : Logs spécifiques au tracking

### Health checks
```bash
# Vérifier les venvs
python -c "import sys; print(sys.executable)"

# Vérifier GPU (si InsightFace)
nvidia-smi
```

## 5. Bonnes Pratiques

1. **Toujours vérifier** `WorkflowState` avant de lancer une étape
2. **Utiliser les commandes exactes** - pas de raccourcis `python3`
3. **Monitorer les ressources** : CPU pour MediaPipe, GPU pour InsightFace
4. **Vérifier les fichiers de sortie** après chaque étape
5. **Consulter les logs** en cas d'erreur

## 6. Dépannage Commun

| Problème | Solution |
|---|---|
| `ImportError` dans une étape | Vérifier le venv utilisé |
| GPU non détecté | Vérifier `STEP5_ENABLE_GPU=1` et nvidia-smi |
| Fichiers manquants | Vérifier `videos_to_track.json` |
| Permission denied | Vérifier les droits sur `/mnt/cache` |

Pour utiliser ce prompt, tapez `/workflow-operator` dans Chat, Agent ou Edit mode.
