# STEP4 Audio — GPU & Pipeline Triage

## 1. Vérifications rapides
- `nvidia-smi --query-gpu=name,driver_version,memory.used,memory.total --format=csv` → confirmer driver ≥ 515, VRAM disponible > 4 Go.
- `audio_env/bin/python - <<'PY'` pour valider torch/cuDNN :
```python
import torch
print('Torch:', torch.__version__)
print('CUDA available:', torch.cuda.is_available())
print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')
PY
```
- Valider `.env` : `AUDIO_PROFILE`, `LEMONFOX_*`, `PYANNOTE_*`, `AUDIO_PARTIAL_SUCCESS_OK`.

## 2. Profil GPU FP32 (recommandé)
```bash
export AUDIO_PROFILE=gpu_fp32
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32
```
- Désactive l’AMP pour éviter les divergences GPU/CPU.
- Si OOM persiste → réduire le batch Lemonfox (`LEMONFOX_BATCH_SIZE=1`).

## 3. Script de smoke test
```bash
audio_env/bin/python workflow_scripts/step4/run_audio_analysis_lemonfox.py \
  --log_dir logs/step4 \
  --input sound-design/smoke_tests/lemonfox_smoke.json \
  --max_files 1
```
- Utiliser un fichier court pour vérifier la stack sans consommer tout le pipeline.

## 4. Analyse des logs
- `grep -n "AUDIO PROFILE" logs/step4/*.log` → confirme profil appliqué.
- `grep -n "Fallback Pyannote" logs/step4/*.log` → vérifier les transitions Lemonfox → Pyannote.
- `grep -n "OOM" logs/step4/*.log` → coupler avec `PYTORCH_CUDA_ALLOC_CONF`.

## 5. Actions correctives
| Symptôme | Action |
| --- | --- |
| `ModuleNotFoundError: torch` | `audio_env/bin/pip install -r requirements.txt` |
| Divergences `is_speech_present` | Forcer `AUDIO_PROFILE=gpu_fp32`, vider caches (`torch.cuda.empty_cache()`) |
| `.mov` non supportés | Exclure du `videos_to_track.json` (cf. systemPatterns) |
| Import Pyannote v3 incompatible | `audio_env/bin/pip install "pyannote.audio<3"` puis relancer |

> Documenter chaque ajustement (profil, batch, fallback) dans le ticket incident + Memory Bank si décision pérenne.
