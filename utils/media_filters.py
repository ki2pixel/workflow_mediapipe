#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filtres média partagés par les étapes du pipeline.

Règle métier : un fichier `.mov` doit traverser le pipeline tel quel (non
normalisé par STEP1, non analysé par STEP2 à STEP6, copié dans le dossier
`docs/` final par STEP7) lorsqu'il :

- porte une couche alpha réelle (logos animés ajoutés en post-production) ;
- ou figure dans ``PRESERVED_MOV_NAMES`` (défaut : ``m6+.mov``).

La détection de la couche alpha s'effectue en deux étages : d'abord `ffprobe`
(`pix_fmt` des flux vidéo), puis MediaInfo en plan B (binding `pymediainfo`
s'il est importable, sinon CLI `mediainfo`). Si la couche alpha reste
indéterminable, le fichier est **préservé par précaution** : aucun `.mov`
non vérifié n'est converti.

Les autres `.mov` sans alpha redeviennent des vidéos ordinaires : STEP1 les
normalise en `.mp4` (MP4 / H.264 / 25 fps) comme tout autre format.

Le comportement global est piloté par la variable d'environnement
`SKIP_MOV_FILES` (active par défaut) : la désactiver rétablit le traitement
de tous les `.mov`, y compris les logos alpha.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

SKIP_MOV_ENV_VAR = "SKIP_MOV_FILES"
PRESERVED_EXTENSIONS: Tuple[str, ...] = (".mov",)

PRESERVED_MOV_NAMES_ENV_VAR = "PRESERVED_MOV_NAMES"
DEFAULT_PRESERVED_MOV_NAMES: Tuple[str, ...] = ("m6+.mov",)

# Formats de pixels porteurs d'une couche alpha (préfixes FFmpeg).
ALPHA_PIX_FMT_PREFIXES: Tuple[str, ...] = (
    "yuva", "gbrap", "ya8", "ya16", "ayuv", "rgba", "bgra", "argb", "abgr",
)
# Codecs QuickTime alpha-capables (tags conteneur normalisés).
# ap4h/ap4x = ProRes 4444 / 4444 XQ, rle = Animation, png = PNG.
ALPHA_CODEC_TAGS = frozenset({"ap4h", "ap4x", "rle", "png"})

# Formats MediaInfo explicitement incapables de porter une couche alpha.
MEDIAINFO_NON_ALPHA_FORMATS = frozenset({"avc", "hevc", "mpeg-4 visual", "dv", "jpeg"})

FFPROBE_PATH = "ffprobe"
MEDIAINFO_PATH = "mediainfo"
PROBE_TIMEOUT_SECONDS = 30

_alpha_cache: Dict[Tuple[str, int, int], bool] = {}
_alpha_cache_lock = threading.RLock()
_mediainfo_missing_warned = False


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


def get_preserved_mov_names() -> Tuple[str, ...]:
    """Noms de fichiers `.mov` à préserver malgré l'absence de couche alpha.

    Lus dans ``PRESERVED_MOV_NAMES`` (séparateur virgule, casse ignorée) ;
    ``m6+.mov`` par défaut. Une valeur vide désactive la liste noire.
    """
    raw = os.environ.get(PRESERVED_MOV_NAMES_ENV_VAR)
    if raw is None:
        return DEFAULT_PRESERVED_MOV_NAMES
    return tuple(name.strip().lower() for name in raw.split(",") if name.strip())


def _pix_fmt_has_alpha(pix_fmt: str) -> bool:
    normalized = (pix_fmt or "").strip().lower()
    return bool(normalized) and normalized.startswith(ALPHA_PIX_FMT_PREFIXES)


def _probe_alpha_ffprobe(file_path: Path) -> Optional[bool]:
    """Étage 1 : couche alpha déduite du pix_fmt des flux vidéo (ffprobe).

    Retourne True (alpha présent), False (tous les flux sont explicitement
    sans alpha) ou None (indéterminable : fichier illisible, pix_fmt manquant).
    """
    try:
        command = [
            FFPROBE_PATH, "-v", "error",
            "-select_streams", "v",
            "-show_entries", "stream=codec_name,codec_tag_string,pix_fmt",
            "-of", "json",
            str(file_path),
        ]
        result = subprocess.run(
            command, capture_output=True, text=True, check=True,
            encoding="utf-8", timeout=PROBE_TIMEOUT_SECONDS,
        )
        payload = json.loads(result.stdout or "{}")
    except Exception as exc:
        logger.debug("Probe ffprobe impossible pour %s: %s", Path(file_path).name, exc)
        return None

    streams = payload.get("streams") or []
    if not streams:
        return None

    has_missing_pix_fmt = False
    for stream in streams:
        pix_fmt = stream.get("pix_fmt")
        if pix_fmt:
            if _pix_fmt_has_alpha(pix_fmt):
                return True
        else:
            has_missing_pix_fmt = True

    if not has_missing_pix_fmt:
        return False

    for stream in streams:
        if stream.get("pix_fmt"):
            continue
        tag = (stream.get("codec_tag_string") or "").strip().lower()
        if tag in ALPHA_CODEC_TAGS:
            return True
    return None


def _mediainfo_payload(file_path: Path) -> Optional[dict]:
    """Charge le JSON MediaInfo (plan B) : binding `pymediainfo` puis CLI."""
    global _mediainfo_missing_warned

    pymediainfo = None
    try:
        import pymediainfo  # type: ignore
    except ImportError as exc:
        logger.debug("pymediainfo non importable: %s", exc)

    if pymediainfo is not None:
        try:
            return pymediainfo.MediaInfo.parse(str(file_path)).to_data()
        except Exception as exc:
            logger.debug("pymediainfo en échec pour %s: %s", Path(file_path).name, exc)

    if not shutil.which(MEDIAINFO_PATH):
        if not _mediainfo_missing_warned:
            logger.warning(
                "Plan B de détection alpha indisponible (ni pymediainfo ni CLI mediainfo) : "
                "les .mov non analysables par ffprobe seront préservés par précaution."
            )
            _mediainfo_missing_warned = True
        return None

    try:
        result = subprocess.run(
            [MEDIAINFO_PATH, "--Output=JSON", str(file_path)],
            capture_output=True, text=True, check=True,
            encoding="utf-8", timeout=PROBE_TIMEOUT_SECONDS,
        )
        return json.loads(result.stdout or "{}")
    except Exception as exc:
        logger.debug("Probe mediainfo impossible pour %s: %s", Path(file_path).name, exc)
        return None


def _iter_mediainfo_tracks(payload: dict) -> List[dict]:
    """Normalise les deux schémas MediaInfo (CLI JSON et `to_data` du binding)."""
    media = payload.get("media")
    if isinstance(media, dict):
        return list(media.get("track") or [])
    tracks = payload.get("tracks")
    if isinstance(tracks, list):
        return tracks
    return []


def _track_field(track: dict, cli_key: str, binding_key: str) -> str:
    value = track.get(cli_key)
    if value in (None, ""):
        value = track.get(binding_key)
    return str(value or "").strip()


def _probe_alpha_mediainfo(file_path: Path) -> Optional[bool]:
    """Étage 2 (plan B) : couche alpha déduite du profil MediaInfo.

    Utile lorsque ffprobe ne peut pas lire le conteneur ou n'expose aucun
    pix_fmt. Retourne None si MediaInfo est indisponible ou non concluant.
    """
    payload = _mediainfo_payload(file_path)
    if not payload:
        return None

    video_tracks = [
        track for track in _iter_mediainfo_tracks(payload)
        if _track_field(track, "@type", "track_type").lower() == "video"
    ]
    if not video_tracks:
        return None

    undetermined = False
    for track in video_tracks:
        fmt = _track_field(track, "Format", "format").lower()
        profile = _track_field(track, "Format_Profile", "format_profile")
        codec_id = _track_field(track, "CodecID", "codec_id").lower()

        if "4444" in profile:
            return True
        if codec_id in ALPHA_CODEC_TAGS:
            return True
        if fmt in {"rle", "png"}:
            # Animation/PNG dans MOV sont alpha-capables : on préserve par prudence.
            return True
        if fmt == "prores" or fmt in MEDIAINFO_NON_ALPHA_FORMATS:
            continue
        undetermined = True

    return None if undetermined else False


def has_alpha_channel(file_path: Path) -> Optional[bool]:
    """Indique si la vidéo porte une couche alpha (None si indéterminable).

    Étages : ffprobe (`pix_fmt`), puis MediaInfo en plan B. Seuls les verdicts
    définitifs sont mis en cache, par (chemin, mtime, taille).
    """
    path = Path(file_path)
    try:
        stat = path.stat()
    except OSError as exc:
        logger.debug("Stat impossible pour %s: %s", path.name, exc)
        return None

    cache_key = (str(path), stat.st_mtime_ns, stat.st_size)
    with _alpha_cache_lock:
        cached = _alpha_cache.get(cache_key)
    if cached is not None:
        return cached

    verdict = _probe_alpha_ffprobe(path)
    if verdict is None:
        verdict = _probe_alpha_mediainfo(path)

    if verdict is not None:
        with _alpha_cache_lock:
            _alpha_cache[cache_key] = verdict
        logger.debug("Détection alpha pour %s: %s", path.name, verdict)
    return verdict


def reset_alpha_cache() -> None:
    """Vide le cache de détection alpha (tests, réexécution manuelle)."""
    with _alpha_cache_lock:
        _alpha_cache.clear()


def is_preserved_media(file_path: Path) -> bool:
    """Vrai si le fichier doit traverser le pipeline tel quel.

    Sont préservés les `.mov` à couche alpha et les `.mov` figurant dans
    ``PRESERVED_MOV_NAMES`` (défaut ``m6+.mov``). En cas de détection alpha
    indéterminable, le fichier est préservé par précaution.
    """
    if not is_skip_preserved_media_enabled():
        return False

    path = Path(file_path)
    if path.suffix.lower() not in PRESERVED_EXTENSIONS:
        return False
    if path.name.lower() in get_preserved_mov_names():
        return True

    verdict = has_alpha_channel(path)
    if verdict is None:
        logger.warning(
            "Couche alpha indéterminable pour %s : fichier préservé par précaution "
            "(installer 'mediainfo' ou 'pymediainfo' pour fiabiliser la détection).",
            path.name,
        )
        return True
    return verdict


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
