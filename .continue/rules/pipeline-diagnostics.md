---
description: pipeline-diagnostics skill migrated from Windsurf as contextual rules
alwaysApply: false
---

# Pipeline Diagnostics Skill

## Quick Start

1. Lire `.env` via `config/settings.py` (`python - <<'PY' ...`) pour afficher les variables critiques (`CACHE_ROOT_DIR`, `STEP5_*`, `DOWNLOAD_HISTORY_DB_PATH`).
2. Valider l'existence des venv spécialisés (`env/`, `transnet_env/`, `audio_env/`, `tracking_env_slim/`, `insightface_env/`).
3. Pour `tracking_env_slim`, vérifier `requirements-tracking-env-lite.txt` (packages allégés).
4. Vérifier les binaires GPU/CPU (`nvidia-smi`, `ffmpeg -version`, `onnxruntime_test`) selon l'étape cible. Pour STEP5 GPU, vérifier `insightface_env/bin/python` et `onnxruntime-gpu`.
5. Consulter `.windsurf/skills/pipeline-diagnostics/resources/env_health_checklist.md` pour dérouler l'audit complet (commandes `.env`, imports venv, `nvidia-smi`, PRAGMA SQLite) avant chaque run majeur, y compris les vérifications STEP7/STEP8.

## Procédure Complète

### 1. **Sanity `.env`**
   - Charger via `python3 config/settings.py --print` (si script dispo) ou `python - <<'PY'` pour inspecter `config.settings.config`.
   - Contrôler : chemins cache, flags `DRY_RUN_DOWNLOADS`, `STEP5_ENABLE_GPU`, `AUDIO_PROFILE`, URLs webhook.

### 2. **Venv Readiness**
   - `ls env/bin/python transnet_env/bin/python audio_env/bin/python tracking_env_slim/bin/python insightface_env/bin/python`.
   - `python -V` dans chaque venv (ex: `env/bin/python -V`).
   - Pour `tracking_env_slim`, vérifier `requirements-tracking-env-lite.txt` (packages allégés).

### 3. **Hardware & Drivers**
   - `nvidia-smi` (GPU dispo, driver version ≥ 515).
   - `ffmpeg -hide_banner | head -n 1` pour STEP2.
   - `insightface_env/bin/python - <<'PY'` pour importer `onnxruntime` et vérifier `get_available_providers()` (GPU).

### 4. **Filesystem & Permissions**
   - Vérifier `CACHE_ROOT_DIR`, `ARCHIVES_DIR`, `logs/stepX` existent et sont accessibles (`FilesystemService` doit être utilisé côté code; ici on vérifie les répertoires).
   - Pour STEP7, vérifier l'accès aux fichiers `*_tracking.json` en entrée.
   - Pour STEP8, vérifier les permissions d'écriture dans `OUTPUT_DIR` et `ARCHIVES_DIR`.

## Checklists par Étape

### STEP1 (Extract)
```bash
# Vérifier venv de base
env/bin/python -V
ls -la env/bin/python

# Vérifier dépendances
env/bin/pip list | grep -E "(ffmpeg|python-multipart|flask|sqlalchemy)"

# Vérifier fichiers d'entrée
ls -la videos_to_track.json
```

### STEP2 (Convert)
```bash
# Vérifier ffmpeg
ffmpeg -version
which ffmpeg

# Vérifier espaces disque
df -h $CACHE_ROOT_DIR
```

### STEP3 (TransNet)
```bash
# Vérifier venv TransNet
transnet_env/bin/python -V
transnet_env/bin/pip list | grep torch

# Vérifier modèles TransNet
ls -la ~/.transnet/
```

### STEP4 (Audio)
```bash
# Vérifier venv audio
audio_env/bin/python -V
audio_env/bin/pip list | grep -E "(torch|lemonfox|pyannote|whisper)"

# Vérifier profil GPU
echo $AUDIO_PROFILE

# Vérifier GPU pour audio
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits
```

### STEP5 (Tracking)
```bash
# Vérifier venv tracking CPU
tracking_env_slim/bin/python -V
tracking_env_slim/bin/pip list | grep -E "(mediapipe|opencv|numpy)"

# Vérifier venv tracking GPU (si activé)
if [ "$STEP5_ENABLE_GPU" = "1" ]; then
    insightface_env/bin/python -V
    insightface_env/bin/pip list | grep -E "(onnxruntime|insightface|numpy)"
    nvidia-smi
fi

# Vérifier workers CPU
echo $TRACKING_CPU_WORKERS
```

### STEP6 (Reducer)
```bash
# Vérifier venv de base
env/bin/python -V
env/bin/pip list | grep -E "(numpy|pandas|json)"

# Vérifier fichiers d'entrée
ls -la logs/step5/*_tracking.json
```

### STEP7 (AE Preprocess)
```bash
# Vérifier venv de base
env/bin/python -V
env/bin/pip list | grep -E "(json|pathlib|shutil)"

# Vérifier fichiers d'entrée
ls -la logs/step6/*_reduced.json
```

### STEP8 (Finalize)
```bash
# Vérifier venv de base
env/bin/python -V
env/bin/pip list | grep -E "(zip|tar|shutil)"

# Vérifier permissions sortie
ls -la $OUTPUT_DIR
ls -la $ARCHIVES_DIR
```

## Résolution d'Incidents

### Erreurs Communes
| Erreur | Cause | Solution |
|---|---|---|
| `ModuleNotFoundError` | Venv incorrect ou package manquant | Utiliser bon interpréteur, installer package |
| `Permission denied` | Droits fichiers/dossiers | `chmod 755`, vérifier propriétaire |
| `CUDA out of memory` | GPU insuffisante ou mauvais profil | Réduire batch size, utiliser `AUDIO_PROFILE=gpu_fp32` |
| `nvidia-smi not found` | Drivers non installés | Installer drivers NVIDIA ≥ 515 |
| `onnxruntime not found` | InsightFace venv mal configuré | Réinstaller `onnxruntime-gpu` |

### Scripts de Dépannage
```bash
# Test complet des venvs
for venv in env transnet_env audio_env tracking_env_slim insightface_env; do
    echo "Testing $venv:"
    $venv/bin/python -V
done

# Test GPU/CPU
nvidia-smi
lscpu | grep "Model name"

# Test filesystem
test -r $CACHE_ROOT_DIR && echo "Cache OK" || echo "Cache ERROR"
test -w $OUTPUT_DIR && echo "Output OK" || echo "Output ERROR"
```

## Commandes d'Audit Complet

```bash
# Audit complet avant run majeur
python3 - <<'PY'
import os
from config.settings import config

print("=== ENV Audit ===")
print(f"CACHE_ROOT_DIR: {config.CACHE_ROOT_DIR}")
print(f"STEP5_ENABLE_GPU: {os.getenv('STEP5_ENABLE_GPU', '0')}")
print(f"AUDIO_PROFILE: {os.getenv('AUDIO_PROFILE', 'unknown')}")

print("\n=== Venv Audit ===")
venvs = ['env', 'transnet_env', 'audio_env', 'tracking_env_slim', 'insightface_env']
for venv in venvs:
    path = f"/mnt/venv_ext4/{venv}/bin/python"
    exists = os.path.exists(path)
    print(f"{venv}: {'✓' if exists else '✗'} {path}")

print("\n=== Hardware Audit ===")
os.system("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits 2>/dev/null || echo 'GPU: Not available'")
PY'
```

Utilisez ce prompt en tapant `/pipeline-diagnostics` dans Continue.
