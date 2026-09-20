#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filtres média partagés par les étapes du pipeline.

Règle métier : les fichiers `.mov` livrés dans les archives sont des logos
animés à couche alpha (ajoutés manuellement en post-production), et non des
vidéos du tournage. Ils ne doivent être ni convertis (STEP2) ni analysés
(STEP3 à STEP7), mais traverser le pipeline tels quels jusqu'à la
finalisation (STEP8), qui les copie dans le dossier `docs/` final.

Le comportement est piloté par la variable d'environnement `SKIP_MOV_FILES`
(active par défaut) : la désactiver rétablit la conversion `.mov` -> `.mp4`.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Tuple

SKIP_MOV_ENV_VAR = "SKIP_MOV_FILES"
PRESERVED_EXTENSIONS: Tuple[str, ...] = (".mov",)


def _parse_bool(raw: str | None, default: bool) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def is_skip_preserved_media_enabled() -> bool:
    """Indique si les médias préservés (.mov) sont ignorés par le pipeline.

    L'environnement est relu à chaque appel afin de rester surchargeable
    (tests, exécution manuelle).
    """
    return _parse_bool(os.environ.get(SKIP_MOV_ENV_VAR), default=True)


def is_preserved_media(file_path: Path) -> bool:
    """Vrai si le fichier doit être conservé tel quel (logo animé .mov)."""
    if not is_skip_preserved_media_enabled():
        return False
    return Path(file_path).suffix.lower() in PRESERVED_EXTENSIONS


def split_preserved_media(paths: Iterable[Path]) -> Tuple[List[Path], List[Path]]:
    """Sépare une liste de fichiers en ``(à_traiter, préservés)``."""
    to_process: List[Path] = []
    preserved: List[Path] = []
    for path in paths:
        if is_preserved_media(path):
            preserved.append(path)
        else:
            to_process.append(path)
    return to_process, preserved
