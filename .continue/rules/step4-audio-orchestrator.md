---
description: step4-audio-orchestrator skill migrated from Windsurf as contextual rules
alwaysApply: false
---

# STEP4 Audio Orchestrator

## Préparation

1. Vérifier `.env` : `AUDIO_PROFILE`, `AUDIO_PARTIAL_SUCCESS_OK`, `LEMONFOX_*`, `PYANNOTE_*`.
2. Confirmer `audio_env/bin/python` (torch 1.12.1+cu113) et packages (`pip list | grep torch`).
3. Inspecter `config/settings.py` pour paths (`CACHE_ROOT_DIR`, `AUDIO_MODE`).
4. En cas de doute GPU/oom, ouvrir `.windsurf/skills/step4-audio-orchestrator/resources/gpu_triage.md` (checklist `nvidia-smi`, scripts smoke test, actions correctives Lemonfox/Pyannote).

## Exécution Standard

```bash
audio_env/bin/python workflow_scripts/step4/run_audio_analysis_lemonfox.py \
  --log_dir logs/step4 \
  --input videos_to_track.json
```

- Lemonfox est prioritaire (profil GPU FP32). Pyannote sert de fallback automatique.

## Checklists

### 1. **Profil GPU** : `AUDIO_PROFILE=gpu_fp32` (AMP off) pour éviter divergences GPU/CPU.
   - Éviter `gpu_fp16` ou `gpu_amp` - incompatibles avec Lemonfox/Pyannote
   - Forcer FP32 pour stabilité numérique

### 2. **OOM Handling** : Utiliser `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32`, `torch.cuda.empty_cache()` entre fichiers en cas de crash.
   - Surveillance mémoire GPU : `nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits`
   - Réduire batch size si OOM répété

### 3. **Import isolé** : charger Lemonfox via `importlib` (`services/lemonfox_audio_service.py`) pour éviter les dépendances Flask.
   - Pas d'import direct dans les routes Flask
   - Isolation complète de l'environnement audio

### 4. **Success partiel** : poser `AUDIO_PARTIAL_SUCCESS_OK=1` pour ne pas bloquer la pipeline quand un fichier audio échoue.
   - Continuer sur les autres fichiers vidéos
   - Logger les échecs sans arrêter tout

### 5. **Logs** : surveiller `logs/step4/*.log` pour `is_speech_present`, vérifier smoothing Lemonfox.
   - Vérifier `diarization_segments.json`
   - Contrôler `audio_analysis_complete.json`

## Résolution incidents

### Erreurs GPU
```bash
# Si OOM détecté
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32
audio_env/bin/python -c "import torch; torch.cuda.empty_cache()"

# Reduire batch size
sed -i 's/BATCH_SIZE=.*/BATCH_SIZE=8/' .env
```

### Erreurs Packages
```bash
# Réinstaller torch si nécessaire
audio_env/bin/pip install torch==1.12.1+cu113 torchvision==0.13.1+cu113 --extra-index-url https://download.pytorch.org/whl/cu113

# Vérifier CUDA
audio_env/bin/python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

### Fallback Pyannote
```bash
# Forcer Pyannote si Lemonfox échoue
export USE_PYANNOTE_FALLBACK=1
audio_env/bin/python workflow_scripts/step4/run_audio_analysis_pyannote.py \
  --log_dir logs/step4 \
  --input videos_to_track.json
```

## Validation Outputs

### Fichiers à vérifier
```bash
# Logs d'analyse
ls -la logs/step4/audio_analysis_lemonfox.log
ls -la logs/step4/audio_analysis_pyannote.log

# Outputs finaux
ls -la logs/step4/diarization_segments.json
ls -la logs/step4/audio_analysis_complete.json

# Fichiers temporaires
ls -la $CACHE_ROOT_DIR/audio_cache/
```

### Scripts de test
```bash
# Test smoke Lemonfox
audio_env/bin/python -c "
from services.lemonfox_audio_service import LemonfoxAudioService
service = LemonfoxAudioService()
print('Lemonfox import: OK')
"

# Test GPU memory
audio_env/bin/python -c "
import torch
if torch.cuda.is_available():
    print(f'GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB')
else:
    print('GPU: Not available')
"
```

## Monitoring en cours d'exécution

```bash
# Surveillance temps réel
tail -f logs/step4/audio_analysis_lemonfox.log | grep -E "(ERROR|WARN|OOM|CUDA)"

# Mémoire GPU
watch -n 1 'nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits'

# Progression fichiers
inotifywait -m logs/step4/ -e create,modify
```

## Configuration Recommandée

```bash
# .env optimal pour STEP4
CACHE_ROOT_DIR=/mnt/cache
AUDIO_PROFILE=gpu_fp32
AUDIO_PARTIAL_SUCCESS_OK=1
LEMONFOX_API_KEY=your_key_here
PYANNOTE_MODEL=pyannote/audio segmentation
```

Utilisez ce prompt en tapant `/step4-audio-orchestrator` dans Continue.
