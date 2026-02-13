---
description: csv-monitoring-sme skill migrated from Windsurf as contextual rules
globs: 
  - "**/*.{py,js,md}"
alwaysApply: true
---

# CSV Monitoring SME

## Préparation

1. Lire `.env` : `DOWNLOAD_HISTORY_DB_PATH`, `DRY_RUN_DOWNLOADS`, `CSV_MONITORING_INTERVAL`, URLs webhook.
2. Vérifier la présence de `download_history.sqlite3` et des scripts `scripts/migrate_download_history_to_sqlite.py`.
3. Consulter `services/csv_service.py` et `services/download_history_repository.py` pour l'API actuelle.
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

#### Commandes SQLite d'Audit
```bash
# Inspection base complète
sqlite3 download_history.sqlite3 "PRAGMA integrity_check;"

# Statistiques générales
sqlite3 download_history.sqlite3 "
SELECT 
  COUNT(*) as total_downloads,
  COUNT(DISTINCT url) as unique_urls,
  MIN(created_at) as oldest_download,
  MAX(created_at) as newest_download
FROM download_history;
"

# Downloads par statut
sqlite3 download_history.sqlite3 "
SELECT 
  status,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM download_history), 2) as percentage
FROM download_history 
GROUP BY status;
"

# URLs suspectes (doublons)
sqlite3 download_history.sqlite3 "
SELECT 
  url,
  COUNT(*) as download_count,
  GROUP_CONCAT(status, ', ') as statuses
FROM download_history 
GROUP BY url 
HAVING COUNT(*) > 1
ORDER BY download_count DESC;
"
```

#### Validation des URLs
```bash
# URLs non conformes
sqlite3 download_history.sqlite3 "
SELECT url, status, error_message
FROM download_history 
WHERE url NOT LIKE 'http://%' 
   OR url NOT LIKE 'https://%'
   OR url LIKE '%..%'
   OR url LIKE '%file://%'
;

# Downloads DRY RUN
sqlite3 download_history.sqlite3 "
SELECT url, created_at, status
FROM download_history 
WHERE status = 'dry_run'
ORDER BY created_at DESC;
"
```

### 3. Monitoring en Temps Réel
```bash
# Surveillance webhook
tail -f logs/webhook_receiver.log | grep -E "(POST|download|ERROR|WARN)"

# Base de données en direct
sqlite3 download_history.sqlite3 "
SELECT 
  datetime(created_at, 'unixepoch') as timestamp,
  url,
  status,
  file_size,
  download_time_seconds
FROM download_history 
WHERE created_at > datetime('now', '-1 hour')
ORDER BY created_at DESC;
"
```

## Configuration CSVService

### Variables d'Environnement
```bash
# .env recommandé
DOWNLOAD_HISTORY_DB_PATH=/path/to/download_history.sqlite3
CSV_MONITORING_INTERVAL=300  # secondes
DRY_RUN_DOWNLOADS=false
CSV_DROPBOX_ONLY=false
CSV_MAX_FILE_SIZE_MB=500
```

### Validation des Fichiers
```bash
# Vérifier intégrité SQLite
python3 - <<'PY'
import sqlite3
try:
    conn = sqlite3.connect('download_history.sqlite3')
    result = conn.execute("PRAGMA integrity_check").fetchone()
    print(f"SQLite integrity: {result[0]}")
    conn.close()
except Exception as e:
    print(f"SQLite error: {e}")
PY'

# Vérifier permissions
test -r download_history.sqlite3 && echo "SQLite writable" || echo "SQLite ERROR: not writable"
```

## Dépannage Commun

### Erreurs SQLite
| Erreur | Cause | Solution |
|---|---|---|
| `database is locked` | Processus concurrent | Attendre fin du processus, utiliser `timeout` |
| `no such table` | Migration incomplète | Relancer migration |
| `disk I/O error` | Permissions disque | `chmod 666` sur fichier |

### Erreurs URLs
```bash
# Normalisation URLs
python3 - <<'PY'
import re
from urllib.parse import urlparse

def normalize_url(url):
    # Supprimer fragments
    parsed = urlparse(url)
    clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    # Validation basique
    if not re.match(r'^https?://', clean_url):
        raise ValueError("Invalid URL scheme")
    
    return clean_url

# Test URLs
test_urls = [
    "http://example.com/file.mp4",
    "https://example.com/path/video.mp4",
    "ftp://invalid.com/file.mp4"
]

for url in test_urls:
    try:
        normalized = normalize_url(url)
        print(f"✓ {url} -> {normalized}")
    except Exception as e:
        print(f"✗ {url} -> ERROR: {e}")
PY'
```

## Scripts d'Automatisation

### Backup Automatique
```bash
#!/bin/bash
# backup_csv_data.sh

DB_PATH="/path/to/download_history.sqlite3"
BACKUP_DIR="/path/to/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Créer backup
sqlite3 $DB_PATH ".backup $BACKUP_DIR/csv_backup_$TIMESTAMP.db"

# Nettoyer anciens backups (garder 7 jours)
find $BACKUP_DIR -name "csv_backup_*.db" -mtime +7 -delete

echo "Backup completed: csv_backup_$TIMESTAMP.db"
```

### Monitoring par Email
```bash
# Rapport quotidien
sqlite3 download_history.sqlite3 "
SELECT 
  DATE(created_at) as date,
  COUNT(*) as downloads,
  COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful,
  COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
FROM download_history 
WHERE DATE(created_at) = DATE('now', 'localtime')
GROUP BY DATE(created_at);
" | mail -s "CSV Daily Report" admin@example.com
```

## Validation Checklist

### Sécurité
- [ ] URLs validées et normalisées
- [ ] Taille fichiers limitée (`CSV_MAX_FILE_SIZE_MB`)
- [ ] Permissions base de données sécurisées
- [ ] Logs d'audit activés

### Performance
- [ ] Index base de données optimisés
- [ ] Monitoring interval configurable
- [ ] Timeout downloads gérés

### Fiabilité
- [ ] Backups automatiques
- [ ] Intérité SQLite vérifiée
- [ ] Gestion erreurs robuste

Utilisez ce prompt en tapant `/csv-monitoring-sme` dans Continue.
