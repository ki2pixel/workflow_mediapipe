#!/usr/bin/env python3
"""
Utility: Add a download URL to the workflow_mediapipe history via CSVService, with normalization.

Usage:
  python scripts/add_url_to_history.py "<url>" ["<timestamp YYYY-MM-DD HH:MM:SS>"]

This script ensures the project root is on sys.path and reports clear outcomes.
"""
import sys
import traceback
from datetime import datetime

# Ensure project root on path
PROJECT_ROOT = "/home/kidpixel/workflow_mediapipe"
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from services.csv_service import CSVService  # type: ignore


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("ERROR: Missing URL.\nUsage: python scripts/add_url_to_history.py '<url>' ['<timestamp YYYY-MM-DD HH:MM:SS>']")
        return 2

    url = argv[1].strip()
    ts = None
    if len(argv) >= 3 and argv[2].strip():
        ts = argv[2].strip()
    else:
        # Use current local time as default timestamp
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        print(f"Adding URL to history (may normalize internally):\n  URL: {url}\n  Timestamp: {ts}")
        ok = CSVService.add_to_download_history_with_timestamp(url, ts)
        print(f"Result: {ok}")
        return 0 if ok else 1
    except Exception as e:
        print("ERROR while adding URL to history:")
        print(e)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
