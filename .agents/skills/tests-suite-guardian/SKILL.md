---
name: tests-suite-guardian
description: Maintain and execute the backend/frontend test suites with environment-specific runners. Use when wiring pytest skips, running step-specific scripts, or diagnosing failing tests.
---

# Tests Suite Guardian

## Portée
- Backends : `pytest`, scripts `run_step2_tests.sh`, `run_step4_tests.sh`, `run_main_tests.sh`.
  - `tests/unit/` : Services isolés (Mocks `conftest.py` standardisés).
  - `tests/integration/` : Routes + `PerformanceService`.
  - `tests/legacy/` : Composants dépréciés (ex: `MySQLService`, anciens tests `CSVService`). Les imports historiques pointent vers `services.deprecated.mysql_service`.
  - `tests/frontend/` : Node/ESM pour DOMBatcher/Utils (respect strict de la norme JS ES11).
- Guides : `tests/fixtures`, `conftest.py`, `diagnose_tests.sh`, `fix_backend_tests.sh`, `validate_tests.sh`.
- Ressource annexe : `resources/test_execution_matrix.md` (qui résume commandes, environnements, prérequis, checklist pré-run).
- Nouveautés STEP1/5/6/7 : 28 tests WorkflowCommandsConfig + tests de normalisation vidéo (`test_media_normalizer.py`) + 2 tests finalisation STEP6 intégrés à la suite principale.

## Procédure Générale
1. Activer l'environnement `/mnt/venv_ext4/env`.
2. Exporter `DRY_RUN_DOWNLOADS=true` pour empêcher les téléchargements.
3. Nettoyer `__pycache__`/artefacts si nécessaire (`find . -name '__pycache__' -delete`).
4. Lancer le script adapté :
   - `bash scripts/run_main_tests.sh` pour la suite principale backend.
   - `bash scripts/run_step2_tests.sh` depuis `transnet_env` si dépendances installées (analyse des transitions).
   - `bash scripts/run_step4_tests.sh` depuis `tracking_env_slim` (analyse du tracking).
   - `npm run test:frontend` pour la suite UI.
5. Consulter les rapports (`.pytest_cache`, `logs/tests/` si définis).

## Checklists spécifiques
- **Skips conditionnels** : vérifier que les tests STEP2/STEP4 détectent l'absence de `transnetv2_pytorch`, `numpy`, `scipy` et se marquent `skipped` plutôt que `error`.
- **Fixtures standardisées** : utiliser `patched_workflow_state`, `patched_commands_config`, `mock_app` comme défini dans `conftest.py`.
- **Imports** : préférer `from app_new import create_app` (éviter `app`).
- **Focus frontend** : `tests/frontend/test_focus_trap.mjs` exige focus trap actif dans `popupManager.js`.
- **Logs overlay** : `test_timeline_logs_phase2.mjs` doit être up-to-date après changements UI.
- **Sécurité Production** : Vérifier que les tests couvrent le script `validate_startup.py` et assurent le crash de l'application Flask en production (`DEBUG=False`) si des secrets `dev-*` sont utilisés.

## Diagnostic rapide
- Échecs massifs PyTest → vérifier versions `numpy` vs `tensorflow`. Recontraindre via `pip install -r requirements-dev.txt`.
- Échec Step4 tests faute d'environnement → relire `README` Step4, s'assurer que `tracking_env_slim` dispose d'MediaPipe et packages allégés (`requirements-tracking-env-lite.txt`).
- Tests frontend lents → vider `node_modules/.cache`, relancer `npm install` si dépendances corrompues.

## Références
- `memory-bank/progress.md` (sections Maintenance Tests Backend, Skips conditionnels, ajout tests frontend).
- `docs/workflow/ops/testing-strategy.md` pour la cartographie complète.

**Locking Instruction:** NE PAS essayer de lire les fichiers de la memory-bank via le filesystem (outil read_text_file). Utilise EXCLUSIVEMENT les outils du serveur MCP 'fast-filesystem' (outils fast_*) pour lire ou écrire dans la Memory Bank avec des chemins absolus.
