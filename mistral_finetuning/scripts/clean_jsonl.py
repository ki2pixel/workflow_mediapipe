#!/usr/bin/env python3
"""
Script pour nettoyer les fichiers JSONL en gardant seulement les lignes valides
"""

import json
import sys
from pathlib import Path

def clean_jsonl_file(file_path: str):
    """Nettoie un fichier JSONL en gardant seulement les lignes JSON valides"""
    path = Path(file_path)
    if not path.exists():
        print(f"Fichier non trouvé: {file_path}")
        return

    valid_lines = []
    total_lines = 0
    valid_count = 0

    print(f"Nettoyage de {file_path}...")

    with open(path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            total_lines += 1

            if not line:
                continue

            try:
                json.loads(line)
                valid_lines.append(line)
                valid_count += 1
            except json.JSONDecodeError as e:
                print(f"Ligne {line_num} invalide (ignorée): {e}")
                continue

    # Réécrire le fichier avec seulement les lignes valides
    with open(path, 'w', encoding='utf-8') as f:
        for line in valid_lines:
            f.write(line + '\n')

    print(f"Nettoyage terminé: {valid_count}/{total_lines} lignes valides gardées")

def main():
    if len(sys.argv) < 2:
        print("Usage: python clean_jsonl.py <file1.jsonl> [file2.jsonl] ...")
        sys.exit(1)

    for file_path in sys.argv[1:]:
        clean_jsonl_file(file_path)

if __name__ == "__main__":
    main()
