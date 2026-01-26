---
name: tests-suite-guardian
description: Maintain and execute the backend/frontend test suites with environment-specific runners. Use when wiring pytest skips, running step-specific scripts, or diagnosing failing tests.
---

# Tests Suite Guardian

## Portée
- Backends : `pytest`, scripts `run_step3_tests.sh`, `run_step5_tests.sh`, `run_main_tests.sh`.
- Frontend : `npm run test:frontend` (Node/ESM tests : DOMBatcher, logs overlay, Step Details, focus trap).
- Guides : `tests/fixtures`, `conftest.py`, `diagnose_tests.sh`, `fix_backend_tests.sh`, `validate_tests.sh`.
- Ressource annexe : `resources/test_execution_matrix.md` (qui résume commandes, environnements, pré-requis, checklist pré-run).

## Procédure Générale
1. Activer l’environnement `/mnt/venv_ext4/env`.
2. Exporter `DRY_RUN_DOWNLOADS=true` pour empêcher les téléchargements.
3. Nettoyer `__pycache__`/artefacts si nécessaire (`find . -name '__pycache__' -delete`).
4. Lancer le script adapté :
   - `bash scripts/run_main_tests.sh` pour la suite principale backend.
   - `bash scripts/run_step3_tests.sh` depuis `transnet_env` si dépendances installées.
   - `bash scripts/run_step5_tests.sh` depuis `tracking_env`.
   - `npm run test:frontend` pour la suite UI.
5. Consulter les rapports (`.pytest_cache`, `logs/tests/` si définis).

## Checklists spécifiques
- **Skips conditionnels** : vérifier que les tests STEP3/STEP5 détectent l’absence de `transnetv2_pytorch`, `numpy`, `scipy` et se marquent `skipped` plutôt que `error`.
- **Fixtures standardisées** : utiliser `patched_workflow_state`, `patched_commands_config`, `mock_app` comme défini dans `conftest.py`.
- **Imports** : préférer `from app_new import create_app` (éviter `app`).
- **Focus frontend** : `tests/frontend/test_focus_trap.mjs` exige focus trap actif dans `popupManager.js`.
- **Logs overlay** : `test_timeline_logs_phase2.mjs` doit être up-to-date après changements UI.

## Diagnostic rapide
- Échecs massifs PyTest → vérifier versions `numpy` vs `tensorflow`. Recontraindre via `pip install -r requirements-dev.txt`.
- Échec Step5 tests faute d’environnement → relire `README` Step5, s’assurer que `tracking_env` dispose d’ONNX Runtime.
- Tests frontend lents → vider `node_modules/.cache`, relancer `npm install` si dépendances corrompues.

## Références
- `memory-bank/progress.md` (sections Maintenance Tests Backend, Skips conditionnels, ajout tests frontend).
- `docs/workflow/technical/TESTING_STRATEGY.md` pour la cartographie complète.
