# Pipeline Diagnostics — Environnement & Matériel

> **Objectif** : valider rapidement que les variables `.env`, les environnements virtuels et le matériel sont prêts avant d’exécuter STEP1→STEP7.

## 1. Variables critiques (`.env`)
```bash
python - <<'PY'
from config import settings
from pprint import pprint
keys = [
    'CACHE_ROOT_DIR', 'ARCHIVES_DIR', 'DOWNLOAD_HISTORY_DB_PATH',
    'DRY_RUN_DOWNLOADS', 'AUDIO_PROFILE', 'STEP5_TRACKING_ENGINE',
    'STEP5_ENABLE_GPU', 'STEP5_GPU_ENGINES', 'TRACKING_CPU_WORKERS'
]
config = settings.config
pprint({k: config.get(k) for k in keys})
PY
```
- Confirmer `DRY_RUN_DOWNLOADS=true` en pré-production.
- Vérifier que `CACHE_ROOT_DIR` et `ARCHIVES_DIR` existent et sont montés.

## 2. Venv readiness
| Venv | Commande | Attendu |
| --- | --- | --- |
| `env/` | `env/bin/python -V` | Python 3.10.x |
| `transnet_env/` | `transnet_env/bin/python - <<'PY'\nimport torch; import transnetv2_pytorch\nprint('TransNet OK')\nPY` | Import sans exception |
| `audio_env/` | `audio_env/bin/python - <<'PY'\nimport torch; print(torch.__version__)\nPY` | 1.12.1+cu113 |
| `tracking_env/` | `tracking_env/bin/python - <<'PY'\nimport onnxruntime; print(onnxruntime.get_available_providers())\nPY` | `CUDAExecutionProvider` présent si GPU |
| `eos_env/` (si STEP5 EOS) | `eos_env/bin/python - <<'PY'\nimport eos\nPY` | Pas d’exception |

## 3. Matériel & binaires
```bash
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
ffmpeg -hide_banner | head -n 1
```
- Driver ≥ 515 recommandé.
- `ffmpeg` doit correspondre à la version documentée (`docs/workflow/pipeline/STEP2_CONVERSION_VIDEO.md`).

## 4. SQLite healthcheck
```bash
python - <<'PY'
import sqlite3
conn = sqlite3.connect('download_history.sqlite3')
print(conn.execute('PRAGMA integrity_check;').fetchone())
print(conn.execute('SELECT COUNT(*) FROM download_history;').fetchone())
conn.close()
PY
```
- Résultat attendu `('ok',)`.
- En cas d’échec, restaurer le dernier backup puis relancer la migration JSON→SQLite.

## 5. Checklist finale
- [ ] Toutes les venvs répondent et importent leurs dépendances clés.
- [ ] GPU détecté (`nvidia-smi`) lorsque STEP5 InsightFace ou MediaPipe GPU requis.
- [ ] Variables `.env` concordent avec les profils attendus (CPU vs GPU, DRY_RUN, chemins).
- [ ] `download_history.sqlite3` sain et accessible.
- [ ] Répertoires `CACHE_ROOT_DIR`, `ARCHIVES_DIR`, `logs/step*` existent avec permissions écriture.

> **Astuce** : conserver ce fichier localement pendant les astreintes pour gagner du temps avant un run complet.
