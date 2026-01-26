---
name: pipeline-diagnostics
description: Checklists and scripts to validate env vars, venv availability, and hardware readiness before launching Workflow MediaPipe steps (STEP1-STEP7). Use when pre-run sanity checks or root-cause hunts point to configuration drift.
---

# Pipeline Diagnostics Skill

## Quick Start
1. Lire `.env` via `config/settings.py` (`python - <<'PY' ...`) pour afficher les variables critiques (`CACHE_ROOT_DIR`, `STEP5_*`, `DOWNLOAD_HISTORY_DB_PATH`).
2. Valider l'existence des venv spécialisés (`env/`, `transnet_env/`, `audio_env/`, `tracking_env/`, `eos_env/`).
3. Vérifier les binaires GPU/CPU (`nvidia-smi`, `ffmpeg -version`, `onnxruntime_test`) selon l'étape cible.
4. Consulter `resources/env_health_checklist.md` pour dérouler l'audit complet (commandes `.env`, imports venv, `nvidia-smi`, PRAGMA SQLite) avant chaque run majeur.

## Procédure Complète
1. **Sanity `.env`**
   - Charger via `python3 config/settings.py --print` (si script dispo) ou `python - <<'PY'` pour inspecter `config.settings.config`.
   - Contrôler : chemins cache, flags `DRY_RUN_DOWNLOADS`, `STEP5_ENABLE_GPU`, `AUDIO_PROFILE`, URLs webhook.
2. **Venv Readiness**
   - `ls env/bin/python transnet_env/bin/python audio_env/bin/python tracking_env/bin/python eos_env/bin/python`.
   - `python -V` dans chaque venv (ex: `env/bin/python -V`).
3. **Hardware & Drivers**
   - `nvidia-smi` (GPU dispo, driver version ≥ 515).
   - `ffmpeg -hide_banner | head -n 1` pour STEP2.
   - `tracking_env/bin/python - <<'PY'` pour importer `onnxruntime`, `mediapipe`, `opencv`.
4. **Filesystem & Permissions**
   - Vérifier `CACHE_ROOT_DIR`, `ARCHIVES_DIR`, `logs/stepX` existent et sont accessibles (`FilesystemService` doit être utilisé côté code; ici on vérifie les répertoires).
5. **SQLite Health**
   - `python - <<'PY'` pour ouvrir `download_history.sqlite3`, lancer `PRAGMA integrity_check;`.

## Résolution Rapide
- Échec import `torch`/`pyannote` STEP4 → relancer install via `audio_env/bin/pip install -r requirements.txt`.
- `tracking_env` manque `onnxruntime` → `tracking_env/bin/pip install onnxruntime-gpu==1.16.3` puis re-tester.
- Variables `.env` incohérentes → éditer `.env`, recharger via `config/settings.py`.

## Références
- `codingstandards.md` (rappel : utiliser les venv spécialisés).
- `memory-bank/productContext.md` (section Pipeline de Traitement) pour cartographier les étapes.
