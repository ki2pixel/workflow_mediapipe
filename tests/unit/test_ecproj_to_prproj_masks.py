"""Masques Premiere et Gaussian Blur à l'export .prproj (outil MediaSolution-EC).

Le blob de tracé « golden » vient d'un projet Premiere 2026 de référence (masque rectangle
à 4 sommets créé dans l'application) : le ré-encodage doit être identique octet pour octet.
L'outil vit hors paquet (`scripts/MediaSolution-EC/tools/`) et est importé par chemin.
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "scripts" / "MediaSolution-EC" / "tools"
sys.path.insert(0, str(TOOLS))

import ecproj_to_prproj as pp  # noqa: E402  (outil hors paquet)

# Blob « Path » d'un rectangle 4 sommets (frame 1080×1920), relevé sur le projet de
# référence (134 octets décodés) — round-trip octet pour octet exigé.
GOLDEN_PATH_BLOB = (
    "AgAAAAEAAABWeQAAAAIAAAAEAAAAAAAAAMqJHD9IAU0+yokcP0gBTT7KiRw/SAFNPgAAAACqE4A/"
    "SAFNPqoTgD9IAU0+qhOAP0gBTT4AAAAAqhOAPyejIj+qE4A/J6MiP6oTgD8noyI/AAAAAMqJHD8n"
    "oyI/yokcPyejIj/KiRw/J6MiPwE="
)
GOLDEN_VERTICES = [(0.61147749, 0.20020020), (1.00060010, 0.20020020),
                   (1.00060010, 0.63530201), (0.61147749, 0.63530201)]

RECT_PX = [(200.0, 100.0), (900.0, 100.0), (900.0, 900.0), (200.0, 900.0)]
RECT_CENTER = (550.0 / 1080.0, 500.0 / 1920.0)


# ------------------------------------------------------------------ fixtures .ecproj


def mask_node(vertices, mode="Add", inverted=False, feather=(0.0, 0.0), closed=True,
              feather_points=None):
    path_value = {
        "vertices": [list(v) for v in vertices],
        "in_tangents": [[0.0, 0.0]] * len(vertices),
        "out_tangents": [[0.0, 0.0]] * len(vertices),
        "closed": closed,
    }
    if feather_points:
        path_value["feather"] = feather_points
    return {
        "node": "Group", "uid": 42, "match": "mask", "name": "Mask 1",
        "kind": {"kind": "Mask", "mode": mode, "inverted": inverted,
                 "color": [177, 180, 79], "locked": False,
                 "motion_blur": "SameAsLayer", "feather_falloff": "Smooth",
                 "roto_bezier": False},
        "enabled": True,
        "children": [
            {"node": "Prop", "uid": 43, "match": "path", "name": "Mask Path",
             "value": {"t": "Path", "v": path_value}},
            {"node": "Prop", "uid": 44, "match": "feather", "name": "Mask Feather",
             "value": {"t": "Vec2", "v": list(feather)}},
            {"node": "Prop", "uid": 45, "match": "opacity", "name": "Mask Opacity",
             "value": {"t": "Scalar", "v": 100.0}},
            {"node": "Prop", "uid": 46, "match": "expansion", "name": "Mask Expansion",
             "value": {"t": "Scalar", "v": 0.0}},
        ],
    }


def blur_node(effect="ec.blur.gaussian", blurriness=30.0):
    return {
        "node": "Prop", "uid": 47, "match": "blur", "name": "Gaussian Blur", "enabled": True,
        "kind": {"kind": "Effect", "effect": effect},
        "children": [
            {"match": "blurriness", "value": {"t": "Scalar", "v": blurriness}},
            {"match": "dimensions", "value": {"t": "Scalar", "v": 0.0}},
            {"match": "repeatEdge", "value": {"t": "Scalar", "v": False}},
        ],
    }


def ec_project(masks=(), effects=(), width=1080, height=1920):
    props_children = []
    if masks:
        props_children.append({"node": "Group", "uid": 41, "match": "masks", "name": "Masks",
                               "kind": {"kind": "Plain"}, "enabled": True,
                               "children": list(masks)})
    if effects:
        props_children.append({"node": "Group", "uid": 48, "match": "effects", "name": "Effects",
                               "kind": {"kind": "Plain"}, "enabled": True,
                               "children": list(effects)})
    layer = {
        "id": 11, "name": "clip.mp4", "label": "Aqua", "comment": "",
        "source": {"type": "Footage", "item": 1},
        "start_time": 0, "in_point": 0, "out_point": 254016000000,
        "stretch": 100.0,
        "switches": {"video": True, "audio": False, "solo": False, "locked": False,
                     "effects": True, "motion_blur": False, "adjustment": False,
                     "three_d": False},
        "blend_mode": "Normal", "preserve_transparency": False, "track_matte": None,
        "parent": None, "markers": [], "auto_orient": "Off",
        "props": {"uid": 40, "match": "layer", "name": "clip.mp4",
                  "kind": {"kind": "Plain"}, "enabled": True, "children": props_children},
    }
    return {
        "savedBy": "0.8.0", "schema": 2,
        "settings": {"audio_sample_rate": 48000},
        "items": {
            "1": {"id": 1, "name": "clip.mp4", "label": "Aqua", "parent": None,
                  "kind": {"type": "Footage", "path": "/tmp/clip.mp4", "kind": "Video",
                           "width": width, "height": height, "pixel_aspect": 1.0,
                           "frame_rate": {"num": 25, "den": 1}, "duration": 254016000000,
                           "has_video": True, "has_audio": False, "codec": "H.264 (High)"}},
            "2": {"id": 2, "name": "clip_9x16", "parent": None,
                  "kind": {"type": "Comp", "width": width, "height": height,
                           "pixel_aspect": 1.0, "frame_rate": {"num": 25, "den": 1},
                           "duration": 254016000000, "display_start": 0,
                           "background": [0, 0, 0], "work_area": [0, 254016000000],
                           "layers": [layer], "markers": [], "renderer": "Classic3D",
                           "shutter_angle": 180.0, "enable_motion_blur": True}},
        },
        "next_id": 99,
    }


def convert(tmp_path, ec):
    src = tmp_path / "clip_9x16.ecproj"
    src.write_text(json.dumps(ec), encoding="utf-8")
    out = tmp_path / "clip_9x16.prproj"
    pp.convert(str(src), str(out), [], False, True, lambda message: None)
    root, by_id, by_uid = pp.read_prproj(str(out))
    return out, Path(str(out) + ".xml").read_text(encoding="utf-8"), (root, by_id, by_uid)


def params_by_id(root, by_id, filter_obj):
    return {int(by_id[ref.get("ObjectRef")].findtext("ParameterID")):
            by_id[ref.get("ObjectRef")]
            for ref in filter_obj.findall("Component/Params/Param")}


def filters_by_match(root, match):
    return [element for element in root if element.tag == "VideoFilterComponent"
            and element.findtext("MatchName") == match]


# ------------------------------------------------------------------------ codec tracé


def test_golden_path_blob_round_trips_byte_for_byte():
    # Given : le blob de tracé d'un projet Premiere 2026 de référence
    # When : il est décodé puis ré-encodé tel quel
    points = pp.decode_mask_path(GOLDEN_PATH_BLOB)
    packed = pp.pack_mask_path(points, closed=True)
    # Then : quatre sommets à angles vifs, et un blob identique octet pour octet
    assert len(points) == 4
    for point in points:
        assert (point[0], point[1]) == (point[2], point[3]) == (point[4], point[5])
    assert packed == GOLDEN_PATH_BLOB
    assert len(base64.b64decode(GOLDEN_PATH_BLOB)) == 134


def test_golden_path_blob_vertices_match_reference():
    # Given : le blob de référence, exprimé en pixels d'une frame 1080×1920
    expected_px = [(x * 1080.0, y * 1920.0) for x, y in GOLDEN_VERTICES]
    # When : l'encodeur reprend ces sommets (tangentes nulles, tracé fermé)
    blob = pp.encode_mask_path(expected_px, [(0.0, 0.0)] * 4, [(0.0, 0.0)] * 4,
                               True, 1080.0, 1920.0)
    # Then : le blob produit est celui de la référence
    assert blob == GOLDEN_PATH_BLOB


def test_encode_mask_path_keeps_tangent_offsets_and_open_flag():
    # Given : un tracé ouvert à deux sommets avec des tangentes asymétriques
    vertices = [(100.0, 100.0), (500.0, 100.0)]
    in_tangents = [(0.0, 0.0), (-50.0, 0.0)]
    out_tangents = [(50.0, 0.0), (0.0, 0.0)]
    # When : il est encodé puis relu
    blob = pp.encode_mask_path(vertices, in_tangents, out_tangents, False, 1000.0, 1000.0)
    points = pp.decode_mask_path(blob)
    # Then : les trois points de chaque sommet sont en absolu et le drapeau est « ouvert »
    assert points[0][2] == pytest.approx(0.1) and points[0][4] == pytest.approx(0.15)
    assert points[1][0] == pytest.approx(0.45) and points[1][2] == pytest.approx(0.5)
    assert base64.b64decode(blob)[-1] == 0


# ------------------------------------------------------------------------ assemblage


def test_convert_writes_mask_under_opacity_and_blur_component(tmp_path):
    # Given : un projet .ecproj avec un masque rectangle « Add » et un Gaussian Blur
    ec = ec_project(masks=[mask_node(RECT_PX)], effects=[blur_node(blurriness=42.0)])
    # When : il est converti en .prproj
    _out, _xml, (root, by_id, by_uid) = convert(tmp_path, ec)
    # Then : toutes les références sont résolues et le filtre masque est complet
    assert pp.check_references(root, by_id, by_uid) == []
    masks = filters_by_match(root, pp.MASK2_MATCH_NAME)
    assert len(masks) == 1
    mask = masks[0]
    params = params_by_id(root, by_id, mask)
    assert len(params) == 27
    points = pp.decode_mask_path(params[7].find("StartKeyframeValue").text)
    assert len(points) == 4
    for point, (px, py) in zip(points, RECT_PX):
        assert point[2] * 1080.0 == pytest.approx(px, abs=1e-3)
        assert point[3] * 1920.0 == pytest.approx(py, abs=1e-3)
    # Position/Anchor = centre de la bounding-box, « Type » = Add (2), Feather = 0
    assert params[9].findtext("StartKeyframe").split(",")[1] == "0.5092592592592593:0.2604166666666667"
    assert params[10].findtext("StartKeyframe").split(",")[1] == "0.5092592592592593:0.2604166666666667"
    assert params[22].findtext("StartKeyframe") == "-91445760000000000,2,0,0,0,0,0,0"
    assert params[14].findtext("StartKeyframe") == "-91445760000000000,0.,0,0,0,0,0,0"
    # les payloads portent leur clé BinaryHash (sans elle, Premiere les ignore)
    assert params[7].find("StartKeyframeValue").get("BinaryHash")
    assert mask.find("PremiereFilterPrivateData").get("BinaryHash")
    # le masque est un sous-composant de l'Opacité explicite
    opacities = filters_by_match(root, "AE.ADBE Opacity")
    assert len(opacities) == 1
    sub_refs = [ref.get("ObjectRef") for ref in opacities[0].findall("SubComponents/SubComponent")]
    assert sub_refs == [mask.get("ObjectID")]
    # la chaîne porte [Opacité, Motion, Gaussian Blur] et plus DefaultOpacity
    chains = [element for element in root if element.tag == "VideoComponentChain"
              and any(component.get("ObjectRef") == opacities[0].get("ObjectID")
                      for component in element.findall("ComponentChain/Components/Component"))]
    assert len(chains) == 1
    assert chains[0].find("DefaultOpacity") is None
    components = chains[0].findall("ComponentChain/Components/Component")
    assert [int(component.get("Index")) for component in components] == [0, 1, 2]
    blurs = filters_by_match(root, pp.PP_BLUR_MATCH_NAME)
    assert len(blurs) == 1
    assert components[2].get("ObjectRef") == blurs[0].get("ObjectID")
    assert len(blurs[0].findall("Component/Params/Param")) == 18
    blur_params = params_by_id(root, by_id, blurs[0])
    assert ",42." in blur_params[3].findtext("StartKeyframe")


def test_convert_normalizes_mask_by_source_size(tmp_path):
    # Given : une comp 1080×1920 dont la source est un média paysage 1920×1080
    # (les masques .ecproj sont en pixels source, comme dans After Effects)
    ec = ec_project(masks=[mask_node(RECT_PX)], width=1080, height=1920)
    ec["items"]["1"]["kind"]["width"] = 1920
    ec["items"]["1"]["kind"]["height"] = 1080
    # When : il est converti
    _out, _xml, (root, by_id, _by_uid) = convert(tmp_path, ec)
    # Then : le tracé et le centre sont normalisés par la source, pas par la comp
    mask = filters_by_match(root, pp.MASK2_MATCH_NAME)[0]
    params = params_by_id(root, by_id, mask)
    points = pp.decode_mask_path(params[7].find("StartKeyframeValue").text)
    assert points[0][2] * 1920.0 == pytest.approx(RECT_PX[0][0], abs=1e-3)
    assert points[0][3] * 1080.0 == pytest.approx(RECT_PX[0][1], abs=1e-3)
    assert points[2][2] * 1920.0 == pytest.approx(RECT_PX[2][0], abs=1e-3)
    assert points[2][3] * 1080.0 == pytest.approx(RECT_PX[2][1], abs=1e-3)
    center = params[9].findtext("StartKeyframe").split(",")[1].split(":")
    assert float(center[0]) * 1920.0 == pytest.approx(550.0, abs=1e-6)
    assert float(center[1]) * 1080.0 == pytest.approx(500.0, abs=1e-6)


def test_convert_writes_empty_path_blob_for_vertex_less_mask(tmp_path):
    # Given : un masque sans aucun sommet mais fermé (EffectCraft le découpe à vide)
    ec = ec_project(masks=[mask_node([])])
    # When : il est converti
    _out, _xml, (root, by_id, by_uid) = convert(tmp_path, ec)
    # Then : il prend l'état par défaut d'Adobe (aucun tracé, Type 0, 0:0)
    assert pp.check_references(root, by_id, by_uid) == []
    mask = filters_by_match(root, pp.MASK2_MATCH_NAME)[0]
    params = params_by_id(root, by_id, mask)
    assert params[7].find("StartKeyframeValue").text == pp.MASK_EMPTY_PATH
    assert params[7].find("StartKeyframeValue").get("BinaryHash") == "5b3d1e1b-2b68-8c23-e1d2-827a00000014"
    assert params[22].findtext("StartKeyframe") == "-91445760000000000,0,0,0,0,0,0,0"
    assert params[9].findtext("StartKeyframe").split(",")[1] == "0:0"
    assert pp.decode_mask_path(pp.MASK_EMPTY_PATH) == []


def test_convert_skips_masks_effectcraft_does_not_apply(tmp_path):
    # Given : un masque au tracé ouvert et un masque en mode None — dans EffectCraft, aucun
    # des deux ne fait de transparence (le calque s'affiche entier)
    ec = ec_project(masks=[mask_node(RECT_PX, closed=False),
                           mask_node(RECT_PX, mode="None")])
    # When : il est converti
    _out, _xml, (root, by_id, by_uid) = convert(tmp_path, ec)
    # Then : aucun filtre masque ni Opacité explicite n'est écrit, et le clip garde
    # l'Opacité intrinsèque de Premiere (il s'affiche entier, comme dans EffectCraft)
    assert pp.check_references(root, by_id, by_uid) == []
    assert filters_by_match(root, pp.MASK2_MATCH_NAME) == []
    assert filters_by_match(root, "AE.ADBE Opacity") == []
    chains = [element for element in root if element.tag == "VideoComponentChain"]
    assert any(chain.find("DefaultOpacity") is not None for chain in chains)


def test_skip_reason_ignores_masks_effectcraft_does_not_apply(tmp_path):
    # Given : les mêmes masques sans découpage (tracé ouvert, mode None)
    path = write_ec(tmp_path, ec_project(masks=[mask_node(RECT_PX, closed=False),
                                                 mask_node(RECT_PX, mode="None")]))
    # When : la raison de ne pas exporter est demandée
    reason = pp.premiere_skip_reason(path)
    # Then : le projet reste exportable (ces masques ne sont pas repris, comme dans EC)
    assert reason is None


def test_skip_reason_blocks_variable_feather_masks(tmp_path):
    # Given : un masque à feather variable (points de feather sur le tracé)
    mask = mask_node(RECT_PX, feather_points=[[50.0, 0.0], [0.0, 0.0],
                                              [0.0, 0.0], [0.0, 0.0]])
    path = write_ec(tmp_path, ec_project(masks=[mask]))
    # When : la raison de ne pas exporter est demandée
    reason = pp.premiere_skip_reason(path)
    # Then : l'export .prproj est refusé (Premiere n'a qu'un feather scalaire)
    assert reason is not None
    assert "feather variable" in reason


def test_convert_uses_greatest_axis_for_mask_feather(tmp_path):
    # Given : un masque avec un feather non uniforme (Vec2, comme EffectCraft)
    ec = ec_project(masks=[mask_node(RECT_PX, feather=(12.0, 40.0))])
    # When : il est converti
    _out, _xml, (root, by_id, _by_uid) = convert(tmp_path, ec)
    # Then : Premiere ne prend qu'un scalaire : le plus grand des deux axes
    mask = filters_by_match(root, pp.MASK2_MATCH_NAME)[0]
    params = params_by_id(root, by_id, mask)
    assert params[14].findtext("StartKeyframe") == "-91445760000000000,40.,0,0,0,0,0,0"


# ----------------------------------------------------------------------------- skip


def write_ec(tmp_path, ec):
    path = tmp_path / "projet.ecproj"
    path.write_text(json.dumps(ec), encoding="utf-8")
    return str(path)


def test_skip_reason_is_none_for_supported_masks_and_blur(tmp_path):
    # Given : un projet avec masque « Add » et Gaussian Blur (cas d'usage courant)
    path = write_ec(tmp_path, ec_project(masks=[mask_node(RECT_PX)],
                                         effects=[blur_node()]))
    # When : la raison de ne pas exporter est demandée
    reason = pp.premiere_skip_reason(path)
    # Then : le projet est exportable en .prproj
    assert reason is None


@pytest.mark.parametrize("mask", [
    mask_node(RECT_PX, mode="Subtract"),
    mask_node(RECT_PX, inverted=True),
])
def test_skip_reason_blocks_masks_out_of_scope(tmp_path, mask):
    # Given : un masque hors périmètre v1 (autre mode, inversion)
    path = write_ec(tmp_path, ec_project(masks=[mask]))
    # When : la raison de ne pas exporter est demandée
    reason = pp.premiere_skip_reason(path)
    # Then : l'export .prproj est refusé avec une raison explicite
    assert reason is not None
    assert "masque" in reason


def test_skip_reason_blocks_unknown_effects(tmp_path):
    # Given : un effet absent de la table Premiere
    path = write_ec(tmp_path, ec_project(effects=[blur_node(effect="ec.glitch.vhs")]))
    # When : la raison de ne pas exporter est demandée
    reason = pp.premiere_skip_reason(path)
    # Then : l'export .prproj est refusé (effet non repris)
    assert reason is not None
    assert "effet" in reason
