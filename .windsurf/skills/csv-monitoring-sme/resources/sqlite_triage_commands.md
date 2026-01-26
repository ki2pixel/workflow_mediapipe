# CSV Monitoring — Requêtes SQLite & Vérifications

> Utiliser `sqlite3 download_history.sqlite3` ou `python - <<'PY'` pour exécuter ces requêtes. Toujours travailler sur une copie en lecture seule pendant le diagnostic.

## 1. Derniers téléchargements Dropbox valides
```sql
SELECT url, status, last_seen_at
FROM download_history
WHERE url LIKE '%dropbox%' OR url LIKE '%workers.dev%'
ORDER BY last_seen_at DESC
LIMIT 20;
```

## 2. URLs non conformes (doivent être ignorées)
```sql
SELECT url, status
FROM download_history
WHERE url NOT LIKE '%dropbox%'
  AND url NOT LIKE '%workers.dev%'
  AND status != 'ignored';
```
- Si des lignes apparaissent → purger et réexécuter la migration JSON→SQLite après correction de `CSVService`.

## 3. Détection de doublons (normalisation incorrecte)
```sql
SELECT normalized_url, COUNT(*)
FROM download_history
GROUP BY normalized_url
HAVING COUNT(*) > 1;
```
- Confirmer que `_normalize_url()` est appliqué avant insertion.

## 4. Vérifier les DRY RUNs
```sql
SELECT url, status, dry_run
FROM download_history
WHERE dry_run = 1
ORDER BY updated_at DESC
LIMIT 10;
```
- Assure que `DRY_RUN_DOWNLOADS=true` n’écrit que des statuts cohérents.

## 5. Statistiques rapides
```sql
SELECT status, COUNT(*)
FROM download_history
GROUP BY status;
```
- Investiguer toute explosion de `failed` ou `pending`.

## 6. Script Python prêt à l’emploi
```bash
python - <<'PY'
import sqlite3
from pathlib import Path
DB = Path('download_history.sqlite3')
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
print('Total entries:', conn.execute('SELECT COUNT(*) FROM download_history').fetchone()[0])
print('\nTop duplicated normalized_url:')
for row in conn.execute('''
    SELECT normalized_url, COUNT(*) as c
    FROM download_history
    GROUP BY normalized_url
    HAVING c > 1
    ORDER BY c DESC
    LIMIT 10
'''):
    print('-', row['normalized_url'], row['c'])
conn.close()
PY
```

> Ajouter les résultats significatifs dans le ticket d’incident pour tracer la chronologie et les corrections appliquées.
