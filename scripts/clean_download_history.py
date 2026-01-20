#!/usr/bin/env python3
"""
Clean Download History
Normalizes and deduplicates the download_history.json file to remove URL variants.

This script applies the improved URL normalization logic to remove duplicate entries
caused by double-encoded sequences (e.g., amp%3Bdl=0) and other URL variations.

Usage:
    python scripts/clean_download_history.py [--dry-run]

Options:
    --dry-run    Show what would be cleaned without modifying the file
"""

import sys
import json
import argparse
from pathlib import Path

# Add parent directory to path to import services
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.csv_service import CSVService
from config.settings import config


def main():
    parser = argparse.ArgumentParser(description='Clean and deduplicate download history')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying them')
    args = parser.parse_args()

    history_file = config.BASE_PATH_SCRIPTS / 'download_history.json'
    backup_file = history_file.with_suffix('.json.bak')

    if not history_file.exists():
        print(f"✗ History file not found: {history_file}")
        return 1

    print(f"📋 Loading download history from: {history_file}")
    
    # Load existing history
    with open(history_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"   Found {len(data)} entries")

    # Build normalized map
    url_map = {}  # normalized_url -> (original_url, timestamp)
    duplicates_found = []

    for item in data:
        if not isinstance(item, dict):
            continue
        
        original_url = item.get('url', '')
        timestamp = item.get('timestamp', '')
        
        if not original_url:
            continue

        normalized_url = CSVService._normalize_url(original_url)
        
        if normalized_url in url_map:
            # Duplicate found - keep earliest timestamp
            existing_ts = url_map[normalized_url][1]
            if timestamp < existing_ts:
                duplicates_found.append((url_map[normalized_url][0], existing_ts))
                url_map[normalized_url] = (original_url, timestamp)
            else:
                duplicates_found.append((original_url, timestamp))
        else:
            url_map[normalized_url] = (original_url, timestamp)

    # Build cleaned history
    cleaned_data = []
    for normalized_url, (orig_url, ts) in sorted(url_map.items(), key=lambda x: x[1][1]):
        cleaned_data.append({
            'url': normalized_url,  # Use normalized URL
            'timestamp': ts
        })

    print(f"\n📊 Cleaning summary:")
    print(f"   Original entries: {len(data)}")
    print(f"   Unique entries: {len(cleaned_data)}")
    print(f"   Duplicates removed: {len(duplicates_found)}")

    if duplicates_found:
        print(f"\n🔍 Duplicate URLs found (showing first 10):")
        for orig_url, ts in duplicates_found[:10]:
            print(f"   - {orig_url[:80]}... ({ts})")
        if len(duplicates_found) > 10:
            print(f"   ... and {len(duplicates_found) - 10} more")

    if args.dry_run:
        print(f"\n🔸 DRY RUN: No changes were made")
        print(f"   Run without --dry-run to apply changes")
        return 0

    if len(cleaned_data) == len(data):
        print(f"\n✓ No duplicates found - history is already clean")
        return 0

    # Create backup
    print(f"\n💾 Creating backup: {backup_file}")
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # Write cleaned history
    print(f"✍️  Writing cleaned history: {history_file}")
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Download history cleaned successfully")
    print(f"   Removed {len(duplicates_found)} duplicate entries")
    print(f"   Backup saved to: {backup_file}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
