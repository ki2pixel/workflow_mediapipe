---
name: step4-audio-orchestrator
description: Operate STEP4 audio analysis (Lemonfox + Pyannote fallback). Use when tuning CUDA profiles, handling OOM, or validating diarization exports/logs in audio_env.
---

# STEP4 Audio Orchestrator

## Préparation
1. Vérifier `.env` : `AUDIO_PROFILE`, `AUDIO_PARTIAL_SUCCESS_OK`, `LEMONFOX_*`, `PYANNOTE_*`.
2. Confirmer `audio_env/bin/python` (torch 1.12.1+cu113) et packages (`pip list | grep torch`).
3. Inspecter `config/settings.py` pour paths (`CACHE_ROOT_DIR`, `AUDIO_MODE`).
4. En cas de doute GPU/oom, ouvrir `resources/gpu_triage.md` (checklist `nvidia-smi`, scripts smoke test, actions correctives Lemonfox/Pyannote).

## Exécution Standard
```bash
audio_env/bin/python workflow_scripts/step4/run_audio_analysis_lemonfox.py \
  --log_dir logs/step4 \
  --input videos_to_track.json
```
- Lemonfox est prioritaire (profil GPU FP32). Pyannote sert de fallback automatique.

## Checklists
1. **Profil GPU** : `AUDIO_PROFILE=gpu_fp32` (AMP off) pour éviter divergences GPU/CPU.
2. **OOM Handling** : Utiliser `PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32`, `torch.cuda.empty_cache()` entre fichiers en cas de crash.
3. **Import isolé** : charger Lemonfox via `importlib` (`services/lemonfox_audio_service.py`) pour éviter les dépendances Flask.
4. **Success partiel** : poser `AUDIO_PARTIAL_SUCCESS_OK=1` pour ne pas bloquer la pipeline quand un fichier audio échoue.
5. **Logs** : surveiller `logs/step4/*.log` pour `is_speech_present`, vérifier smoothing Lemonfox.

## Résolution incidents
- `ModuleNotFoundError: torch` → réinstaller via `audio_env/bin/pip install -r requirements.txt`.
- Divergences diarisation → vérifier `AUDIO_PROFILE`, repasser en `gpu_fp32`, confirmer `LEMONFOX_SMOOTHING`.
- Fichiers `.mov` → exclure avant STEP4 (cf. systemPatterns Audio).
- Import Pyannote v3 → fallback v2 si pipeline non supporté (`pip install pyannote.audio==2.x`).

## Références
- `memory-bank/systemPatterns.md` section Audio (STEP4).
- `docs/workflow/pipeline/STEP4_ANALYSE_AUDIO.md` pour paramètres détaillés.
