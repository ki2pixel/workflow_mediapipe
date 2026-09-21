#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility: audit the R2 / worker proxy objects referenced by the webhook.

Some .zip archives are missing on the Cloudflare side even though the mail
carries a valid Dropbox link. This script HEADs every `r2_url` published by the
webhook and reports which objects are absent, so gaps can be spotted before a
download fails at startup.

Read-only: it never downloads a payload and never writes to the history.

Usage:
  python scripts/check_r2_objects.py [--json] [--limit N] [--show-ok]

Exit codes:
  0 - every referenced object answered
  1 - at least one object is missing (404/410)
  2 - the webhook could not be reached
"""
import argparse
import json
import sys
import traceback

from pathlib import Path

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env before importing the config module: WEBHOOK_JSON_URL lives there
try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / '.env')
except ImportError:
    pass

from services.csv_service import CSVService  # type: ignore
from services.download_service import DownloadService  # type: ignore
from services.filesystem_service import FilesystemService  # type: ignore
from services.webhook_service import fetch_records  # type: ignore

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept-Encoding': 'identity',
}


def _probe(record: dict, history: set) -> dict:
    """HEAD a single r2_url and classify the answer."""
    url = record.get('url') or ''
    source_url = record.get('fallback_url') or record.get('source_url') or ''
    probe = DownloadService._probe_remote(url, HEADERS, 'R2-CHECK')
    status_code = probe.status_code

    if status_code is None:
        state = 'UNREACHABLE'
    elif status_code in (404, 410):
        state = 'MISSING'
    elif status_code in (401, 403):
        state = 'FORBIDDEN'
    elif status_code >= 400:
        state = 'ERROR'
    else:
        state = 'OK'

    normalized_r2 = CSVService._normalize_url(url) if url else ''
    normalized_source = CSVService._normalize_url(source_url) if source_url else ''
    already_downloaded = bool(
        (normalized_r2 and normalized_r2 in history)
        or (normalized_source and normalized_source in history)
    )

    return {
        'state': state,
        'pending': not already_downloaded,
        'status_code': status_code,
        'filename': record.get('original_filename') or '',
        'r2_url': url,
        'source_url': source_url,
        'content_length': probe.content_length,
        'content_type': probe.content_type,
        'error': probe.error,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Audit R2/worker objects referenced by the webhook")
    parser.add_argument('--json', action='store_true', help="Output the report as JSON")
    parser.add_argument('--limit', type=int, default=0, help="Only check the N most recent records")
    parser.add_argument('--show-ok', action='store_true', help="Also list reachable objects")
    args = parser.parse_args(argv[1:])

    try:
        records = fetch_records()
    except Exception as e:
        print(f"ERROR: unable to fetch webhook records: {e}")
        traceback.print_exc()
        return 2

    if records is None:
        print("ERROR: webhook unreachable (no records returned)")
        return 2

    r2_records = [row for row in records if '/dropbox/' in (row.get('url') or '')]
    if args.limit and args.limit > 0:
        r2_records = r2_records[-args.limit:]

    try:
        history = CSVService.get_download_history()
    except Exception as e:
        print(f"WARNING: unable to read the download history ({e}): pending detection disabled")
        history = set()

    report = [_probe(record, history) for record in r2_records]
    unavailable_states = {'MISSING', 'FORBIDDEN', 'ERROR', 'UNREACHABLE'}
    unavailable = [entry for entry in report if entry['state'] in unavailable_states]
    # Only objects that are still awaited matter: older R2 copies are expected
    # to be gone once the archive has been downloaded from Dropbox.
    pending_unavailable = [entry for entry in unavailable if entry['pending']]

    if args.json:
        print(json.dumps({
            'total': len(report),
            'problems': unavailable,
            'pending_problems': pending_unavailable,
            'entries': report,
        }, indent=2))
        return 1 if pending_unavailable else 0

    for entry in report:
        if entry['state'] == 'OK' and not args.show_ok:
            continue
        size = FilesystemService.format_bytes_human(entry['content_length']) if entry['content_length'] else 'n/a'
        label = entry['filename'] or '(sans nom)'
        scope = 'EN ATTENTE' if entry['pending'] else 'déjà traité'
        print(f"{entry['state']:<11} {label:<28} {size:>10}  [{scope}]  {entry['r2_url']}")
        if entry['state'] != 'OK':
            print(f"             └─ status={entry['status_code']} dropbox={entry['source_url'] or 'n/a'}")

    print()
    print(f"{len(pending_unavailable)} objet(s) manquant(s) parmi les archives en attente")
    print(f"{len(unavailable)} objet(s) indisponible(s) / {len(report)} enregistrement(s) vérifié(s)")
    return 1 if pending_unavailable else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
