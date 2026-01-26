# Suites de tests — Matrice d’exécution

| Suite | Commande | Environnement | Pré-requis | Résultat attendu |
| --- | --- | --- | --- | --- |
| Backend principale | `bash scripts/run_main_tests.sh` | `/mnt/venv_ext4/env` | `DRY_RUN_DOWNLOADS=true`, dépendances `requirements-dev.txt` |  ✅ PyTest (majorité) + skips documentés STEP3/STEP5 |
| STEP3 dédiée | `bash scripts/run_step3_tests.sh` | `transnet_env` | `transnetv2_pytorch`, GPU ou CPU compatible | Tests marqués `skip` si dépendances manquantes |
| STEP5 dédiée | `bash scripts/run_step5_tests.sh` | `tracking_env` | `onnxruntime`, `opencv`, variables STEP5 alignées | Logs GPU/CPU affichés, erreurs converties en skips si libs absentes |
| Frontend | `npm run test:frontend` | Node 18 LTS | `node_modules` installés, `DOMBatcher` bundlé | Tests DOMBatcher, focus trap, Timeline, logs overlay |
| Diagnostics backend | `bash scripts/diagnose_tests.sh` | `/mnt/venv_ext4/env` | Utilitaires `jq`, `grep` disponibles | Rapport JSON sur tests flaky/skip/xfail |
| Correctifs automatisés | `bash scripts/fix_backend_tests.sh` | `/mnt/venv_ext4/env` | Accès écriture au repo | Nettoyage `__pycache__`, reinstall dépendances ciblées |

## Pré-checklist
- [ ] `pip install -r requirements-dev.txt` exécuté dans l’env de base.
- [ ] `npm install` à jour (front).
- [ ] `pytest.ini` non modifié localement (sinon reset). 
- [ ] Variables `TRANSNET_ENV_PYTHON`, `TRACKING_ENV_PYTHON` pointent vers les bons interpréteurs.
- [ ] Logs de run précédents vidés (`rm -rf logs/tests/*` si volumineux).

## Astuces
- Utiliser `PYTEST_ADDOPTS="-n auto"` uniquement si la suite ne dépend pas des environnements spécialisés.
- Documenter tout nouveau `skip` dans `tests/README.md` + Memory Bank (`progress.md`).
