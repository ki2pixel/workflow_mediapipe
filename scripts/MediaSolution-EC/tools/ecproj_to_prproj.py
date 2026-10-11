#!/usr/bin/env python3
"""ecproj_to_prproj.py — convertit un projet EffectCraft (.ecproj) en projet Premiere Pro (.prproj).

EffectCraft ne sait pas écrire de .prproj et son export FCP7/xmeml centre mal les clips à
l'import dans Premiere Pro. Cet outil reconstruit **directement** le projet Premiere depuis le
JSON .ecproj, hors Adobe, sans passer par le .aep.

Le format .prproj (gzip d'un XML `PremiereData`) n'est pas documenté : la structure écrite ici
a été relevée sur des projets de référence générés par Adobe (Premiere/AE 2026) et alignée
valeur par valeur avec le .ecproj d'origine. Correspondances vérifiées :

  - une comp EffectCraft  → une séquence Premiere (1 piste V + 1 piste A, davantage si des
                            calques se chevauchent — allocation automatique) ;
  - un calque Footage     → un item de piste (Start/End = in_point/out_point) ;
  - le groupe Transform   → le filtre « AE.ADBE Motion » (11 paramètres) :
        Position = [x / largeur_comp, y / hauteur_comp]     (Point normalisé)
        Anchor   = [x / largeur_source, y / hauteur_source]
        Scale    = pourcentage (2 emplacements + Uniform Scale), Rotation = degrés ;
  - les keyframes         → StartKeyframe (sentinelle -100 h = valeur de la 1re clé) + lignes
                            `temps,x:y,<ease>,5,4,<tangentes>` ; clés linéaires : vitesses
                            |Δnormalisé|/Δt et influence 1/6 ; clés Bézier (ease 0 / 33 %) :
                            gabarit Adobe « 5,0,0,0,0,0 » ; tangentes spatiales automatiques
                            (P_next − P_prev)/6, les valeurs explicites du .ecproj sinon ;
  - les calques parentés  → position **monde** (les objets nuls « Null Segments » ne sont pas
                            exportés, comme pour le .aep) ;
  - les médias            → vidéo, image fixe (structure « still » à durée infinie) et audio
                            seul (sans flux vidéo) ; chemins réécrits par défaut selon
                            PATH_MAP (/mnt/cache → F:, pour l'ouverture sous Windows).

Les temps écrits sont ceux du .ecproj. La chaîne Adobe .aep→Premiere décalait les clés de
1 à 4 images (`floor(image × 25/24)`, artefact de timebase) : ce décalage n'est pas reproduit.

Limites v1 (avertissement, non exporté) : sources autres que Footage (Solid/Text/Shape/Camera/
Light/comp imbriquée), plus d'une comp, blend ≠ Normal, opacité ≠ 100, stretch ≠ 100.

Masques et effets (propres à EffectCraft — l'export .aep, lui, les écrit) : ces projets ne
sont **pas exportés en .prproj** (le fichier serait incomplet) — seul le .aep est produit, et
un .prproj voisin devenu obsolète est supprimé. `--force` passe outre.

Usage :
  python3 ecproj_to_prproj.py <projet.ecproj> [-o sortie.prproj] [--path-map SRC=DST] [--verify]
  python3 ecproj_to_prproj.py <dossier> --all [--compare-with REF.prproj]
  python3 ecproj_to_prproj.py            # mode bureau : scan de ROOT + fenêtres zenity

Options :
  -o, --out FICHIER     chemin du .prproj (défaut : à côté du .ecproj, même nom)
  --all                 convertit tous les *.ecproj du dossier donné (récursif)
  --path-map SRC=DST    réécrit le préfixe des chemins de médias (répétable ; défaut :
                        la constante PATH_MAP, /mnt/cache → F:)
  --no-path-map         n'applique aucune réécriture (chemins Linux écrits tels quels)
  --skip-missing        n'affiche qu'un décompte des médias absents (pas la liste)
  --force               exporte même si le projet a des masques/effets (incomplet)
  --verify              relit le .prproj produit et affiche un résumé (lecture seule)
  --compare-with REF    compare le résultat à un .prproj de référence (diff sémantique)
  --xml-dump            écrit aussi le XML décompressé à côté du .prproj (débogage)
  --no-gui              force la sortie texte (mode bureau sans fenêtre)
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime

# ------------------------------------------------------------------- réglages

# Mode bureau (double-clic, sans argument) : les seuls réglages à modifier.
ROOT = "/mnt/cache"                       # racine scannée (dossiers projet = ses enfants directs)
NAME_FILTERS = ("camille",)               # sous-chaînes de nom de dossier — tuple : la virgule compte
PATH_MAP = [("/mnt/cache", "F:")]         # réécriture des chemins de médias pour Windows ; [] = inchangés
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prproj_export.log")

TICKS_PER_SECOND = 254_016_000_000

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import ecproj_to_aep as conv  # helpers partagés avec le convertisseur .aep
except Exception as exc:  # pragma: no cover - dépend de l'environnement
    print(f"ecproj_to_aep.py introuvable ou invalide (doit être dans le même dossier) : {exc}",
          file=sys.stderr)
    sys.exit(2)

# ------------------------- constantes du format .prproj (fichier Premiere 2026)

CLASS_IDS: dict[str, tuple[str, str]] = {
    "Project": ("62ad66dd-0dcd-42da-a660-6d8fbde94876", "45"),
    "RootProjectItem": ("1c307a89-9318-47d7-a583-bf2553736543", "1"),
    "ClipProjectItem": ("cb4e0ed7-aca1-4171-8525-e3658dec06dd", "1"),
    "ProjectSettings": ("50c16708-a1a1-4d2f-98d5-4e283ae28353", "21"),
    "CompileSettings": ("18a35d66-597e-4157-b783-938b5bec3547", "4"),
    "ScratchDiskSettings": ("4c6ed82b-a81c-4df1-8bd0-750504c4b560", "4"),
    "IngestSettings": ("2db8f76b-2c37-48ee-925d-9a4f7278152d", "2"),
    "WorkspaceSettings": ("c4372273-e1aa-4683-98aa-a2ceadf3066c", "1"),
    "VideoSettings": ("58474264-30c4-43a2-bba5-dc0812df8a3a", "10"),
    "AudioSettings": ("6baf5521-b132-4634-840e-13cec5bc86a4", "8"),
    "VideoCompileSettings": ("db372db5-7de2-4d3c-98ae-f42659d77b22", "9"),
    "AudioCompileSettings": ("34b10007-ab6d-49a7-bac5-7b60d919e387", "6"),
    "DummyCaptureSettings": ("328c2aa2-47f9-4211-805b-b6a6dbd4ca29", "1"),
    "DefaultSequenceSettings": ("567bdf53-d6d9-4d61-b2f1-f4834bebea9b", "2"),
    "MasterClip": ("fb11c33a-b0a9-4465-aa94-b6d5db2628cf", "12"),
    "ClipLoggingInfo": ("77ab7fdd-dcdf-465d-9906-7a330ca1e738", "10"),
    "AudioComponentChain": ("3cb131d1-d3c0-47ae-a19a-bdf75ea11674", "4"),
    "VideoComponentChain": ("0970e08a-f58f-4108-b29a-1a717b8e12e2", "3"),
    "VideoClip": ("9308dbef-2440-4acb-9ab2-953b9a4e82ec", "11"),
    "AudioClip": ("b8830d03-de02-41ee-84ec-fe566dc70cd9", "8"),
    "ClipChannelGroupVectorSerializer": ("a3127a8c-95d4-456e-a7f5-171b3f922426", "1"),
    "VideoMediaSource": ("e64ddf74-8fac-4682-8aa8-0e0ca2248949", "2"),
    "AudioMediaSource": ("f588da05-fc2a-4fbc-9383-74d653b379e3", "2"),
    "SecondaryContent": ("f9d004b5-cb04-4e2f-af6f-64fadc2c4be9", "1"),
    "ClipChannelVectorSerializer": ("333d203b-3a53-4195-8894-fc7523ff3dc7", "1"),
    "AudioSequenceSource": ("e8d4cc83-38cb-491f-9d94-e5f7e3b205ee", "7"),
    "VideoSequenceSource": ("4752dfa9-7a7e-4a3b-a25b-cafde1a8d036", "3"),
    "Media": ("7a5c103e-f3ac-4391-b6b4-7cc3d2f9a7ff", "30"),
    "ClipChannelSerializer": ("5c89aa7a-89a6-4483-becd-f2b1def42316", "1"),
    "Sequence": ("6a15d903-8739-11d5-af2d-9b7855ad8974", "12"),
    "AudioStream": ("0b5cf52f-2b85-4863-890b-8844b64ecfe9", "8"),
    "VideoStream": ("a36e4719-3ec6-4a0c-ab11-8b4aab377aa5", "22"),
    "VideoTrackGroup": ("9e9abf7a-0918-49c2-91ae-991b5dde77bb", "13"),
    "AudioTrackGroup": ("9b9238b9-53a8-4cc3-b03f-b36246d052e6", "6"),
    "DataTrackGroup": ("b714b71d-6838-48dd-9b77-db19088ced7e", "1"),
    "VideoClipTrack": ("f68dcd81-8805-11d5-af2d-9bfa89d4ddd4", "1"),
    "AudioClipTrack": ("097f6203-99ae-11d5-84f2-8cf14bde7040", "7"),
    "AudioMixTrack": ("4b1d8400-e89e-11d5-abc4-a1a13b1e80a0", "4"),
    "VideoClipTrackItem": ("368b0406-29e3-4923-9fcd-094fbf9a1089", "8"),
    "AudioClipTrackItem": ("064ec682-9ba6-11d5-af2d-9ca32c7d6164", "11"),
    "StereoToStereoPanProcessor": ("7bf86a01-efbe-11d5-abc4-c1ce2b1e9090", "1"),
    "DefaultPanProcessor": ("33a94282-ee2c-11d5-abc4-c1cd7f9e3c10", "2"),
    "AudioTrackInlet": ("be3af080-e8c6-11d5-abc4-a1c6d5dee670", "4"),
    "SubClip": ("e0c58dc9-dbdd-4166-aef7-5db7e3f22e84", "6"),
    "AudioFader": ("1a38c583-ed5c-11d5-abc4-c1cbf61ec590", "3"),
    "AudioMeter": ("72ea4700-f615-11d5-abc4-c186585e63e0", "2"),
    "VideoFilterComponent": ("d10da199-beea-4dd1-b941-ed3a78766d50", "9"),
    "AudioFilterComponent": ("d77a90a0-6c9e-44bf-9b20-de8c21168fe1", "4"),
    "PointComponentParam": ("ca81d347-309b-44d2-acc7-1c572efb973c", "4"),
    "VideoComponentParam": ("fe47129e-6c94-4fc0-95d5-c056a517aaf3", "10"),
    "AudioComponentParam": ("a714635e-a628-4b27-9d59-77eba47dbc1a", "10"),
}
CLASS_UNIFORM_PARAM = ("cc12343e-f113-4d3b-ae05-b287db77d461", "10")
CLASS_ALT_PARAM = ("a4ff2d6e-7ac2-44f8-9d52-17d9ca50e542", "10")
CLASS_MUTE_PARAM = ("32657501-3aa4-445f-a49b-d09ecb9fa1ae", "10")
CLASS_VOLUME_PARAM = ("a714635e-a628-4b27-9d59-77eba47dbc1a", "10")

GUID_MEDIA_VIDEO = "228cda18-3625-4d2d-951e-348879e4ed93"
GUID_MEDIA_AUDIO = "80b8e3d5-6dca-4195-aefb-cb5f407ab009"
GUID_MEDIA_DATA = "d8143ffe-eec4-4d2a-a909-d5f7bf094dc5"
GUID_IMPLEMENTATION = "bf7c0e58-488e-4211-9dad-8a71d808748f"
GUID_EDITING_MODE = "5125b1eb-7925-433f-beea-f5d884227812"

SENTINEL = "-91445760000000000"
AUDIO_LAYOUT = '[{"channellabel":100},{"channellabel":101}]'
COLOR_SPACE = '{"baseColorProfile":{"colorProfileName":"BT.709 RGB Full"},"baseProfileType":1}'
IMMERSIVE = ('{"ambisonicsHRIR":"","ambisonicsMonitoringType":0,"capturedHorizontalView":360,'
             '"capturedVerticalView":180,"fieldOfHorizontalView":108,"fieldOfVerticalView":108,'
             '"projectionType":0,"stereoscopicEye":0,"stereoscopicType":0,"version":3}')
TONEMAP = '{"peak":-1,"version":3}'
INFLUENCE = "0.16666666666666666"
DEFAULT_CLIP_VOLUME = "0.177827939391"
DEFAULT_CLIP_VOLUME_F = "0.17782793939113617"
STILL_DURATION_TICKS = 10973491200000000   # durée « infinie » d'un média image : 12 h (comme Adobe)
STILL_CLIP_TICKS = 1524096000000           # plage nominale du clip image dans le masterclip (6 s)


# -------------------------------------------------------------- mini-DOM XML


def esc(text) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt_num(value) -> str:
    """Format Adobe : « 207. », « 0.5 », « -0.034987815221150714 » (entier suffixé d'un point)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    f = float(value)
    rounded = round(f)
    if abs(f - rounded) < 1e-9 and abs(rounded) < 1e15:
        if rounded == 0:
            return "-0" if str(f).startswith("-") else "0"
        return f"{int(rounded)}."
    return repr(f)


def fmt_scalar(value) -> str:
    """Comme fmt_num mais zéro = « 0. » (forme des valeurs scalaires Adobe)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    f = float(value)
    rounded = round(f)
    if abs(f - rounded) < 1e-9 and abs(rounded) < 1e15:
        if rounded == 0:
            return "-0." if str(f).startswith("-") else "0."
        return f"{int(rounded)}."
    return repr(f)


class E:
    """Élément XML structurel (un attribut peut porter une référence à un Obj)."""

    __slots__ = ("name", "attrs", "children", "text")

    def __init__(self, name: str, attrs: dict | None = None, children: list | None = None,
                 text: str | None = None):
        self.name = name
        self.attrs = attrs or {}
        self.children = children
        self.text = text


class Obj:
    """Objet du graphe .prproj : ObjectID (ou ObjectUID) + ClassID + Version + champs."""

    __slots__ = ("tag", "classid", "version", "uid", "id", "fields")

    def __init__(self, tag: str, uid: bool = False, classid_version: tuple[str, str] | None = None):
        cid, ver = classid_version or CLASS_IDS[tag]
        self.tag = tag
        self.classid = cid
        self.version = ver
        self.uid = str(uuid.uuid4()) if uid else None
        self.id: int | None = None
        self.fields: list[tuple] = []

    def txt(self, tag: str, value) -> "Obj":
        self.fields.append(("t", tag, str(value)))
        return self

    def ref(self, tag: str, target: "Obj") -> "Obj":
        self.fields.append(("r", tag, target))
        return self

    def el(self, element: E) -> "Obj":
        self.fields.append(("x", element))
        return self


def _emit_e(e: E, depth: int) -> list[str]:
    ind = "\t" * depth
    attrs = []
    has_ref = False
    for key, value in e.attrs.items():
        if isinstance(value, Obj):
            ref_key = "ObjectURef" if value.uid else "ObjectRef"
            ref_val = value.uid if value.uid else value.id
            attrs.append(f'{ref_key}="{ref_val}"')
            has_ref = True
        else:
            attrs.append(f'{key}="{esc(value)}"')
    head = f"{ind}<{e.name}" + (" " + " ".join(attrs) if attrs else "")
    if has_ref and e.children is None and e.text is None:
        return [head + "/>"]
    if e.text is not None:
        return [f"{head}>{esc(e.text)}</{e.name}>"]
    lines = [head + ">"]
    for child in e.children or []:
        lines.extend(_emit_e(child, depth + 1))
    lines.append(f"{ind}</{e.name}>")
    return lines


def _emit_obj(o: Obj, depth: int) -> list[str]:
    ind = "\t" * depth
    ind_child = "\t" * (depth + 1)
    if o.uid is not None:
        head = f'{ind}<{o.tag} ObjectUID="{o.uid}" ClassID="{o.classid}" Version="{o.version}">'
    else:
        head = f'{ind}<{o.tag} ObjectID="{o.id}" ClassID="{o.classid}" Version="{o.version}">'
    lines = [head]
    for field in o.fields:
        kind = field[0]
        if kind == "t":
            lines.append(f'{ind_child}<{field[1]}>{esc(field[2])}</{field[1]}>')
        elif kind == "r":
            tag, target = field[1], field[2]
            if target.uid is not None:
                lines.append(f'{ind_child}<{tag} ObjectURef="{target.uid}"/>')
            else:
                lines.append(f'{ind_child}<{tag} ObjectRef="{target.id}"/>')
        else:
            lines.extend(_emit_e(field[1], depth + 1))
    lines.append(f"{ind}</{o.tag}>")
    return lines


def serialize(document: list) -> str:
    counter = 0
    for entry in document:
        if isinstance(entry, Obj) and entry.uid is None:
            counter += 1
            entry.id = counter
    lines = ['<?xml version="1.0" encoding="UTF-8" ?>', '<PremiereData Version="3">']
    for entry in document:
        if isinstance(entry, Obj):
            lines.extend(_emit_obj(entry, 1))
        else:
            lines.extend(_emit_e(entry, 1))
    lines.append("</PremiereData>")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------- valeurs du .ecproj


def ticks_per_frame(frame_rate) -> int:
    """Durée d'une image en ticks (les champs FrameRate du .prproj sont des ticks/image)."""
    if isinstance(frame_rate, dict):
        num = int(frame_rate.get("num") or 25)
        den = int(frame_rate.get("den") or 1)
    else:
        from fractions import Fraction
        frac = Fraction(float(frame_rate or 25)).limit_denominator(1000)
        num, den = frac.numerator, frac.denominator
    return int(round(TICKS_PER_SECOND * den / num)) if num else int(TICKS_PER_SECOND / 25)


def pixel_aspect_str(value) -> str:
    try:
        pa = float(value if value is not None else 1.0)
    except (TypeError, ValueError):
        pa = 1.0
    if abs(pa - 1.0) < 1e-9:
        return "1,1"
    from fractions import Fraction
    frac = Fraction(pa).limit_denominator(1000)
    return f"{frac.numerator},{frac.denominator}"


def node_value(node: dict | None):
    if not node:
        return None
    return conv.prop_value(node.get("value"))


def pair_from(value, fallback=(0.0, 0.0)) -> tuple[float, float]:
    if isinstance(value, list) and len(value) >= 2:
        return float(value[0]), float(value[1])
    if value is not None:
        return float(value), float(fallback[1])
    return float(fallback[0]), float(fallback[1])


def node_pair(node: dict | None, fallback=(0.0, 0.0)) -> tuple[float, float]:
    return pair_from(node_value(node), fallback)


def key_pair(key: dict, fallback=(0.0, 0.0)) -> tuple[float, float]:
    return pair_from(conv.prop_value((key or {}).get("value")), fallback)


def node_keys(node: dict | None) -> list[dict]:
    return (node or {}).get("keys") or []


def scalar_of(value, default=0.0) -> float:
    if isinstance(value, list):
        return float(value[0]) if value else default
    if value is None:
        return default
    return float(value)


def keys_are_constant(node: dict | None) -> bool:
    keys = node_keys(node)
    if len(keys) <= 1:
        return True
    values = []
    for key in keys:
        value = conv.prop_value(key.get("value"))
        values.append(tuple(value) if isinstance(value, list) else value)
    return len(set(values)) == 1


# ------------------------------------------------- encodage des paramètres


def point_start(x_norm, y_norm) -> str:
    return (f"{SENTINEL},{fmt_num(x_norm)}:{fmt_num(y_norm)},"
            "0,0,0,0,0,0,5,4,0,0,0,0")


def point_row(time_ticks, x_norm, y_norm, tail, spatial) -> str:
    return (f"{int(time_ticks)},{fmt_num(x_norm)}:{fmt_num(y_norm)},"
            + ",".join(tail) + ",5,4," + ",".join(spatial))


def scalar_start(value) -> str:
    return f"{SENTINEL},{fmt_scalar(value)},0,0,0,0,0,0"


def scalar_row(time_ticks, value, tail) -> str:
    return f"{int(time_ticks)},{fmt_scalar(value)}," + ",".join(tail)


def is_linear_key(key: dict) -> bool:
    return (str(key.get("in_interp") or "Linear").lower() == "linear"
            and str(key.get("out_interp") or "Linear").lower() == "linear")


def temporal_tail(key: dict, in_speed: float, out_speed: float) -> list[str]:
    """Gabarit relevé sur Adobe : clé linéaire → vitesses (u/s) + influence 1/6 ;
    clé Bézier (ease 0 / 33 %) → « 5,0,0,0,0,0 » (courbe lissée native)."""
    if is_linear_key(key):
        return ["0", "0", fmt_num(in_speed), INFLUENCE, fmt_num(out_speed), INFLUENCE]
    return ["5", "0", "0", "0", "0", "0"]


def point_keyframes(node: dict, cw: float, ch: float, offset=(0.0, 0.0)):
    """(StartKeyframe, Keyframes) d'un paramètre Point (Position/Anchor)."""
    keys = node_keys(node)
    dx, dy = offset
    points = []
    for key in keys:
        x, y = key_pair(key)
        points.append((x + dx, y + dy))
    if not points:
        x, y = node_pair(node)
        return point_start((x + dx) / cw, (y + dy) / ch), None
    if keys_are_constant(node):
        x, y = points[0]
        return point_start(x / cw, y / ch), None

    def norm(pt):
        return (pt[0] / cw, pt[1] / ch)

    times = [int(k.get("time") or 0) for k in keys]
    speeds_in, speeds_out = [0.0] * len(points), [0.0] * len(points)
    for i in range(1, len(points)):
        dt = conv.ticks_to_seconds(times[i] - times[i - 1])
        if dt > 0:
            (px, py), (qx, qy) = norm(points[i - 1]), norm(points[i])
            speeds_in[i] = ((qx - px) ** 2 + (qy - py) ** 2) ** 0.5 / dt
    for i in range(len(points) - 1):
        dt = conv.ticks_to_seconds(times[i + 1] - times[i])
        if dt > 0:
            (px, py), (qx, qy) = norm(points[i]), norm(points[i + 1])
            speeds_out[i] = ((qx - px) ** 2 + (qy - py) ** 2) ** 0.5 / dt

    rows = []
    for i, key in enumerate(keys):
        nx, ny = norm(points[i])
        tail = temporal_tail(key, speeds_in[i], speeds_out[i])
        if bool(key.get("spatial_auto", True)):
            if 0 < i < len(points) - 1:
                delta = (norm(points[i + 1])[0] - norm(points[i - 1])[0],
                         norm(points[i + 1])[1] - norm(points[i - 1])[1])
            elif i == 0:
                delta = (norm(points[1])[0] - norm(points[0])[0],
                         norm(points[1])[1] - norm(points[0])[1])
            else:
                delta = (norm(points[-1])[0] - norm(points[-2])[0],
                         norm(points[-1])[1] - norm(points[-2])[1])
            tin = (0.0, 0.0) if i == 0 else (-delta[0] / 6.0, -delta[1] / 6.0)
            tout = (0.0, 0.0) if i == len(points) - 1 else (delta[0] / 6.0, delta[1] / 6.0)
        else:
            si = key.get("spatial_in") or [0.0, 0.0, 0.0]
            so = key.get("spatial_out") or [0.0, 0.0, 0.0]
            tin = (float(si[0]) / cw, float(si[1]) / ch)
            tout = (float(so[0]) / cw, float(so[1]) / ch)
        rows.append(point_row(times[i], nx, ny, tail,
                              [fmt_num(tin[0]), fmt_num(tin[1]),
                               fmt_num(tout[0]), fmt_num(tout[1])]))
    x0, y0 = points[0]
    return point_start(x0 / cw, y0 / ch), ";".join(rows) + ";"


def scalar_keyframes(node: dict):
    """(StartKeyframe, Keyframes) d'un paramètre scalaire (Échelle, Rotation)."""
    keys = node_keys(node)
    if not keys or keys_are_constant(node):
        value = node_value(node) if not keys else conv.prop_value(keys[0].get("value"))
        return scalar_start(scalar_of(value)), None

    def val(key):
        return scalar_of(conv.prop_value(key.get("value")))

    times = [int(k.get("time") or 0) for k in keys]
    speeds_in, speeds_out = [0.0] * len(keys), [0.0] * len(keys)
    for i in range(1, len(keys)):
        dt = conv.ticks_to_seconds(times[i] - times[i - 1])
        if dt > 0:
            speeds_in[i] = abs(val(keys[i]) - val(keys[i - 1])) / dt
    for i in range(len(keys) - 1):
        dt = conv.ticks_to_seconds(times[i + 1] - times[i])
        if dt > 0:
            speeds_out[i] = abs(val(keys[i + 1]) - val(keys[i])) / dt
    rows = [scalar_row(times[i], val(key), temporal_tail(key, speeds_in[i], speeds_out[i]))
            for i, key in enumerate(keys)]
    return scalar_start(val(keys[0])), ";".join(rows) + ";"


# ------------------------------------------------------- fabriques d'objets


def layout_e() -> E:
    return E("AudioChannelLayout", text=AUDIO_LAYOUT)


def make_audio_chain(components: list[Obj], with_defaults: bool = True) -> Obj:
    chain = Obj("AudioComponentChain")
    if with_defaults:
        chain.txt("DefaultVol", "true")
        chain.txt("DefaultVolumeComponentID", "1")
        chain.txt("DefaultChannelVolumeComponentID", "2")
    if components:
        chain.el(E("ComponentChain", {"Version": "3"}, children=[
            E("Components", {"Version": "1"}, children=[
                E("Component", {"Index": str(i), "ref": obj}) for i, obj in enumerate(components)
            ])
        ]))
    else:
        chain.el(E("ComponentChain", {"Version": "3"}))
    chain.el(layout_e())
    chain.txt("ChannelType", "1")
    return chain


def make_ccgvs():
    ccgvs = Obj("ClipChannelGroupVectorSerializer")
    ccvs = Obj("ClipChannelVectorSerializer")
    serializers = []
    for channel in range(2):
        serializer = Obj("ClipChannelSerializer")
        serializer.txt("SourceClipIndex", "0")
        serializer.txt("mSourceChannelIndex", str(channel))
        serializers.append(serializer)
    ccvs.el(E("ClipChannels", {"Version": "1"}, children=[
        E("ClipChannelItem", {"Index": "0", "ref": serializers[0]}),
        E("ClipChannelItem", {"Index": "1", "ref": serializers[1]}),
    ]))
    ccvs.txt("ChannelType", "1")
    ccgvs.el(E("ClipChannelVectors", {"Version": "1"}, children=[
        E("ClipChannelVectorItem", {"Index": "0", "ref": ccvs})
    ]))
    return ccgvs, ccvs, serializers


def make_video_chain(filter_obj: Obj | None = None, intrinsic_motion: bool = False) -> Obj:
    chain = Obj("VideoComponentChain")
    if filter_obj is None and not intrinsic_motion:
        chain.el(E("ComponentChain", {"Version": "3"}))
        return chain
    if intrinsic_motion:
        chain.txt("DefaultMotion", "true")
    chain.txt("DefaultOpacity", "true")
    if intrinsic_motion:
        chain.txt("DefaultMotionComponentID", "2")
    chain.txt("DefaultOpacityComponentID", "1")
    if filter_obj is None:
        chain.el(E("ComponentChain", {"Version": "3"}))
    else:
        chain.el(E("ComponentChain", {"Version": "3"}, children=[
            E("Components", {"Version": "1"}, children=[
                E("Component", {"Index": "0", "ref": filter_obj})
            ])
        ]))
    return chain


def make_point_param(node: dict | None, cw: float, ch: float, fallback, offset=(0.0, 0.0)) -> Obj:
    param = Obj("PointComponentParam")
    if node is None:
        x, y = fallback
        param.txt("ParameterControlType", "17")
        param.txt("ParameterID", "-1")
        param.txt("StartKeyframe", point_start((x + offset[0]) / cw, (y + offset[1]) / ch))
        return param
    animated = bool(node_keys(node)) and not keys_are_constant(node)
    start, rows = point_keyframes(node, cw, ch, offset)
    if animated:
        param.txt("IsTimeVarying", "true")
    param.txt("ParameterControlType", "17")
    param.txt("ParameterID", "-1")
    param.txt("StartKeyframe", start)
    if rows is not None:
        param.txt("Keyframes", rows)
    return param


def make_scalar_param(node: dict | None, fallback=0.0, time_varying=False,
                      classid_version=None, bool_value=None) -> Obj:
    param = Obj("VideoComponentParam",
                classid_version=classid_version or CLASS_IDS["VideoComponentParam"])
    animated = bool(node_keys(node)) and not keys_are_constant(node)
    if animated and bool_value is None:
        start, rows = scalar_keyframes(node)
        param.txt("IsTimeVarying", "true")
        param.txt("ParameterControlType", "17")
        param.txt("ParameterID", "-1")
        param.txt("StartKeyframe", start)
        param.txt("Keyframes", rows)
        return param
    if bool_value is not None:
        param.txt("IsTimeVarying", "true")
        param.txt("ParameterControlType", "17")
        param.txt("ParameterID", "-1")
        param.txt("StartKeyframe", f"{SENTINEL},{'true' if bool_value else 'false'},0,0,0,0,0,0")
        return param
    value = scalar_of(node_value(node), fallback) if node is not None else fallback
    if time_varying:
        param.txt("IsTimeVarying", "true")
    param.txt("ParameterControlType", "17")
    param.txt("ParameterID", "-1")
    param.txt("StartKeyframe", scalar_start(value))
    return param


# ------------------------------------------------------------- construction


def convert(ec_path: str, out_path: str, path_maps: list[tuple[str, str]], skip_missing: bool,
            xml_dump: bool, log) -> dict:
    with open(ec_path, "r", encoding="utf-8") as handle:
        ec = json.load(handle)

    warnings: list[str] = []
    missing: list[str] = []
    warn = warnings.append
    warn_missing = missing.append

    items = ec.get("items") or {}
    comps = [it for it in items.values() if (it.get("kind") or {}).get("type") == "Comp"]
    if not comps:
        raise ValueError("aucune comp dans le .ecproj")
    if len(comps) > 1:
        warn(f"{len(comps)} comps trouvées : seule « {comps[0].get('name')} » est exportée (v1)")
    comp = comps[0]
    comp_kind = comp.get("kind") or {}
    cw = float(comp_kind.get("width") or 1080)
    ch = float(comp_kind.get("height") or 1920)
    frame_ticks = ticks_per_frame(comp_kind.get("frame_rate"))
    comp_duration = int(comp_kind.get("duration") or 0)
    sample_rate = int(((ec.get("settings") or {}).get("audio_sample_rate") or 48000))
    audio_ticks = int(round(TICKS_PER_SECOND / sample_rate)) if sample_rate else 5292000

    # --- médias -------------------------------------------------------------
    bundles: dict[str, dict] = {}
    for item_id, item in items.items():
        item_kind = item.get("kind") or {}
        if item_kind.get("type") != "Footage":
            continue
        real_path = str(item_kind.get("path") or "")
        if not real_path:
            warn(f"média « {item.get('name')} » sans chemin, ignoré")
            continue
        stored_path = conv.apply_path_map(real_path, path_maps)
        if stored_path != real_path and re.match(r"^[A-Za-z]:", stored_path):
            stored_path = stored_path.replace("/", "\\")
        if not os.path.exists(real_path):
            warn_missing(f"média absent du disque (référencé quand même) : {real_path}")
        is_still = str(item_kind.get("kind") or "") == "Still"
        bundles[str(item_id)] = {
            "id": item_id,
            "name": str(item.get("name") or os.path.basename(real_path)),
            "stored_path": stored_path,
            "real_path": real_path,
            "width": int(item_kind.get("width") or 1920),
            "height": int(item_kind.get("height") or 1080),
            # une image fixe est sans audio et de durée « infinie » (structure Adobe) ;
            # sa cadence est celle de la séquence, pas celle déclarée par l'item EC
            "frame_rate": ((comp_kind.get("frame_rate") if is_still
                            else item_kind.get("frame_rate")) or {"num": 25, "den": 1}),
            "duration": (STILL_DURATION_TICKS if is_still
                         else int(item_kind.get("duration") or 0)),
            "has_audio": bool(item_kind.get("has_audio", True)) and not is_still,
            "has_video": bool(item_kind.get("has_video", True)),
            "is_still": is_still,
        }
        if not bundles[str(item_id)]["has_video"] and not bundles[str(item_id)]["has_audio"]:
            warn(f"média « {item.get('name')} » sans vidéo ni audio : traité comme vidéo")
            bundles[str(item_id)]["has_video"] = True
        elif not bundles[str(item_id)]["has_video"]:
            warn(f"média « {item.get('name')} » audio seul : exporté comme média audio "
                 f"(pas de flux vidéo)")
        if is_still:
            warn(f"média « {item.get('name')} » de type image : exporté comme image fixe "
                 f"(durée infinie, sans audio)")

    # --- calques → entrées, allocation de pistes ----------------------------
    layers = comp_kind.get("layers") or []
    layers_by_id = {int(l["id"]): l for l in layers if l.get("id") is not None}

    tracks: list[list[dict]] = []
    audio_only_entries: list[dict] = []
    for layer in reversed(layers):  # du bas vers le haut : piste libre la plus basse
        source = layer.get("source") or {}
        stype = source.get("type") or ""
        if stype == "Null":
            continue
        if stype != "Footage" or str(source.get("item")) not in bundles:
            warn(f"calque « {layer.get('name')} » : source {stype or '?'} non exportée (v1)")
            continue
        if abs(float(layer.get("stretch") or 100.0) - 100.0) > 1e-6:
            warn(f"calque « {layer.get('name')} » : stretch ≠ 100 % non géré (v1), ignoré")
            continue
        blend = str(layer.get("blend_mode") or "Normal")
        if blend != "Normal":
            warn(f"calque « {layer.get('name')} » : mode de fusion {blend} non géré (v1)")
        n_masks = len(conv.enabled_masks(layer))
        n_effects = len(conv.collect_effects(layer))
        if n_masks or n_effects:
            warn(f"calque « {layer.get('name')} » : {n_masks} masque(s) et {n_effects} effet(s) "
                 f"propres à EffectCraft, non repris par Premiere (v1)")
        start = int(layer.get("in_point") or 0)
        end = int(layer.get("out_point") or 0)
        if end <= start:
            warn(f"calque « {layer.get('name')} » : in/out invalides, ignoré")
            continue
        layer_start = int(layer.get("start_time") or 0)
        entry = {
            "layer": layer,
            "bundle": bundles[str(source.get("item"))],
            "start": start,
            "end": end,
            "src_in": max(0, start - layer_start),
            "src_out": max(0, end - layer_start),
            "audio": bool((layer.get("switches") or {}).get("audio")),
            "track": -1,
        }
        if not entry["bundle"]["has_video"]:
            audio_only_entries.append(entry)  # média audio seul : pas de piste vidéo
            continue
        placed = False
        for index, track in enumerate(tracks):
            if all(entry["end"] <= item["start"] or entry["start"] >= item["end"]
                   for item in track):
                track.append(entry)
                entry["track"] = index
                placed = True
                break
        if not placed:
            tracks.append([entry])
            entry["track"] = len(tracks) - 1
    for track in tracks:
        track.sort(key=lambda item: item["start"])
    entries: list[dict] = ([entry for track in tracks for entry in track]
                           + audio_only_entries)
    entries_by_track = tracks
    track_count = max(1, len(entries_by_track))

    # pistes audio : allocation indépendante (seuls les calques réellement audibles)
    audio_tracks_list: list[list[dict]] = []
    for entry in sorted((item for item in entries
                         if item["audio"] and item["bundle"]["has_audio"]),
                        key=lambda item: item["start"]):
        placed = False
        for track in audio_tracks_list:
            if all(entry["end"] <= item["start"] or entry["start"] >= item["end"]
                   for item in track):
                track.append(entry)
                placed = True
                break
        if not placed:
            audio_tracks_list.append([entry])
    audio_entries = [entry for track in audio_tracks_list for entry in track]
    audio_track_count = max(1, len(audio_tracks_list))

    # --- objets (création puis assemblage dans l'ordre du document) ---------
    document: list = []

    project_ref = Obj("Project", classid_version=CLASS_IDS["Project"])
    project = Obj("Project")
    project.el(E("Node", {"Version": "1"}, children=[E("Properties", {"Version": "1"}, children=[
        E("MZ.Project.ApplicationID", text="Pro"),
        E("MZ.BuildVersion.Modified", text=f"Pr 26.2.1 - {datetime.now():%d/%m/%Y %H:%M:%S}"),
        E("MZ.BuildVersion.Created", text=f"Pr 26.2.1 - {datetime.now():%d/%m/%Y %H:%M:%S}"),
    ])]))
    root = Obj("RootProjectItem", uid=True)
    root.el(E("ProjectItem", {"Version": "1"}, children=[E("Name", text="Root Bin")]))
    settings = Obj("ProjectSettings")
    compile_settings = [Obj("CompileSettings") for _ in range(5)]
    scratch = Obj("ScratchDiskSettings")
    for tag in ("AudioPreviewLocation0", "VideoPreviewLocation0", "CapsuleMediaLocation0",
                "DVDEncodingLocation0", "TransferMediaLocation0", "CapturedVideoLocation0",
                "CCLibrariesLocation0", "AutoSaveLocation0"):
        scratch.txt(tag, "SameAsProject")
    ingest = Obj("IngestSettings")
    ingest.txt("Enabled", "false")
    ingest.txt("Action", "copy")
    workspace = Obj("WorkspaceSettings")
    project.ref("RootProjectItem", root)
    project.ref("ProjectSettings", settings)
    project.ref("MovieCompileSettings", compile_settings[0])
    project.ref("StillCompileSettings", compile_settings[1])
    project.ref("AudioCompileSettings", compile_settings[2])
    project.ref("CustomCompileSettings", compile_settings[3])
    project.ref("VideoPreviewCompileSettings", compile_settings[4])
    project.ref("ScratchDiskSettings", scratch)
    project.ref("IngestSettings", ingest)
    project.ref("ProjectWorkspace", workspace)
    project.txt("NextID", "1000000")

    media_items = []
    for bundle in bundles.values():
        item_obj = Obj("ClipProjectItem", uid=True)
        item_obj.el(E("ProjectItem", {"Version": "1"}, children=[E("Name", text=bundle["name"])]))
        bundle["item"] = item_obj
        media_items.append(item_obj)
    sequence_item = Obj("ClipProjectItem", uid=True)
    sequence_item.el(E("ProjectItem", {"Version": "1"},
                       children=[E("Name", text=str(comp.get("name") or "Sequence"))]))
    root.el(E("ProjectItemContainer", {"Version": "1"}, children=[
        E("Items", {"Version": "1"}, children=[
            E("Item", {"Index": str(index), "ref": item})
            for index, item in enumerate(media_items + [sequence_item])
        ])
    ]))

    vs_global = Obj("VideoSettings")
    vs_global.txt("FrameRate", frame_ticks)
    vs_global.txt("FrameSize", f"0,0,{int(cw)},{int(ch)}")
    vs_global.txt("PixelAspectRatio", pixel_aspect_str(comp_kind.get("pixel_aspect")))
    as_global = Obj("AudioSettings")

    def make_vcs(target_vs: Obj) -> Obj:
        vcs = Obj("VideoCompileSettings")
        vcs.ref("VideoSettings", target_vs)
        for tag, value in (("Compressor", "1685288558"), ("VideoCompilerClassIDFourCC", "1061109567"),
                           ("VideoFileTypeFourCC", "1096173910"), ("Depth", "24"),
                           ("RenderDepth", "0"), ("Aspect43", "false"), ("Quality", "100"),
                           ("UseDataRate", "false"), ("DataRate", "3500"),
                           ("ForceRecompress", "true"), ("ForceRecompressValue", "2"),
                           ("Deinterlace", "false"), ("IgnoreVideoFilters", "false"),
                           ("OptimizeStills", "false"), ("FramesAtMarkers", "false"),
                           ("RealTimePreview", "true"), ("VideoFieldType", "0"),
                           ("DoKeyframeEveryNFrames", "false"),
                           ("DoKeyframeEveryNFramesValue", "0"),
                           ("AddKeyframesAtMarkers", "false"), ("AddKeyframesAtEdits", "false"),
                           ("RelativeFrameSize", "1")):
            vcs.txt(tag, value)
        return vcs

    def make_acs(target_as: Obj) -> Obj:
        acs = Obj("AudioCompileSettings")
        acs.ref("AudioSettings", target_as)
        acs.txt("SampleType", "3")
        acs.txt("Compressor", "1380013856")
        acs.txt("Interleave", "1")
        return acs

    global_pair_vs, global_pair_as = Obj("VideoSettings"), Obj("AudioSettings")
    vcs_global = make_vcs(global_pair_vs)
    acs_global = make_acs(global_pair_as)
    dummy_capture = Obj("DummyCaptureSettings")
    default_seq = Obj("DefaultSequenceSettings")
    default_seq.txt("TotalVideoTracks", "1")
    default_seq.txt("DefaultAudioStandardMonoTracks", "0")
    default_seq.txt("DefaultAudioStandardStereoTracks", "1")
    default_seq.txt("DefaultAudioStandard51Tracks", "0")
    default_seq.txt("DefaultAudioSubmixMonoTracks", "0")
    default_seq.txt("DefaultAudioSubmixStereoTracks", "0")
    default_seq.txt("DefaultAudioSubmix51Tracks", "0")

    compile_pairs = []
    for _ in range(5):
        pair_vs, pair_as = Obj("VideoSettings"), Obj("AudioSettings")
        compile_pairs.append((make_vcs(pair_vs), make_acs(pair_as), pair_vs, pair_as))
    for compile_obj, pair in zip(compile_settings, compile_pairs):
        compile_obj.ref("VideoCompileSettings", pair[0])
        compile_obj.ref("AudioCompileSettings", pair[1])
    for compile_obj in compile_settings:
        compile_obj.txt("CompilerClassIDFourCC", "0")
        compile_obj.txt("CompilerFourCC", "0")
        compile_obj.txt("ExportVideo", "true")
        compile_obj.txt("ExportAudio", "true")
        compile_obj.txt("AddToProjectWhenFinished", "true")
        compile_obj.txt("BeepWhenFinished", "false")
        compile_obj.txt("ExportWorkAreaOnly", "false")
        compile_obj.txt("EmbedProjectLink", "false")
    # le dernier (aperçu vidéo) reprend les FourCC du compilateur vidéo
    compile_settings[4].fields = [
        field for field in compile_settings[4].fields
        if not (field[0] == "t" and field[1] in ("CompilerClassIDFourCC", "CompilerFourCC"))
    ]
    insert_at = next(i for i, field in enumerate(compile_settings[4].fields)
                     if field[0] == "t" and field[1] == "ExportVideo")
    compile_settings[4].fields.insert(insert_at, ("t", "CompilerFourCC", "1096173910"))
    compile_settings[4].fields.insert(insert_at, ("t", "CompilerClassIDFourCC", "1061109567"))

    settings.ref("VideoSettings", vs_global)
    settings.ref("AudioSettings", as_global)
    settings.ref("VideoCompileSettings", vcs_global)
    settings.ref("AudioCompileSettings", acs_global)
    settings.ref("CaptureSettings", dummy_capture)
    settings.ref("DefaultSequenceSettings", default_seq)
    settings.txt("VideoTimeDisplay", "101")
    settings.txt("AudioTimeDisplay", "200")
    settings.txt("VideoTimeDisplayInitial", "999")
    settings.txt("ActionSafeWidth", "10")
    settings.txt("ActionSafeHeight", "10")
    settings.txt("TitleSafeWidth", "20")
    settings.txt("TitleSafeHeight", "20")
    settings.txt("ShouldScaleMedia", "false")
    settings.txt("EditingModeID", GUID_EDITING_MODE)
    settings.txt("PreviewFileFormatID", "00000000-0000-0000-0000-000000000000")
    settings.txt("UsePreviewCache", "false")
    settings.txt("ColorManagementSettings",
                 '{"enableLogColorManagement":2,"graphicsWhiteLuminance":203,'
                 '"lutInterpolationMethod":1}')

    # masterclips (médias puis séquence)
    masters = []
    for bundle in bundles.values():
        has_audio = bundle["has_audio"]
        is_still = bundle["is_still"]
        master = Obj("MasterClip", uid=True)
        logging = Obj("ClipLoggingInfo")
        if is_still:
            logging.txt("CaptureMode", "2")
        logging.txt("ClipName", bundle["name"])
        logging.txt("TimecodeFormat", "101")
        if not is_still:
            logging.txt("MediaInPoint", "0")
            logging.txt("MediaOutPoint", str(bundle["duration"]))
        logging.txt("MediaFrameRate", str(ticks_per_frame(bundle["frame_rate"])))
        audio_chain = audio_source = audio_clip = None
        video_source = video_clip = None
        secondary = []
        clips_children: list[E] = []
        source_fields: list[Obj] = []
        children_order: list[Obj] = []
        if bundle["has_video"]:
            video_source = Obj("VideoMediaSource")
            video_clip_children = [E("Source", {"ref": video_source}),
                                   E("ClipID", text=str(uuid.uuid4()))]
            if is_still:
                video_clip_children += [E("InPoint", text="0"),
                                        E("OutPoint", text=str(STILL_CLIP_TICKS))]
            video_clip_children.append(E("InUse", text="false"))
            video_clip = Obj("VideoClip")
            video_clip.el(E("Clip", {"Version": "18"}, children=video_clip_children))
            clips_children.append(E("Clip", {"Index": "0", "ref": video_clip}))
            source_fields.append(video_source)
        if has_audio:
            audio_chain = make_audio_chain([])
            audio_source = Obj("AudioMediaSource")
            audio_clip = Obj("AudioClip")
            for channel in range(2):
                sec = Obj("SecondaryContent")
                sec.ref("Content", audio_source)
                sec.txt("ChannelIndex", str(channel))
                secondary.append(sec)
            audio_clip.el(E("Clip", {"Version": "18"}, children=[
                E("Source", {"ref": audio_source}),
                E("ClipID", text=str(uuid.uuid4())),
                E("InUse", text="false"),
            ]))
            audio_clip.el(E("SecondaryContents", {"Version": "1"}, children=[
                E("SecondaryContentItem", {"Index": "0", "ref": secondary[0]}),
                E("SecondaryContentItem", {"Index": "1", "ref": secondary[1]}),
            ]))
            audio_clip.el(layout_e())
            clips_children.append(E("Clip", {"Index": str(len(clips_children)), "ref": audio_clip}))
            source_fields += [audio_source, secondary[0], secondary[1]]
        if has_audio:
            ccgvs, ccvs, ccs = make_ccgvs()
            source_fields.append(ccvs)
        else:
            ccgvs, ccvs, ccs = Obj("ClipChannelGroupVectorSerializer"), None, []
        # ordre d'émission des enfants du masterclip, comme Adobe :
        # LoggingInfo, chaîne audio, clip vidéo, clip audio, groupes de canaux
        children_order = [logging]
        if audio_chain is not None:
            children_order.append(audio_chain)
        if video_clip is not None:
            children_order.append(video_clip)
        if audio_clip is not None:
            children_order.append(audio_clip)
        children_order.append(ccgvs)
        master.ref("LoggingInfo", logging)
        if has_audio:
            master.el(E("AudioComponentChains", {"Version": "1"}, children=[
                E("AudioComponentChain", {"Index": "0", "ref": audio_chain})
            ]))
        master.el(E("Clips", {"Version": "1"}, children=clips_children))
        master.ref("AudioClipChannelGroups", ccgvs)
        master.txt("Name", bundle["name"])
        master.txt("MasterClipChangeVersion", "0")
        bundle["master_obj"] = master
        bundle["video_source"] = video_source
        bundle["audio_source"] = audio_source
        masters.append({"master": master, "logging": logging, "audio_chain": audio_chain,
                        "video_source": video_source, "audio_source": audio_source,
                        "video_clip": video_clip, "audio_clip": audio_clip,
                        "secondary": secondary, "ccgvs": ccgvs, "ccvs": ccvs, "ccs": ccs,
                        "children": children_order, "sources": source_fields})

    sequence = Obj("Sequence", uid=True)
    seq_master = Obj("MasterClip", uid=True)
    seq_logging = Obj("ClipLoggingInfo")
    seq_audio_chain = make_audio_chain([])
    seq_audio_source = Obj("AudioSequenceSource")
    seq_video_source = Obj("VideoSequenceSource")
    seq_secondary = []
    for channel in range(2):
        sec = Obj("SecondaryContent")
        sec.ref("Content", seq_audio_source)
        sec.txt("ChannelIndex", str(channel))
        seq_secondary.append(sec)
    seq_audio_clip = Obj("AudioClip")
    seq_audio_clip.el(E("Clip", {"Version": "18"}, children=[
        E("Source", {"ref": seq_audio_source}),
        E("ClipID", text=str(uuid.uuid4())),
        E("InUse", text="false"),
    ]))
    seq_audio_clip.el(E("SecondaryContents", {"Version": "1"}, children=[
        E("SecondaryContentItem", {"Index": "0", "ref": seq_secondary[0]}),
        E("SecondaryContentItem", {"Index": "1", "ref": seq_secondary[1]}),
    ]))
    seq_audio_clip.el(layout_e())
    seq_video_clip = Obj("VideoClip")
    seq_video_clip.el(E("Clip", {"Version": "18"}, children=[
        E("Source", {"ref": seq_video_source}),
        E("ClipID", text=str(uuid.uuid4())),
        E("InUse", text="false"),
    ]))
    seq_ccgvs, seq_ccvs, seq_ccs = make_ccgvs()
    seq_master.ref("LoggingInfo", seq_logging)
    seq_master.el(E("AudioComponentChains", {"Version": "1"}, children=[
        E("AudioComponentChain", {"Index": "0", "ref": seq_audio_chain})
    ]))
    seq_master.el(E("Clips", {"Version": "1"}, children=[
        E("Clip", {"Index": "0", "ref": seq_audio_clip}),
        E("Clip", {"Index": "1", "ref": seq_video_clip}),
    ]))
    seq_master.ref("AudioClipChannelGroups", seq_ccgvs)
    seq_master.txt("Name", str(comp.get("name") or "Sequence"))
    seq_master.txt("MasterClipChangeVersion", "7")
    sequence_item.ref("MasterClip", seq_master)
    for bundle, entry in zip(bundles.values(), masters):
        bundle["item"].ref("MasterClip", entry["master"])

    # groupes de pistes et pistes
    video_group_chain = make_video_chain(None)
    video_group = Obj("VideoTrackGroup")
    audio_group = Obj("AudioTrackGroup")
    video_tracks = [Obj("VideoClipTrack", uid=True) for _ in range(track_count)]
    audio_tracks = [Obj("AudioClipTrack", uid=True) for _ in range(audio_track_count)]
    audio_mix_track = Obj("AudioMixTrack")

    # composants audio des pistes : un fader + un meter par piste (plus le mixeur),
    # un panner (avec son paramètre Balance) par piste — structure relevée sur Adobe
    def make_balance_param() -> Obj:
        param = Obj("AudioComponentParam", classid_version=CLASS_VOLUME_PARAM)
        param.txt("StartKeyframe", f"{SENTINEL},0.5,0,0,0,0,0,0")
        param.txt("CurrentValue", "0.5")
        param.txt("IsInverted", "true")
        param.txt("Name", "Balance")
        return param

    balance_params = [make_balance_param() for _ in range(audio_track_count)]

    def make_panner(balance: Obj | None):
        panner = (Obj("StereoToStereoPanProcessor") if balance is not None
                  else Obj("DefaultPanProcessor"))
        component_children = [E("ID", text="4294967280")]
        if balance is not None:
            component_children.insert(0, E("Params", {"Version": "1"}, children=[
                E("Param", {"Index": "0", "ref": balance})
            ]))
        panner.el(E("PanProcessor", {"Version": "3"}, children=[E("AudioComponent", {"Version": "3"}, children=[
            E("Component", {"Version": "7"}, children=component_children),
            layout_e(),
            E("ChannelType", text="1"),
            E("FrameRate", text=str(audio_ticks)),
            E("AudioComponentType", text="0"),
        ])]))
        if balance is None:
            panner.txt("DefaultPannerInputChannelType", "1")
            panner.txt("DefaultPannerOutputChannelType", "1")
        return panner

    panners = [make_panner(balance) for balance in balance_params]
    default_panner = make_panner(None)

    def make_fader(params):
        fader = Obj("AudioFader")
        fader.el(E("AudioComponent", {"Version": "3"}, children=[
            E("Component", {"Version": "7"}, children=[
                E("Params", {"Version": "1"}, children=[
                    E("Param", {"Index": "0", "ref": params[0]}),
                    E("Param", {"Index": "1", "ref": params[1]}),
                ]),
                E("ID", text="1"),
            ]),
            layout_e(),
            E("ChannelType", text="1"),
            E("FrameRate", text=str(audio_ticks)),
            E("AudioComponentType", text="1"),
        ]))
        return fader

    def make_meter():
        meter = Obj("AudioMeter")
        meter.el(E("AudioComponent", {"Version": "3"}, children=[
            E("Component", {"Version": "7"}, children=[E("ID", text="2")]),
            layout_e(),
            E("ChannelType", text="1"),
            E("FrameRate", text=str(audio_ticks)),
            E("AudioComponentType", text="2"),
        ]))
        return meter

    def make_fader_params():
        volume_param = Obj("AudioComponentParam", classid_version=CLASS_VOLUME_PARAM)
        volume_param.txt("UpperBound", "5.6234130859375")
        volume_param.txt("RangeLocked", "false")
        volume_param.txt("UnitsString", "dB")
        volume_param.txt("Name", "Volume")
        mute_param = Obj("AudioComponentParam", classid_version=CLASS_MUTE_PARAM)
        mute_param.txt("RangeLocked", "false")
        mute_param.txt("Name", "Mute")
        return volume_param, mute_param

    fader_params = [make_fader_params() for _ in range(audio_track_count + 1)]
    faders = [make_fader(pair) for pair in fader_params]
    meters = [make_meter() for _ in range(audio_track_count + 1)]
    track_chains = [make_audio_chain([faders[index], meters[index]], with_defaults=False)
                    for index in range(audio_track_count)]
    mix_chain = make_audio_chain([faders[audio_track_count], meters[audio_track_count]],
                                 with_defaults=False)
    inlet = Obj("AudioTrackInlet")
    inlet.el(E("Sources", {"Version": "1"}, children=[
        E("Source", {"Index": "0", "ref": audio_tracks[0]})
    ]))
    inlet.el(layout_e())

    # --- médias (objets Media + flux) et sources -----------------------------
    for bundle in bundles.values():
        audio_stream = None
        if bundle["has_audio"]:
            audio_stream = Obj("AudioStream")
            audio_stream.el(layout_e())
            audio_stream.txt("FrameRate", audio_ticks)
            audio_stream.txt("Duration", str(bundle["duration"]))
            audio_stream.txt("SampleType", "5")
        video_stream = None
        if bundle["has_video"]:
            video_stream = Obj("VideoStream")
            video_stream.txt("FrameRate", ticks_per_frame(bundle["frame_rate"]))
            video_stream.txt("Duration", str(bundle["duration"]))
            video_stream.txt("CodecType", "1061109567")
            if bundle["is_still"]:
                video_stream.txt("IsStill", "true")
            video_stream.txt("FrameRect", f"0,0,{bundle['width']},{bundle['height']}")
            video_stream.txt("OriginalColorSpace", COLOR_SPACE)
            video_stream.txt("IsPAROverridden", "true")
            video_stream.txt("OriginalFieldType", "-1")
            video_stream.txt("IsFieldTypeOverridden", "true")
            video_stream.txt("OverriddenFieldType", "0")
        media_obj = Obj("Media", uid=True)
        if audio_stream is not None:
            media_obj.ref("AudioStream", audio_stream)
        if video_stream is not None:
            media_obj.ref("VideoStream", video_stream)
        media_obj.txt("FilePath", bundle["stored_path"])
        media_obj.txt("ImplementationID", GUID_IMPLEMENTATION)
        media_obj.txt("Title", os.path.basename(bundle["real_path"]) or bundle["name"])
        if bundle["is_still"]:
            media_obj.txt("Infinite", "true")
        media_obj.txt("OfflineReason", "1")
        bundle["media_obj"] = media_obj
        bundle["audio_stream"] = audio_stream
        bundle["video_stream"] = video_stream
        for source in (bundle["video_source"], bundle["audio_source"]):
            if source is None:
                continue
            source.el(E("MediaSource", {"Version": "4"}, children=[
                E("Content", {"Version": "10"}),
                E("Media", {"ref": media_obj}),
            ]))
            source.txt("OriginalDuration", str(bundle["duration"]))
    for source in (seq_audio_source, seq_video_source):
        source.el(E("SequenceSource", {"Version": "4"}, children=[
            E("Content", {"Version": "10"}),
            E("Sequence", {"ref": sequence}),
        ]))
        source.txt("OriginalDuration", str(comp_duration))

    # --- objets par entrée : items, sous-clips, chaînes, filtres, paramètres --
    for entry in entries:
        layer = entry["layer"]
        bundle = entry["bundle"]
        name = str(layer.get("name") or bundle["name"])
        sw = float(bundle["width"])
        sh = float(bundle["height"])
        offset = conv.world_offset(layer, layers_by_id) if layer.get("parent") else (0.0, 0.0)

        position_node = conv.find_transform_node(layer, "position")
        anchor_node = conv.find_transform_node(layer, "anchor")
        scale_node = conv.find_transform_node(layer, "scale")
        rotation_node = conv.find_transform_node(layer, "rotation")
        opacity_node = conv.find_transform_node(layer, "opacity")

        scale_value = node_value(scale_node) or [100.0, 100.0, 100.0]
        scale_x = scalar_of(scale_value, 100.0)
        scale_y = (float(scale_value[1]) if isinstance(scale_value, list)
                   and len(scale_value) > 1 else scale_x)
        rotation_value = scalar_of(node_value(rotation_node), 0.0)

        def animated(node):
            return bool(node) and bool(node_keys(node)) and not keys_are_constant(node)

        if opacity_node is not None:
            opacity_value = node_value(opacity_node)
            if animated(opacity_node) or (opacity_value is not None
                                          and abs(scalar_of(opacity_value, 100.0) - 100.0) > 1e-6):
                warn(f"opacité ≠ 100 sur « {name} » : non exportée (v1)")
        if animated(anchor_node):
            warn(f"ancre animée sur « {name} » : encodage expérimental")
        if animated(rotation_node):
            warn(f"rotation animée sur « {name} » : encodage expérimental")
        if animated(scale_node):
            warn(f"échelle animée sur « {name} » : encodage expérimental")

        if animated(scale_node):
            scale_param_x = make_scalar_param(scale_node, 100.0)
            scale_param_y = make_scalar_param(scale_node, 100.0)
        else:
            scale_param_x = make_scalar_param(None, fallback=scale_x)
            scale_param_y = make_scalar_param(None, fallback=scale_y)
        rotation_param = (make_scalar_param(rotation_node, 0.0) if rotation_node is not None
                          else make_scalar_param(None, fallback=rotation_value))

        # Transform identique aux valeurs par défaut → chaîne intrinsèque d'Adobe
        # (« DefaultMotion », aucun filtre Motion) ; c'est le cas des images fixes posées
        # plein cadre, que Premiere rend avec ses composants par défaut.
        pos_x, pos_y = node_pair(position_node, (cw / 2.0, ch / 2.0))
        anc_x, anc_y = node_pair(anchor_node, (sw / 2.0, sh / 2.0))
        default_motion = (
            not animated(position_node) and not animated(anchor_node)
            and not animated(scale_node) and not animated(rotation_node)
            and offset == (0.0, 0.0)
            and abs(pos_x - cw / 2.0) < 1e-6 and abs(pos_y - ch / 2.0) < 1e-6
            and abs(anc_x - sw / 2.0) < 1e-6 and abs(anc_y - sh / 2.0) < 1e-6
            and abs(scale_x - 100.0) < 1e-6 and abs(scale_y - 100.0) < 1e-6
            and abs(rotation_value) < 1e-6
        )

        if default_motion:
            motion_params = []
            motion_filter = None
            video_chain = make_video_chain(None, intrinsic_motion=True)
        else:
            motion_params = [
                make_point_param(position_node, cw, ch, (cw / 2.0, ch / 2.0), offset),
                scale_param_x,
                scale_param_y,
                make_scalar_param(None, fallback=0.0, classid_version=CLASS_UNIFORM_PARAM,
                                  bool_value=abs(scale_x - scale_y) < 1e-9),
                rotation_param,
                make_point_param(anchor_node, sw, sh, (sw / 2.0, sh / 2.0)),
                make_scalar_param(None, fallback=0.0, time_varying=True,
                                  classid_version=CLASS_ALT_PARAM),
                make_scalar_param(None, fallback=0.0, time_varying=True),
                make_scalar_param(None, fallback=0.0, time_varying=True),
                make_scalar_param(None, fallback=0.0, time_varying=True),
                make_scalar_param(None, fallback=0.0, time_varying=True),
            ]
            motion_filter = Obj("VideoFilterComponent")
            motion_filter.el(E("Component", {"Version": "7"}, children=[
                E("Params", {"Version": "1"}, children=[
                    E("Param", {"Index": str(index), "ref": param})
                    for index, param in enumerate(motion_params)
                ]),
                E("Intrinsic", text="true"),
                E("ID", text="2"),
            ]))
            motion_filter.txt("MatchName", "AE.ADBE Motion")
            motion_filter.txt("VideoFilterType", "2")
            video_chain = make_video_chain(motion_filter)
        entry["params"] = motion_params
        entry["keyframed"] = animated(position_node)
        entry["motion_filter"] = motion_filter
        segment_video_clip = Obj("VideoClip")
        segment_video_clip.el(E("Clip", {"Version": "18"}, children=[
            E("Source", {"ref": bundle["video_source"]}),
            E("ClipID", text=str(uuid.uuid4())),
            E("InPoint", text=str(entry["src_in"])),
            E("OutPoint", text=str(entry["src_out"])),
        ]))
        video_subclip = Obj("SubClip")
        video_subclip.ref("Clip", segment_video_clip)
        video_subclip.ref("MasterClip", bundle["master_obj"])
        video_subclip.txt("OrigChGrp", "0")
        video_subclip.txt("Name", bundle["name"])
        video_item = Obj("VideoClipTrackItem")
        video_item.el(E("ClipTrackItem", {"Version": "8"}, children=[
            E("ComponentOwner", {"Version": "1"},
              children=[E("Components", {"ref": video_chain})]),
            E("TrackItem", {"Version": "4"}, children=(
                [E("Start", text=str(entry["start"]))] if entry["start"] else []
            ) + [E("End", text=str(entry["end"]))]),
            E("SubClip", {"ref": video_subclip}),
        ]))
        video_item.txt("FrameRect", f"0,0,{int(cw)},{int(ch)}")
        video_item.txt("PixelAspectRatio", "1,1")
        video_item.txt("ToneMapSettings", TONEMAP)
        entry["video_item"] = video_item
        entry["video_chain"] = video_chain
        entry["video_subclip"] = video_subclip
        entry["segment_video_clip"] = segment_video_clip

        if not bundle["has_video"]:
            # média audio seul : pas d'item vidéo (les objets construits plus haut ne sont
            # pas émis — seule la partie audio de ce calque compte)
            entry["params"] = []
            entry["motion_filter"] = None
            entry["video_chain"] = None
            entry["video_item"] = None
            entry["video_subclip"] = None
            entry["segment_video_clip"] = None
            entry["keyframed"] = False

        if entry["audio"] and bundle["has_audio"]:
            mute_param = Obj("AudioComponentParam", classid_version=CLASS_MUTE_PARAM)
            mute_param.txt("IsTimeVarying", "false")
            mute_param.txt("ParameterControlType", "17")
            mute_param.txt("RangeLocked", "false")
            volume_param = Obj("AudioComponentParam", classid_version=CLASS_VOLUME_PARAM)
            volume_param.txt("StartKeyframe", f"{SENTINEL},{DEFAULT_CLIP_VOLUME},0,0,0,0,0,0")
            volume_param.txt("CurrentValue", DEFAULT_CLIP_VOLUME_F)
            volume_param.txt("ParameterControlType", "17")
            volume_param.txt("RangeLocked", "false")
            audio_filter = Obj("AudioFilterComponent")
            audio_filter.el(E("AudioComponent", {"Version": "3"}, children=[
                E("Component", {"Version": "7"}, children=[
                    E("Params", {"Version": "1"}, children=[
                        E("Param", {"Index": "0", "ref": mute_param}),
                        E("Param", {"Index": "1", "ref": volume_param}),
                    ]),
                    E("Intrinsic", text="true"),
                    E("ID", text="3"),
                ]),
                layout_e(),
                E("ChannelType", text="1"),
                E("FrameRate", text=str(audio_ticks)),
                E("AudioComponentType", text="0"),
            ]))
            audio_filter.txt("FilterPreset", "0")
            audio_filter.txt("FilterMatchName", "Internal Volume")
            audio_filter.txt("FilterIndex", "-1")
            audio_chain = make_audio_chain([audio_filter])
            segment_secondary = []
            for channel in range(2):
                sec = Obj("SecondaryContent")
                sec.ref("Content", bundle["audio_source"])
                sec.txt("ChannelIndex", str(channel))
                segment_secondary.append(sec)
            segment_audio_clip = Obj("AudioClip")
            segment_audio_clip.el(E("Clip", {"Version": "18"}, children=[
                E("Source", {"ref": bundle["audio_source"]}),
                E("ClipID", text=str(uuid.uuid4())),
                E("InPoint", text=str(entry["src_in"])),
                E("OutPoint", text=str(entry["src_out"])),
            ]))
            segment_audio_clip.el(E("SecondaryContents", {"Version": "1"}, children=[
                E("SecondaryContentItem", {"Index": "0", "ref": segment_secondary[0]}),
                E("SecondaryContentItem", {"Index": "1", "ref": segment_secondary[1]}),
            ]))
            segment_audio_clip.el(layout_e())
            audio_subclip = Obj("SubClip")
            audio_subclip.ref("Clip", segment_audio_clip)
            audio_subclip.ref("MasterClip", bundle["master_obj"])
            audio_subclip.txt("OrigChGrp", "0")
            audio_subclip.txt("Name", bundle["name"])
            audio_item = Obj("AudioClipTrackItem")
            audio_item.el(E("ClipTrackItem", {"Version": "8"}, children=[
                E("ComponentOwner", {"Version": "1"},
                  children=[E("Components", {"ref": audio_chain})]),
                E("TrackItem", {"Version": "4"}, children=(
                    [E("Start", text=str(entry["start"]))] if entry["start"] else []
                ) + [E("End", text=str(entry["end"]))]),
                E("SubClip", {"ref": audio_subclip}),
            ]))
            audio_item.txt("PreRenderComponentChainHashVersion", "1")
            audio_item.txt("ID", str(uuid.uuid4()))
            entry["audio_item"] = audio_item
            entry["audio_chain"] = audio_chain
            entry["audio_subclip"] = audio_subclip
            entry["segment_audio_clip"] = segment_audio_clip
            entry["audio_filter"] = audio_filter
            entry["audio_tail_params"] = [mute_param, volume_param]
            entry["audio_tail_secondary"] = segment_secondary

    # --- remplissage des pistes, groupes et séquence -------------------------
    video_group.el(E("TrackGroup", {"Version": "1"}, children=[
        E("Tracks", {"Version": "1"}, children=[
            E("Track", {"Index": str(i), "ref": track}) for i, track in enumerate(video_tracks)
        ]),
        E("FrameRate", text=str(frame_ticks)),
        E("NextTrackID", text=str(track_count + 1)),
    ]))
    video_group.txt("FrameRect", f"0,0,{int(cw)},{int(ch)}")
    video_group.txt("OutputColorSpace", COLOR_SPACE)
    video_group.txt("ImmersiveVideoVRConfiguration", IMMERSIVE)
    video_group.txt("IsGraphicsWhiteSameAsProject", "false")
    video_group.txt("IsColorAwareEffectsEnabledSameAsProject", "false")
    video_group.el(E("ComponentOwner", {"Version": "1"},
                     children=[E("Components", {"ref": video_group_chain})]))

    for index, (track_obj, track_entries) in enumerate(zip(video_tracks, entries_by_track)):
        track_obj.el(E("ClipTrack", {"Version": "2"}, children=[
            E("Track", {"Version": "4"}, children=[
                E("Node", {"Version": "1"}, children=[E("Properties", {"Version": "1"}, children=[
                    E("MZ.TrackTargeted", text="1")
                ])]),
                E("MediaType", text=GUID_MEDIA_VIDEO),
                E("Index", text=str(index)),
                E("ID", text=str(index + 1)),
            ]),
            E("ClipItems", {"Version": "3"}, children=[
                E("TrackItems", {"Version": "1"}, children=[
                    E("TrackItem", {"Index": str(i), "ref": entry["video_item"]})
                    for i, entry in enumerate(track_entries)
                ]),
                E("MediaType", text=GUID_MEDIA_VIDEO),
                E("Index", text=str(index)),
            ]),
            E("TransitionItems", {"Version": "3"}, children=[
                E("MediaType", text=GUID_MEDIA_VIDEO),
                E("Index", text=str(index)),
            ]),
        ]))
    audio_entries_by_track = audio_tracks_list + [[] for _ in range(
        audio_track_count - len(audio_tracks_list))]
    for index, (track_obj, track_entries, panner, chain) in enumerate(
            zip(audio_tracks, audio_entries_by_track, panners, track_chains)):
        track_obj.el(E("ClipTrack", {"Version": "2"}, children=[
            E("Track", {"Version": "4"}, children=[
                E("Node", {"Version": "1"}, children=[E("Properties", {"Version": "1"}, children=[
                    E("MZ.TrackTargeted", text="1")
                ])]),
                E("MediaType", text=GUID_MEDIA_AUDIO),
                E("Index", text=str(index)),
                E("ID", text=str(index + 2)),
            ]),
            E("ClipItems", {"Version": "3"}, children=[
                E("TrackItems", {"Version": "1"}, children=[
                    E("TrackItem", {"Index": str(i), "ref": entry["audio_item"]})
                    for i, entry in enumerate(track_entries)
                ]),
                E("MediaType", text=GUID_MEDIA_AUDIO),
                E("Index", text=str(index)),
            ]),
            E("TransitionItems", {"Version": "3"}, children=[
                E("MediaType", text=GUID_MEDIA_AUDIO),
                E("Index", text=str(index)),
            ]),
        ]))
        track_obj.el(E("AudioTrack", {"Version": "12"}, children=[
            E("ComponentOwner", {"Version": "1"}, children=[E("Components", {"ref": chain})]),
            E("Panner", {"ref": panner}),
            E("NextPannerID", text="4294967279"),
            E("ID", text=str(uuid.uuid4())),
        ]))

    audio_group.el(E("TrackGroup", {"Version": "1"}, children=[
        E("Tracks", {"Version": "1"}, children=[
            E("Track", {"Index": str(i), "ref": track}) for i, track in enumerate(audio_tracks)
        ]),
        E("FrameRate", text=str(audio_ticks)),
        E("NextTrackID", text=str(audio_track_count + 2)),
    ]))
    audio_group.ref("MasterTrack", audio_mix_track)
    audio_group.txt("AutomationSafeFlags", "0")
    audio_group.txt("NumAdaptiveChannels", "2")
    audio_group.txt("ID", str(uuid.uuid4()))
    audio_mix_track.el(E("AudioTrack", {"Version": "12"}, children=[
        E("ComponentOwner", {"Version": "1"}, children=[E("Components", {"ref": mix_chain})]),
        E("Panner", {"ref": default_panner}),
        E("SubType", text="3"),
        E("Assign", text="0"),
        E("NextPannerID", text="4294967279"),
        E("ID", text=str(uuid.uuid4())),
    ]))
    audio_mix_track.el(E("Track", {"Version": "4"}, children=[
        E("MediaType", text=GUID_MEDIA_AUDIO),
        E("Index", text="0"),
        E("ID", text="1"),
    ]))
    audio_mix_track.ref("Inlet", inlet)

    data_group = Obj("DataTrackGroup")
    data_group.el(E("TrackGroup", {"Version": "1"}, children=[
        E("FrameRate", text=str(frame_ticks)),
        E("NextTrackID", text="1"),
    ]))

    sequence.el(E("Node", {"Version": "1"}, children=[E("Properties", {"Version": "1"}, children=[
        E("AECompID", text=str(comp.get("id") or "")),
        E("MZ.Sequence.VideoTimeDisplayFormat", text="101"),
        E("MZ.ZeroPoint", text="0"),
    ])]))
    sequence.el(E("PersistentGroupContainer", {"Version": "1"}, children=[
        E("LinkContainer", {"Version": "1"})
    ]))
    sequence.el(E("TrackGroups", {"Version": "1"}, children=[
        E("TrackGroup", {"Version": "1", "Index": "0"}, children=[
            E("First", text=GUID_MEDIA_VIDEO), E("Second", {"ref": video_group})]),
        E("TrackGroup", {"Version": "1", "Index": "1"}, children=[
            E("First", text=GUID_MEDIA_AUDIO), E("Second", {"ref": audio_group})]),
        E("TrackGroup", {"Version": "1", "Index": "2"}, children=[
            E("First", text=GUID_MEDIA_DATA), E("Second", {"ref": data_group})]),
    ]))
    sequence.txt("Name", str(comp.get("name") or "Sequence"))

    # --- assemblage du document (ordre du fichier de référence) ---------------
    document = [
        E("Project", {"ref": project}),
        project,
        root,
        settings,
        *compile_settings,
        scratch,
        ingest,
        workspace,
        *media_items,
        sequence_item,
        vs_global,
        as_global,
        vcs_global,
        acs_global,
        dummy_capture,
        default_seq,
        *[field for pair in compile_pairs for field in (pair[0], pair[1])],
        *[entry["master"] for entry in masters],
        seq_master,
        global_pair_vs,
        global_pair_as,
        *[field for pair in compile_pairs for field in (pair[2], pair[3])],
        *[field for entry in masters for field in entry["children"]],
        seq_logging,
        seq_audio_chain,
        seq_audio_clip,
        seq_video_clip,
        seq_ccgvs,
        *[field for entry in masters for field in entry["sources"]],
        seq_audio_source,
        seq_secondary[0],
        seq_secondary[1],
        seq_video_source,
        seq_ccvs,
        *[field for bundle, entry in zip(bundles.values(), masters)
          for field in (bundle["media_obj"], *entry["ccs"])],
        sequence,
        seq_ccs[0],
        seq_ccs[1],
        *[field for bundle in bundles.values()
          for field in (bundle["audio_stream"], bundle["video_stream"]) if field is not None],
        video_group,
        audio_group,
        data_group,
        *video_tracks,
        video_group_chain,
        *audio_tracks,
        audio_mix_track,
        *[entry["video_item"] for entry in entries if entry["video_item"] is not None],
        *[entry["audio_item"] for entry in audio_entries],
        *[field for index in range(audio_track_count)
          for field in (track_chains[index], panners[index])],
        mix_chain,
        default_panner,
        inlet,
        *[field for entry in entries if entry["video_chain"] is not None
          for field in (entry["video_chain"], entry["video_subclip"])],
        *[field for entry in audio_entries
          for field in (entry["audio_chain"], entry["audio_subclip"])],
        *[field for index in range(audio_track_count)
          for field in (faders[index], meters[index], balance_params[index])],
        faders[audio_track_count],
        meters[audio_track_count],
        *[field for entry in entries
          if entry["motion_filter"] is not None and entry["segment_video_clip"] is not None
          for field in (entry["motion_filter"], entry["segment_video_clip"])],
        *[field for entry in entries
          if entry["motion_filter"] is None and entry["segment_video_clip"] is not None
          for field in (entry["segment_video_clip"],)],
        *[field for entry in audio_entries
          for field in (entry["audio_filter"], entry["segment_audio_clip"])],
        *[field for pair in fader_params for field in pair],
        *[param for entry in entries for param in entry["params"]],
        *[field for entry in audio_entries
          for field in (entry["audio_tail_params"][0], entry["audio_tail_params"][1],
                        entry["audio_tail_secondary"][0], entry["audio_tail_secondary"][1])],
    ]

    xml_text = serialize(document)
    tmp_path = out_path + ".tmp"
    with gzip.open(tmp_path, "wb", compresslevel=9) as handle:
        handle.write(xml_text.encode("utf-8"))
    os.replace(tmp_path, out_path)
    if xml_dump:
        with open(out_path + ".xml", "w", encoding="utf-8") as handle:
            handle.write(xml_text)

    report = {
        "media": len(bundles),
        "tracks": track_count,
        "items": len(entries),
        "audio_items": len(audio_entries),
        "keyframed": sum(1 for entry in entries if entry.get("keyframed")),
        "warnings": warnings,
        "missing": missing,
    }
    log(f"{os.path.basename(ec_path)} → {os.path.basename(out_path)} : "
        f"{report['media']} média(s), {report['tracks']} piste(s), {report['items']} item(s), "
        f"{report['audio_items']} audio, {report['keyframed']} animé(s)")
    return report


# ------------------------------------------------------------- vérification


def read_prproj(path: str):
    with open(path, "rb") as handle:
        raw = handle.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    root = ET.fromstring(raw.decode("utf-8"))
    by_id, by_uid = {}, {}
    for element in root:
        if element.get("ObjectID") is not None:
            by_id[element.get("ObjectID")] = element
        if element.get("ObjectUID") is not None:
            by_uid[element.get("ObjectUID")] = element
    return root, by_id, by_uid


def resolve(element, by_id, by_uid):
    if element is None:
        return None
    if "ObjectRef" in element.attrib:
        return by_id.get(element.get("ObjectRef"))
    if "ObjectURef" in element.attrib:
        return by_uid.get(element.get("ObjectURef"))
    return None


def check_references(root, by_id, by_uid) -> list[str]:
    problems = []
    for element in root:
        for node in element.iter():
            for key, value in node.attrib.items():
                if key == "ObjectRef" and value not in by_id:
                    problems.append(f"{element.tag}: ObjectRef={value}")
                elif key == "ObjectURef" and value not in by_uid:
                    problems.append(f"{element.tag}: ObjectURef={value}")
    return problems


def sequence_snapshot(root, by_id, by_uid) -> list[dict]:
    """Modèle lisible du fichier : séquences → pistes → items (temps, plage média, Motion)."""
    sequences = []
    for element in root:
        if element.tag != "Sequence":
            continue
        tracks = []
        track_groups = element.find("TrackGroups")
        for group_ref in (track_groups.findall("TrackGroup") if track_groups is not None else []):
            group = resolve(group_ref.find("Second"), by_id, by_uid)
            if group is None or group.tag not in ("VideoTrackGroup", "AudioTrackGroup"):
                continue
            kind = "V" if group.tag == "VideoTrackGroup" else "A"
            frame_rect = (group.findtext("FrameRect") or "0,0,0,0").split(",")
            dims = (frame_rect[2], frame_rect[3]) if len(frame_rect) == 4 else ("0", "0")
            tracks_list = group.find("TrackGroup/Tracks")
            for track_ref in (tracks_list.findall("Track") if tracks_list is not None else []):
                track = resolve(track_ref, by_id, by_uid)
                if track is None:
                    continue
                items = []
                for item_ref in track.findall("ClipTrack/ClipItems/TrackItems/TrackItem"):
                    item = resolve(item_ref, by_id, by_uid)
                    if item is None:
                        continue
                    info = {"start": 0, "end": 0, "in": 0, "out": 0, "params": {}}
                    track_item = item.find("ClipTrackItem/TrackItem")
                    if track_item is not None:
                        info["start"] = int(track_item.findtext("Start") or 0)
                        info["end"] = int(track_item.findtext("End") or 0)
                    subclip = resolve(item.find("ClipTrackItem/SubClip"), by_id, by_uid)
                    if subclip is not None:
                        clip = resolve(subclip.find("Clip"), by_id, by_uid)
                        if clip is not None:
                            inner = clip.find("Clip")
                            info["in"] = int(inner.findtext("InPoint") or 0)
                            info["out"] = int(inner.findtext("OutPoint") or 0)
                    chain = resolve(item.find("ClipTrackItem/ComponentOwner/Components"),
                                    by_id, by_uid)
                    if chain is not None:
                        for component_ref in chain.findall("ComponentChain/Components/Component"):
                            filter_obj = resolve(component_ref, by_id, by_uid)
                            if filter_obj is None:
                                continue
                            for param_ref in filter_obj.findall("Component/Params/Param"):
                                param = resolve(param_ref, by_id, by_uid)
                                if param is None:
                                    continue
                                info["params"][int(param_ref.get("Index"))] = {
                                    "start": param.findtext("StartKeyframe"),
                                    "keys": param.findtext("Keyframes"),
                                }
                    items.append(info)
                tracks.append({"kind": kind, "items": items, "dims": dims})
        sequences.append({"name": element.findtext("Name") or "", "tracks": tracks})
    return sequences


def parse_point(start_keyframe: str | None):
    if not start_keyframe:
        return None
    parts = start_keyframe.split(",")
    if len(parts) < 2 or ":" not in parts[1]:
        return None
    x, _, y = parts[1].partition(":")
    try:
        return float(x), float(y)
    except ValueError:
        return None


def verify_summary(path: str) -> str:
    root, by_id, by_uid = read_prproj(path)
    problems = check_references(root, by_id, by_uid)
    sequences = sequence_snapshot(root, by_id, by_uid)
    lines = [f"Vérification de {os.path.basename(path)} :"]
    if problems:
        lines.append(f"  !! {len(problems)} référence(s) non résolue(s), ex. {problems[:3]}")
    else:
        lines.append("  références : toutes résolues")
    for seq in sequences:
        video_tracks = [track for track in seq["tracks"] if track["kind"] == "V"]
        audio_tracks = [track for track in seq["tracks"] if track["kind"] == "A"]
        video = video_tracks[0] if video_tracks else {"items": [], "dims": ("0", "0")}
        n_video = sum(len(track["items"]) for track in video_tracks)
        n_audio = sum(len(track["items"]) for track in audio_tracks)
        lines.append(f"  séquence « {seq['name']} » : {n_video} clip(s) vidéo sur "
                     f"{len(video_tracks)} piste(s), {n_audio} clip(s) audio sur "
                     f"{len(audio_tracks)} piste(s), cadre {video['dims'][0]}x{video['dims'][1]}")
        for item in video["items"][:3]:
            state = "animé" if item["params"].get(0, {}).get("keys") else "fixe"
            lines.append(
                f"    [{item['start'] / TICKS_PER_SECOND:8.3f} .. "
                f"{item['end'] / TICKS_PER_SECOND:8.3f}] média "
                f"{item['in'] / TICKS_PER_SECOND:8.3f}..{item['out'] / TICKS_PER_SECOND:8.3f} "
                f"{state}, Position={parse_point(item['params'].get(0, {}).get('start'))}")
        if len(video["items"]) > 3:
            lines.append(f"    … et {len(video['items']) - 3} autre(s) clip(s)")
    return "\n".join(lines)


def compare_prproj(ours_path: str, ref_path: str) -> None:
    our_root, our_id, our_uid = read_prproj(ours_path)
    ref_root, ref_id, ref_uid = read_prproj(ref_path)
    ours = sequence_snapshot(our_root, our_id, our_uid)
    refs = sequence_snapshot(ref_root, ref_id, ref_uid)
    ref_by_name = {seq["name"]: seq for seq in refs}
    print(f"Comparaison avec la référence « {os.path.basename(ref_path)} » :")
    for seq in ours:
        ref = ref_by_name.get(seq["name"]) or (refs[0] if len(refs) == 1 else None)
        if ref is None:
            print(f"  « {seq['name']} » : pas de séquence correspondante dans la référence")
            continue
        for ours_track, ref_track in zip(seq["tracks"], ref["tracks"]):
            if ours_track["kind"] != ref_track["kind"]:
                continue
            ours_items, ref_items = ours_track["items"], ref_track["items"]
            if len(ours_items) != len(ref_items):
                print(f"  piste {ours_track['kind']} : {len(ours_items)} clip(s) contre "
                      f"{len(ref_items)} dans la référence — à contrôler")
                continue
            max_shift = 0
            same_values = total_values = 0
            mismatches = []
            for ours_item, ref_item in zip(ours_items, ref_items):
                max_shift = max(max_shift, abs(ours_item["start"] - ref_item["start"]),
                                abs(ours_item["end"] - ref_item["end"]))
                for slot in (0, 5):
                    ours_point = parse_point(ours_item["params"].get(slot, {}).get("start"))
                    ref_point = parse_point(ref_item["params"].get(slot, {}).get("start"))
                    if ours_point is None or ref_point is None:
                        continue
                    total_values += 1
                    if (abs(ours_point[0] - ref_point[0]) < 1e-6
                            and abs(ours_point[1] - ref_point[1]) < 1e-6):
                        same_values += 1
                    elif len(mismatches) < 3:
                        mismatches.append(f"Pos/Anchor {ours_point} contre {ref_point}")
            print(f"  piste {ours_track['kind']} : {len(ours_items)} clip(s) ; Position/Anchor "
                  f"identiques {same_values}/{total_values} (valeurs normalisées, tol 1e-6) ; "
                  f"écart de temps max {max_shift / TICKS_PER_SECOND:.3f} s "
                  f"(la référence a subi le décalage 24→25 fps de la chaîne Adobe)")
            for line in mismatches:
                print(f"      écart : {line}")


# ------------------------------------------------------- compatibilité Premiere


def premiere_skip_reason(ec_path: str) -> str | None:
    """Raison de ne pas exporter ce .ecproj en .prproj, sinon None.

    Premiere ne reprend ni masques ni effets (propres à EffectCraft) : ces projets ne
    sont exportés qu'en .aep, pour ne pas produire un .prproj incomplet.
    """
    try:
        with open(ec_path, "r", encoding="utf-8") as handle:
            return conv.premiere_incompatibilities(json.load(handle))
    except Exception:
        return None


def remove_stale_prproj(ec_path: str) -> str | None:
    """Supprime le .prproj voisin d'un projet non exportable ; retourne le chemin supprimé."""
    stale = os.path.splitext(ec_path)[0] + ".prproj"
    if os.path.isfile(stale):
        os.remove(stale)
        return stale
    return None


def report_skip(ec_path: str, reason: str, log) -> None:
    """Signale un projet sauté et retire le .prproj obsolète éventuel."""
    removed = remove_stale_prproj(ec_path)
    print(f"  ignoré : {reason} propre(s) à EffectCraft, non repris par Premiere "
          f"— export .aep uniquement" + (" ; .prproj obsolète supprimé" if removed else ""))
    log(f"[prproj] {os.path.basename(ec_path)} : ignoré ({reason})"
        + (" ; .prproj obsolète supprimé" if removed else ""))


# ------------------------------------------------------------------- bureau


def log_line(message: str) -> None:
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as handle:
            handle.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}\n")
    except OSError:
        pass


def scan_root(root: str, filters) -> list[str]:
    """Dossiers projet enfants directs de `root` — même détection que le panel et que
    l'export .aep : nom contenant un des filtres (insensible à la casse) et sous-dossier `docs/`."""
    needles = [needle.strip().lower() for needle in filters if len(needle.strip()) >= 2]
    folders = []
    try:
        entries = list(os.scandir(root))
    except OSError:
        return folders
    for entry in entries:
        if entry.name.startswith(".") or not entry.is_dir(follow_symlinks=False):
            continue
        if needles and not any(needle in entry.name.lower() for needle in needles):
            continue
        if not os.path.isdir(os.path.join(entry.path, "docs")):
            continue
        folders.append(entry.path)
    return sorted(folders)


def collect_ecproj(folders) -> list[str]:
    found = set()
    for folder in folders:
        for dirpath, dirnames, filenames in os.walk(folder, onerror=lambda exc: None):
            dirnames[:] = [name for name in dirnames if not name.startswith(".")]
            for name in filenames:
                if name.lower().endswith(".ecproj"):
                    found.add(os.path.join(dirpath, name))
    return sorted(found)


def run_desktop(args, maps) -> int:
    gui = (not args.no_gui
           and shutil.which("zenity") is not None
           and bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")))
    if not os.path.isdir(ROOT):
        print(f"Racine introuvable : {ROOT}", file=sys.stderr)
        return 2
    files = collect_ecproj(scan_root(ROOT, NAME_FILTERS))
    log_line(f"--- {len(files)} projet(s), mapping={maps or 'aucun'} ---")
    if not files:
        text = f"Aucun .ecproj trouvé sous {ROOT}."
        if gui:
            subprocess.run(["zenity", "--info", "--title", "Export PRPROJ", "--text", text])
        else:
            print(text)
        return 0
    progress = None
    if gui:
        progress = subprocess.Popen(
            ["zenity", "--progress", "--title", "Export PRPROJ",
             "--text", "Conversion des .ecproj…", "--percentage=0", "--auto-close"],
            stdin=subprocess.PIPE, text=True)
    conversions = skipped = failures = 0
    for index, src in enumerate(files):
        if progress is not None:
            try:
                progress.stdin.write(f"#{int(index * 100 / len(files))}\n")
                progress.stdin.write(f"{os.path.basename(src)}\n")
                progress.stdin.flush()
            except (BrokenPipeError, AttributeError):
                progress = None
        out = os.path.splitext(src)[0] + ".prproj"
        reason = None if args.force else premiere_skip_reason(src)
        if reason:
            skipped += 1
            report_skip(src, reason, log_line)
            continue
        try:
            report = convert(src, out, maps, args.skip_missing, args.xml_dump, log_line)
            conversions += 1
            print(f"OK  {src} → {out} ({report['items']} item(s))")
        except Exception as exc:  # pragma: no cover - dépend des données
            failures += 1
            print(f"ÉCHEC {src} : {exc}", file=sys.stderr)
            log_line(f"ÉCHEC {src} : {exc}")
    if progress is not None:
        try:
            progress.stdin.close()
        except (BrokenPipeError, AttributeError):
            pass
        progress.wait()
    summary = f"{conversions} projet(s) converti(s), {failures} échec(s)"
    if skipped:
        summary += (f", {skipped} ignoré(s) (masques/effets : export .aep uniquement)")
    summary += "."
    if gui:
        subprocess.run(["zenity", "--info", "--title", "Export PRPROJ", "--text", summary])
    else:
        print(summary)
    return 1 if failures else 0


# --------------------------------------------------------------------- main


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convertit un projet EffectCraft (.ecproj) en projet Premiere Pro (.prproj).")
    parser.add_argument("input", nargs="?", help="fichier .ecproj, ou dossier avec --all")
    parser.add_argument("-o", "--out", help="chemin du .prproj de sortie")
    parser.add_argument("--all", action="store_true", help="convertit tous les *.ecproj du dossier")
    parser.add_argument("--path-map", action="append", default=None, metavar="SRC=DST",
                        help="réécrit le préfixe des chemins de médias (répétable)")
    parser.add_argument("--no-path-map", action="store_true",
                        help="n'applique aucune réécriture (chemins Linux écrits tels quels)")
    parser.add_argument("--skip-missing", action="store_true",
                        help="résume les médias absents au lieu de les lister")
    parser.add_argument("--force", action="store_true",
                        help="exporte même si le projet a des masques/effets (le .prproj "
                             "sera alors incomplet : Premiere ne les reprend pas)")
    parser.add_argument("--verify", action="store_true", help="relit le .prproj produit")
    parser.add_argument("--compare-with", metavar="REF.prproj",
                        help="compare le résultat à un .prproj de référence")
    parser.add_argument("--xml-dump", action="store_true",
                        help="écrit aussi le XML décompressé à côté du .prproj")
    parser.add_argument("--no-gui", action="store_true",
                        help="force la sortie texte (mode bureau sans fenêtre)")
    args = parser.parse_args()

    if args.no_path_map and args.path_map:
        parser.error("--path-map et --no-path-map sont incompatibles")
    if args.path_map is None:
        # sans indication : mapping du mode bureau (les .prproj sont ouverts sous Windows)
        maps: list[tuple[str, str]] = [] if args.no_path_map else list(PATH_MAP)
    else:
        maps = []
        for mapping in args.path_map:
            if "=" not in mapping:
                parser.error(f"--path-map attend SRC=DST, reçu : {mapping}")
            src, dst = mapping.split("=", 1)
            maps.append((src, dst))

    if not args.input:
        return run_desktop(args, maps)

    jobs: list[tuple[str, str]] = []
    if args.all:
        if not os.path.isdir(args.input):
            parser.error("--all attend un dossier")
        if args.out:
            parser.error("-o et --all sont incompatibles")
        jobs = [(path, os.path.splitext(path)[0] + ".prproj")
                for path in collect_ecproj([args.input])]
    else:
        if not os.path.isfile(args.input):
            parser.error(f"fichier introuvable : {args.input}")
        jobs.append((args.input, args.out or os.path.splitext(args.input)[0] + ".prproj"))

    if not jobs:
        print("Aucun .ecproj à convertir.")
        return 0

    log_line(f"--- {len(jobs)} projet(s), mapping={maps or 'aucun'} ---")
    failures = 0
    skipped = 0
    for src, out in jobs:
        print(f"→ {os.path.basename(src)}  ⇒  {out}")
        reason = None if args.force else premiere_skip_reason(src)
        if reason:
            skipped += 1
            report_skip(src, reason, log_line)
            continue
        try:
            report = convert(src, out, maps, args.skip_missing, args.xml_dump, log_line)
        except Exception as exc:  # pragma: no cover - dépend des données
            failures += 1
            print(f"  ÉCHEC : {exc}", file=sys.stderr)
            log_line(f"ÉCHEC {src} : {exc}")
            continue
        detail = (f"{report['media']} média(s), {report['tracks']} piste(s), "
                  f"{report['items']} item(s)")
        if report["audio_items"]:
            detail += f", {report['audio_items']} audio"
        if report["keyframed"]:
            detail += f", {report['keyframed']} animé(s)"
        print(f"  {detail} → {out}")
        if report["missing"]:
            if args.skip_missing:
                print(f"  ! {len(report['missing'])} média(s) absent(s)")
            else:
                for line in report["missing"]:
                    print(f"  ! {line}")
        for line in report["warnings"]:
            print(f"  ! {line}")
        if args.verify:
            try:
                print(verify_summary(out))
            except Exception as exc:
                print(f"  vérification impossible : {exc}", file=sys.stderr)
        if args.compare_with:
            try:
                compare_prproj(out, args.compare_with)
            except Exception as exc:
                print(f"  comparaison impossible : {exc}", file=sys.stderr)

    if skipped:
        print(f"{skipped} projet(s) ignoré(s) (masques/effets : export .aep uniquement).")
        log_line(f"{skipped} projet(s) ignoré(s) (masques/effets)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
