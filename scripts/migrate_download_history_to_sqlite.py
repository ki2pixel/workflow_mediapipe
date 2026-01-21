#!/usr/bin/env python3
"""Migrate legacy download_history.json entries into the SQLite repository.

This script is safe to run multiple times. It reads the structured JSON history
(if present), normalizes URLs, converts timestamps to the canonical local time
format, then upserts them into the SQLite database used by CSVService.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import config  # noqa: E402
from services.csv_service import CSVService  # noqa: E402
from services.download_history_repository import download_history_repository  # noqa: E402


def _normalize_ts_for_db(raw_ts: str) -> str:
    from datetime import datetime, timezone

    if not raw_ts:
        return ""
    ts = str(raw_ts).strip()
    if not ts:
        return ""
    try:
        parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if parsed.tzinfo:
            return parsed.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return ts


def _load_legacy_entries(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open('r', encoding='utf-8') as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        return []
    entries: List[Dict[str, str]] = []
    if data and isinstance(data[0], dict):
        for item in data:
            if not isinstance(item, dict):
                continue
            url = item.get('url')
            if not url:
                continue
            entries.append({
                'url': CSVService._normalize_url(str(url)),
                'timestamp': _normalize_ts_for_db(str(item.get('timestamp') or '')),
            })
        return entries
    for raw in data:
        if not isinstance(raw, str):
            continue
        entries.append({'url': CSVService._normalize_url(raw), 'timestamp': ''})
    return entries


def migrate_download_history(legacy_path: Path, dry_run: bool) -> Tuple[int, int]:
    entries = _load_legacy_entries(legacy_path)
    if not entries:
        return 0, 0

    normalized: List[Tuple[str, str]] = []
    for item in entries:
        url = item.get('url')
        if not url:
            continue
        ts = item.get('timestamp') or ''
        normalized.append((url, ts))

    if dry_run:
        return len(entries), len(normalized)

    download_history_repository.upsert_many(normalized)
    return len(entries), len(normalized)


def backup_file(path: Path) -> Path:
    backup = path.with_suffix(path.suffix + '.bak')
    shutil.copy2(path, backup)
    return backup


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Migrer download_history.json vers SQLite.',
    )
    parser.add_argument(
        '--legacy-file',
        type=Path,
        default=config.BASE_PATH_SCRIPTS / 'download_history.json',
        help='Chemin vers le fichier download_history.json (défaut: BASE_PATH_SCRIPTS).',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Ne rien écrire en base, afficher uniquement le nombre d’entrées détectées.',
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Ne pas créer de sauvegarde .bak du fichier legacy.',
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    legacy_file = args.legacy_file.resolve()
    if not legacy_file.exists():
        print(f"✗ Aucun fichier legacy trouvé : {legacy_file}")
        return 0

    CSVService.initialize()

    if not args.dry_run and not args.no_backup:
        backup = backup_file(legacy_file)
        print(f"💾 Sauvegarde créée : {backup}")

    total_raw, total_upsert = migrate_download_history(legacy_file, args.dry_run)

    if args.dry_run:
        print(f"[DRY-RUN] {total_raw} entrées détectées, {total_upsert} seront insérées.")
    else:
        print(f"✓ Migration terminée : {total_upsert} URL insérées/actualisées.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
