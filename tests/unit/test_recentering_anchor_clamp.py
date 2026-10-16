#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests du bornage de l'ancre de recentrage (panneaux EffectCraft / CEP / Analyse-Écart).

L'ancre est exprimée en pixels de la source : avec un calque positionné au centre de la
composition, celle-ci n'est entièrement couverte que si l'ancre reste dans
[demiComp/échelle, largeurSource - demiComp/échelle]. Sans ce bornage, le recentrage
pousse le calque hors champ et laisse apparaître le fond (bug historique).

La fonction `clampAnchorToCoverage` vit dans des .jsx non importables (directives
ExtendScript, API hôte). Ces tests l'extraient donc du fichier livré et l'exécutent sous
Node : c'est bien le code expédié qui est vérifié, pas une réimplémentation.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Fichiers qui appliquent l'ancre de recentrage depuis le tracking, et nombre de sites
# de recentrage attendus (= nombre d'appels au bornage).
ANCHOR_SOURCES = (
    ("scripts/MediaSolution-EC/MediaSolution.jsx", 1),
    ("scripts/after_effects/MediaSolution-CEP/host/MediaSolution.jsx", 1),
    ("scripts/after_effects/Analyse-Écart-X-depuis-JSON-et-Label-Vidéo36_good.jsx", 2),
    ("scripts/after_effects/Media-Solution-v11.2-production.jsx", 1),
)

ANCHOR_PATHS = tuple(relative_path for relative_path, _ in ANCHOR_SOURCES)

FUNCTION_NAME = "clampAnchorToCoverage"

# Cas réels mesurés dans les projets (source 1920 px, comp 1080 px, échelle 180 %) :
# la couverture impose une ancre dans [300, 1620].
REAL_CASES = [
    (1752.5, 1080, 1920, 180, 1620.0),   # « Andy avoue… veut participer », segment 157,80-160,48 s
    (1853.2, 1080, 1920, 180, 1620.0),   # « Cynthia et Greg s'expliquent… »
    (1638.9, 1080, 1920, 180, 1620.0),
    (231.5, 1080, 1920, 180, 300.0),     # « Andy avoue… jamais été amoureux »
    (221.5, 1080, 1920, 180, 300.0),
    (1161.0, 1080, 1920, 180, 1161.0),   # segment déjà correct : inchangé
    (540.0, 1080, 1920, 180, 540.0),
    (960.0, 1080, 1920, 180, 960.0),
]


def _extract_function(source: str, name: str) -> str:
    """Extrait `function <name>(...) { ... }` du source en équilibrant les accolades."""
    match = re.search(r"function\s+" + re.escape(name) + r"\s*\(", source)
    assert match, f"fonction {name} introuvable"
    start = source.index("{", match.end() - 1)
    depth = 0
    for index in range(start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[match.start():index + 1]
    raise AssertionError(f"accolades non équilibrées pour {name}")


def _run_in_node(function_source: str, cases) -> list:
    """Exécute la fonction extraite sous Node sur les cas fournis."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("node indisponible : test du code JS ignoré")

    script = (
        function_source
        + "\nvar cases = " + json.dumps(cases) + ";\n"
        + "var out = cases.map(function (c) { return " + FUNCTION_NAME + "(c[0], c[1], c[2], c[3]); });\n"
        + "console.log(JSON.stringify(out));\n"
    )
    result = subprocess.run(
        [node, "-e", script], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"node a échoué : {result.stderr[:400]}"
    return json.loads(result.stdout.strip().splitlines()[-1])


# Variables porteuses du centre issu du tracking, selon les fichiers.
RAW_TRACKED_CENTRES = ("pick.centerX", "centerToAim", "centerX")


@pytest.mark.parametrize("relative_path,expected_calls", ANCHOR_SOURCES)
def test_no_anchor_is_set_from_a_raw_tracked_centre(relative_path, expected_calls):
    """Garde-fou de non-régression : chaque recentrage doit passer par le bornage."""
    # Given
    source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

    # When : toutes les affectations d'ancre avec une liste littérale
    offenders = []
    for match in re.finditer(r"setValue\(\[([^\]]+)\]", source):
        prefix = source[max(0, match.start() - 60):match.start()]
        if "Anchor" not in prefix:
            continue
        expression = match.group(1).strip()
        if expression.startswith(RAW_TRACKED_CENTRES):
            offenders.append(expression)

    # Then : la fonction existe et chacun des sites de recentrage l'appelle
    assert f"function {FUNCTION_NAME}(" in source
    assert source.count(f"{FUNCTION_NAME}(") >= expected_calls + 1  # définition + appels
    assert not offenders, f"{relative_path}: ancre posée sans bornage -> {offenders}"


@pytest.mark.parametrize("relative_path", ANCHOR_PATHS)
def test_clamp_keeps_the_composition_covered(relative_path):
    """Sur les valeurs réelles, l'ancre bornée reste dans la plage de couverture."""
    # Given
    source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    function_source = _extract_function(source, FUNCTION_NAME)

    # When
    results = _run_in_node(function_source, REAL_CASES)

    # Then
    for (center, comp, src, scale, expected), got in zip(REAL_CASES, results):
        assert got == pytest.approx(expected, abs=0.01), (
            f"{relative_path}: clamp({center}) = {got} au lieu de {expected}"
        )


@pytest.mark.parametrize("relative_path", ANCHOR_PATHS)
def test_clamp_covers_the_whole_range_and_is_idempotent(relative_path):
    """Toute ancre bornée couvre la composition, et rebornée elle ne bouge plus."""
    # Given
    source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    function_source = _extract_function(source, FUNCTION_NAME)
    scale_percent = 180.0
    comp_width = 1080.0
    source_width = 1920.0
    cases = [(center, comp_width, source_width, scale_percent) for center in range(0, 1921, 37)]

    # When
    results = _run_in_node(function_source, cases)
    again = _run_in_node(
        function_source,
        [(value, comp_width, source_width, scale_percent) for value in results],
    )

    # Then : le calque couvre la composition et le bornage est stable
    for value, second in zip(results, again):
        assert value == pytest.approx(second, abs=0.01)
        left_edge = comp_width / 2 - (value * scale_percent / 100)
        right_edge = left_edge + source_width * scale_percent / 100
        assert left_edge <= 0.01, f"fond visible à gauche (ancre {value})"
        assert right_edge >= comp_width - 0.01, f"fond visible à droite (ancre {value})"


@pytest.mark.parametrize("relative_path", ANCHOR_PATHS)
def test_clamp_is_safe_on_degenerate_inputs(relative_path):
    """Échelle nulle, source ou comp absente : la valeur d'entrée est conservée."""
    # Given
    source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    function_source = _extract_function(source, FUNCTION_NAME)
    cases = [
        (800.0, 1080, 1920, 0),
        (800.0, 1080, 0, 180),
        (800.0, 0, 1920, 180),
        (800.0, 1080, 1920, None),
    ]

    # When
    results = _run_in_node(function_source, cases)

    # Then
    assert results == [800.0, 800.0, 800.0, 800.0]


def test_clamp_falls_back_to_source_centre_for_a_too_small_layer():
    """Un calque plus étroit que la composition est centré (aucune ancre ne couvrirait)."""
    # Given
    source = (PROJECT_ROOT / "scripts/MediaSolution-EC/MediaSolution.jsx").read_text(encoding="utf-8")
    function_source = _extract_function(source, FUNCTION_NAME)
    cases = [(1500.0, 1920, 1080, 100)]  # comp plus large que la source

    # When
    results = _run_in_node(function_source, cases)

    # Then
    assert results == [540.0]
