---
name: csv-monitoring-sme
description: Manage CSVService monitoring, download_history SQLite, and Dropbox-only policies. Use when diagnosing webhook ingestion, migrations, or URL normalization.
---

# CSV Monitoring SME

## Préparation
1. Lire `.env` : `DOWNLOAD_HISTORY_DB_PATH`, `DRY_RUN_DOWNLOADS`, `CSV_MONITORING_INTERVAL`, URLs webhook.
2. Vérifier la présence de `download_history.sqlite3` et des scripts `scripts/migrate_download_history_to_sqlite.py`.
3. Consulter `services/csv_service.py` et `services/download_history_repository.py` pour l’API actuelle.
4. Pour un diagnostic rapide, ouvrir `resources/sqlite_triage_commands.md` (requêtes toutes prêtes pour détecter doublons, URLs non conformes, DRY RUNs, stats).

## Workflows clés
### 1. Migration JSON → SQLite
```bash
python scripts/migrate_download_history_to_sqlite.py \
  --input archives/download_history.json \
  --output download_history.sqlite3 \
  --backup
```
- Vérifier `PRAGMA integrity_check;` après migration.

### 2. Diagnostic Monitoring
1. Exécuter `python - <<'PY'` pour inspecter `WorkflowState.downloads`.
2. Consulter `logs/app.log` pour les entrées `CSVService`.
3. Vérifier `download_history` via `sqlite3 download_history.sqlite3 "SELECT url, status, last_seen FROM download_history LIMIT 20;"`.
4. Confirmer la politique Dropbox-only : `_is_dropbox_like_url(url)` doit être vraie pour créer un téléchargement.

### 3. DRY-RUN / Tests
- Lancer `pytest tests/integration/test_csv_dry_run.py tests/integration/test_csv_monitor_no_retrigger.py` (depuis `/mnt/venv_ext4/env`).
- Activer `DRY_RUN_DOWNLOADS=true` pour éviter les téléchargements réels.

## Checklists rapides
- **URLs non-HTTP** : rejetées (ftp/file). Vérifier `CSVService._check_csv_for_downloads`.
- **Entrées virtuelles** : supprimées (`manual_open` n’existe plus). Toute entrée doit correspondre à un téléchargement réel.
- **Normalisation** : `_normalize_url()` appliqué avant insertion SQLite → éviter doublons.
- **Worker** : `execute_csv_download_worker()` n’écrit dans l’historique qu’en cas de succès ou DRY_RUN.

## Résolution incidents
- Historique corrompu → relancer migration depuis archive JSON, ou restaurer backup sqlite.
- Téléchargements en boucle → vérifier `download_history_repository.upsert_many()` (timestamp mis à jour) + `CSVMonitorService` intervalle.
- URL FromSmash/SwissTransfer visibles → confirmer qu’elles sont ignorées côté CSV (sinon purger `download_history`).

## Références
- `memory-bank/decisionLog.md` (sections migration SQLite et politique Dropbox-only).
- `docs/workflow/monitoring/CSV_DOWNLOADS_MANAGEMENT.md` (si présent) pour procédures complètes.
- `resources/sqlite_triage_commands.md` pour copier/coller les requêtes SQLite et le script Python de synthèse.
