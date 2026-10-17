#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Télécharge le sous-ensemble dev de VoxConverse (audio + annotations RTTM).

Les archives sont conservées dans ``scratch/bench_step3_der/voxconverse`` afin
de pouvoir relancer le benchmark sans retélécharger 2 Go.

Exemple :
    python3 scripts/fetch_voxconverse_dev.py
    python3 scripts/fetch_voxconverse_dev.py --force
"""

import argparse
import sys
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEST = PROJECT_ROOT / "scratch" / "bench_step3_der" / "voxconverse"
DEV_WAV_URL = "https://www.robots.ox.ac.uk/~vgg/data/voxconverse/data/voxconverse_dev_wav.zip"
REPO_ZIP_URL = "https://codeload.github.com/joonson/voxconverse/zip/refs/heads/master"
WAV_ARCHIVE = "voxconverse_dev_wav.zip"
REPO_ARCHIVE = "voxconverse_repo.zip"
PROGRESS_STEP = 128 * 1024 * 1024


def download(url: str, destination: Path) -> None:
    """Télécharge une archive avec progression (reprise non supportée)."""
    if destination.exists() and destination.stat().st_size > 0:
        print(f"Archive déjà présente : {destination.name} ({destination.stat().st_size / 1e9:.2f} Go)")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    print(f"Téléchargement de {url} -> {destination.name}")

    with urllib.request.urlopen(url) as response, open(temporary, "wb") as output:
        total = int(response.headers.get("Content-Length") or 0)
        downloaded = 0
        next_marker = PROGRESS_STEP
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            downloaded += len(chunk)
            if downloaded >= next_marker:
                if total:
                    print(f"  {downloaded / 1e9:.2f} / {total / 1e9:.2f} Go", flush=True)
                else:
                    print(f"  {downloaded / 1e9:.2f} Go", flush=True)
                next_marker += PROGRESS_STEP

    temporary.replace(destination)
    print(f"  terminé : {destination.stat().st_size / 1e9:.2f} Go")


def extract_members(archive: Path, destination: Path, keep) -> int:
    """Extrait les membres sélectionnés (aplatis dans ``destination``)."""
    destination.mkdir(parents=True, exist_ok=True)
    extracted = 0
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            if member.is_dir() or not keep(member.filename):
                continue
            target = destination / Path(member.filename).name
            with bundle.open(member) as source, open(target, "wb") as output:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
            extracted += 1
    return extracted


def main() -> int:
    parser = argparse.ArgumentParser(description="Téléchargement du corpus VoxConverse dev")
    parser.add_argument("--dest", default=str(DEFAULT_DEST), help="Répertoire de destination")
    parser.add_argument("--force", action="store_true", help="Retélécharger les archives")
    args = parser.parse_args()

    destination = Path(args.dest).resolve()
    wav_archive = destination / WAV_ARCHIVE
    repo_archive = destination / REPO_ARCHIVE

    if args.force:
        for path in (wav_archive, repo_archive):
            if path.exists():
                path.unlink()

    try:
        download(DEV_WAV_URL, wav_archive)
        download(REPO_ZIP_URL, repo_archive)
    except Exception as exc:
        print(f"Échec du téléchargement : {exc}", file=sys.stderr)
        return 1

    try:
        wav_count = extract_members(
            wav_archive, destination / "wav",
            lambda name: name.lower().endswith(".wav"),
        )
        rttm_count = extract_members(
            repo_archive, destination / "rttm",
            lambda name: "/dev/" in name and name.lower().endswith(".rttm"),
        )
    except zipfile.BadZipFile as exc:
        print(f"Archive invalide : {exc}", file=sys.stderr)
        return 1

    print(f"{wav_count} fichier(s) WAV et {rttm_count} annotation(s) RTTM extraits dans {destination}")
    if not wav_count or not rttm_count:
        print("Corpus incomplet : vérifier les archives téléchargées.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
