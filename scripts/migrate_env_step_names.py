#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Migration du fichier `.env` vers le schéma de numérotation v2 des variables d'étape.

Contexte
--------
La suppression de l'étape de conversion a décalé la numérotation du pipeline.
Les variables `STEPn_*` suivent désormais la numérotation actuelle :

    schéma 1 (historique)          schéma 2 (actuel)
    STEP3_*  transitions           STEP2_*  transitions
    STEP4_*  audio                 STEP3_*  audio
    STEP5_*  tracking              STEP4_*  tracking
    STEP6_*  réduction JSON        STEP5_*  réduction JSON
    STEP7_*  pré-traitement AE     STEP6_*  pré-traitement AE
    USE_OPENCV5_STEP2 / STEP5      USE_OPENCV5_STEP2 / STEP4

Un `.env` resté en schéma 1 serait interprété de travers (par exemple
`STEP3_ENABLE_CORAL_TPU`, historiquement l'audio, désignerait le tracking).
Ce script renomme donc les clés du fichier, dans l'ordre croissant pour que
chaque espace de noms soit libéré avant d'être réutilisé, et appose le
marqueur `ENV_STEP_SCHEMA=2`.

Usage
-----
    python scripts/migrate_env_step_names.py [--env-file .env] [--dry-run] [--force]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_ENV_FILE = BASE_DIR / ".env"

SCHEMA_MARKER_KEY = "ENV_STEP_SCHEMA"
SCHEMA_VERSION = "2"

STEP_KEY_PATTERN = re.compile(r'^(?P<indent>\s*)(?P<key>STEP([3-7])_[A-Z0-9_]*)')
OPENCV5_KEY_PATTERN = re.compile(r'^(?P<indent>\s*)(?P<key>USE_OPENCV5_STEP([3-7]))\s*$')


def renumber_key(line: str) -> tuple[str, str | None]:
    """Renomme la clé d'une ligne `CLE=valeur` si elle appartient au schéma 1."""
    if line.lstrip().startswith("#") or "=" not in line:
        return line, None

    key_part, _, value_part = line.partition("=")
    match = STEP_KEY_PATTERN.match(key_part)
    if match:
        old_key = match.group("key")
        new_key = f"STEP{int(match.group(3)) - 1}{old_key[len('STEP') + 1:]}"
        return f"{match.group('indent')}{new_key}={value_part}", f"{old_key} -> {new_key}"

    match = OPENCV5_KEY_PATTERN.match(key_part.strip())
    if match:
        old_key = match.group("key")
        new_key = f"USE_OPENCV5_STEP{int(match.group(3)) - 1}"
        return f"{match.group('indent')}{new_key}={value_part}", f"{old_key} -> {new_key}"

    return line, None


def migrate(env_file: Path, dry_run: bool = False, force: bool = False) -> int:
    if not env_file.exists():
        print(f"❌ Fichier introuvable : {env_file}")
        return 1

    lines = env_file.read_text(encoding="utf-8").splitlines()
    has_marker = any(
        line.split("=", 1)[0].strip() == SCHEMA_MARKER_KEY
        and line.split("=", 1)[1].strip().strip('"').strip("'") == SCHEMA_VERSION
        for line in lines
        if "=" in line
    )

    if has_marker and not force:
        print(f"✅ {env_file} est déjà en schéma {SCHEMA_VERSION} — rien à faire.")
        return 0

    migrated_lines: list[str] = []
    renames: list[str] = []
    for line in lines:
        new_line, rename = renumber_key(line)
        migrated_lines.append(new_line)
        if rename:
            renames.append(rename)

    if not has_marker:
        migrated_lines.append(f"{SCHEMA_MARKER_KEY}={SCHEMA_VERSION}")

    print(f"{len(renames)} variable(s) à renommer :")
    for rename in renames:
        print(f"  - {rename}")

    if dry_run:
        print("(mode --dry-run : aucun fichier modifié)")
        return 0

    backup = env_file.with_name(f"{env_file.name}.bak-{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(env_file, backup)
    env_file.write_text("\n".join(migrated_lines) + "\n", encoding="utf-8")
    print(f"✅ {env_file} migré (sauvegarde : {backup.name})")
    print(f"   Marqueur {SCHEMA_MARKER_KEY}={SCHEMA_VERSION} apposé.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE, help="Chemin du fichier .env")
    parser.add_argument("--dry-run", action="store_true", help="Afficher les renommages sans écrire")
    parser.add_argument("--force", action="store_true", help="Migrer même si le marqueur est déjà présent")
    args = parser.parse_args()

    return migrate(args.env_file, dry_run=args.dry_run, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
