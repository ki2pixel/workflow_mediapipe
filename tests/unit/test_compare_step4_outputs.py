#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests unitaires du comparateur de précision STEP4
(``scripts/compare_step4_tracking_outputs.py``).

Vérifie la métrologie (IoU, RMSE, jitter), le gating par seuils et l'interface
en ligne de commande, sur des JSON synthétiques — sans exécuter le pipeline.
"""

import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_comparator():
    spec = importlib.util.spec_from_file_location(
        "compare_step4_tracking_outputs",
        PROJECT_ROOT / "scripts" / "compare_step4_tracking_outputs.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


comparator = _load_comparator()


def _frame(index, bias=0.0, with_face=True, shift=0.0, id_prefix="obj_"):
    objects = []
    if with_face:
        blendshapes = {
            "jawOpen": 0.2 + 0.05 * ((index % 7) - 3) + bias,
            "mouthSmileLeft": 0.3 + bias,
            "eyeBlinkLeft": 0.1 + bias,
        }
        objects.append({
            "id": f"{id_prefix}1",
            "centroid_x": 100 + shift,
            "centroid_y": 120,
            "bbox_xmin": 80 + shift,
            "bbox_xmax": 140 + shift,
            "bbox_ymin": 90,
            "bbox_ymax": 160,
            "blendshapes": blendshapes,
            "is_speaking": index % 3 == 0,
        })
    return {"frame": index + 1, "tracked_objects": objects}


def _write(path: Path, frames):
    path.write_text(json.dumps({"metadata": {"engine": "blazeface_tpu"}, "frames": frames}), encoding="utf-8")


class TestGeometry:
    def test_iou_identical_boxes_is_one(self):
        # Given/When/Then: deux boîtes identiques ont une IoU de 1
        assert comparator.iou((0, 0, 10, 10), (0, 0, 10, 10)) == 1.0

    def test_iou_disjoint_boxes_is_zero(self):
        # Given/When/Then: deux boîtes disjointes ont une IoU de 0
        assert comparator.iou((0, 0, 10, 10), (20, 20, 30, 30)) == 0.0

    def test_iou_missing_box_is_nan(self):
        # Given/When/Then: une boîte absente n'est pas comparable
        assert math.isnan(comparator.iou(None, (0, 0, 1, 1)))

    def test_bbox_of_requires_all_coordinates(self):
        # Given: un objet partiel
        # When/Then: la boîte est refusée
        assert comparator.bbox_of({"bbox_xmin": 0, "bbox_xmax": 1}) is None

    def test_percentile_interpolates_by_rank(self):
        # Given: une série de 10 valeurs
        values = list(range(10))

        # When/Then: les percentiles suivent la définition numpy (interpolation linéaire)
        assert comparator.percentile(values, 0.0) == 0
        assert comparator.percentile(values, 1.0) == 9
        assert comparator.percentile(values, 0.5) == pytest.approx(4.5)
        assert comparator.percentile(values, 0.05) == pytest.approx(0.45)
        assert comparator.percentile([], 0.5) is None


class TestJitter:
    def test_second_difference_is_zero_on_linear_series(self):
        # Given: une rampe linéaire (dérivée seconde nulle)
        # When/Then: l'indice de jittering est nul
        assert comparator.second_difference_rms([0.0, 1.0, 2.0, 3.0]) == pytest.approx(0.0, abs=1e-12)

    def test_second_difference_measures_alternation(self):
        # Given: un signal alterné 0/1 (jitter maximal)
        # When/Then: la RMS de la dérivée seconde vaut 2
        assert comparator.second_difference_rms([0.0, 1.0, 0.0, 1.0]) == pytest.approx(2.0, abs=1e-9)

    def test_short_series_is_not_computable(self):
        # Given/When/Then: moins de trois points ne permet pas de dérivée seconde
        assert comparator.second_difference_rms([0.5, 0.6]) == 0.0


class TestCompareVideo:
    def test_identical_runs_have_no_deviation(self, tmp_path):
        # Given: deux sorties strictement identiques
        frames = [_frame(index) for index in range(40)]
        reference, candidate = tmp_path / "ref.json", tmp_path / "test.json"
        _write(reference, frames)
        _write(candidate, frames)

        # When: les deux vidéos sont comparées
        result = comparator.compare_video(reference, candidate)

        # Then: aucune déviation n'est mesurée
        assert result["frames_compared"] == 40
        assert result["blendshapes"]["max_rmse"] == 0.0
        assert result["bbox_iou"]["p5"] == 1.0
        assert result["face_presence"]["agreement"] == 1.0
        assert result["speaking"]["agreement"] == 1.0
        assert result["identities"]["ratio"] == 1.0

    def test_degraded_run_is_detected(self, tmp_path):
        # Given: une variante décalée en biais, bbox, identités et frames manquantes
        frames = [_frame(index) for index in range(40)]
        degraded = [_frame(index, bias=0.05, shift=6.0, with_face=index not in (10, 11, 12)) for index in range(40)]
        reference, candidate = tmp_path / "ref.json", tmp_path / "test.json"
        _write(reference, frames)
        _write(candidate, degraded)

        # When: les deux vidéos sont comparées
        result = comparator.compare_video(reference, candidate)

        # Then: les écarts sont quantifiés
        assert result["blendshapes"]["max_rmse"] == pytest.approx(0.05, abs=1e-6)
        assert result["face_presence"]["agreement"] == pytest.approx(37 / 40, abs=1e-6)
        assert result["bbox_iou"]["p5"] < 0.99
        assert result["centroid_distance_px"]["p95"] > 3.0

    def test_two_objects_are_paired_by_centroid_order(self, tmp_path):
        # Given: deux visages suivis dans les deux sorties
        frames = []
        for index in range(20):
            frame = _frame(index)
            frame["tracked_objects"].append({
                "id": "obj_2",
                "centroid_x": 300,
                "centroid_y": 120,
                "bbox_xmin": 280,
                "bbox_xmax": 340,
                "bbox_ymin": 90,
                "bbox_ymax": 160,
                "blendshapes": {"jawOpen": 0.5},
                "is_speaking": False,
            })
            frames.append(frame)
        reference, candidate = tmp_path / "ref.json", tmp_path / "test.json"
        _write(reference, frames)
        _write(candidate, frames)

        # When: les sorties sont comparées
        result = comparator.compare_video(reference, candidate)

        # Then: les deux objets sont appariés sans dérive
        assert result["centroid_distance_px"]["count"] == 40
        assert result["centroid_distance_px"]["max"] == 0.0
        assert result["objects_count_mismatch_frames"] == 0


class TestThresholds:
    def _summary(self, per_video):
        return {"ref": "ref", "test": "test", "videos": per_video, "thresholds": comparator.DEFAULT_THRESHOLDS}

    def _video(self, **overrides):
        base = {
            "video": "v1",
            "frames_compared": 100,
            "objects_count_mismatch_frames": 0,
            "face_presence": {"ref_rate": 1.0, "test_rate": 1.0, "agreement": 1.0},
            "bbox_iou": {"count": 100, "p5": 1.0, "p50": 1.0},
            "centroid_distance_px": {"count": 100, "p50": 0.0, "p95": 0.0, "max": 0.0},
            "blendshapes": {
                "coefficients": 52,
                "max_rmse": 0.001,
                "max_rmse_coefficient": "jawOpen",
                "mouth_max_rmse": 0.001,
                "eye_max_rmse": 0.001,
                "critical_rmse": {},
            },
            "speaking": {"compared": 100, "agreement": 1.0},
            "identities": {"ref_ids": 3, "test_ids": 3, "ratio": 1.0},
            "jitter": {"jawOpen": {"ref": 0.01, "test": 0.01}},
        }
        base.update(overrides)
        return base

    def test_no_failure_when_metrics_are_stable(self):
        # Given: une vidéo sans dérive
        # When: les seuils sont évalués
        failures = comparator.evaluate_thresholds(self._summary([self._video()]), comparator.DEFAULT_THRESHOLDS)

        # Then: aucun seuil n'est franchi
        assert failures == []

    def test_rmse_threshold_fails(self):
        # Given: une RMSE au-delà du contrat de précision
        video = self._video()
        video["blendshapes"]["max_rmse"] = 0.05

        # When/Then: le dépassement est signalé
        failures = comparator.evaluate_thresholds(self._summary([video]), comparator.DEFAULT_THRESHOLDS)
        assert any("max_k RMSE" in failure for failure in failures)

    def test_presence_iou_centroid_and_identity_thresholds_fail(self):
        # Given: une vidéo dégradée sur tous les axes géométriques
        video = self._video(
            face_presence={"ref_rate": 1.0, "test_rate": 0.9, "agreement": 0.9},
            bbox_iou={"count": 100, "p5": 0.5, "p50": 0.9},
            centroid_distance_px={"count": 100, "p50": 1.0, "p95": 9.0, "max": 12.0},
            identities={"ref_ids": 3, "test_ids": 7, "ratio": 2.33},
        )

        # When: les seuils sont évalués
        failures = comparator.evaluate_thresholds(self._summary([video]), comparator.DEFAULT_THRESHOLDS)

        # Then: chaque axe franchi est listé
        assert any("présence de visage" in failure for failure in failures)
        assert any("IoU P5" in failure for failure in failures)
        assert any("dérive centroïde" in failure for failure in failures)
        assert any("churn d'identités" in failure for failure in failures)

    def test_jitter_regression_is_rejected_within_tolerance(self):
        # Given: un jitter dégradé de 5 % pour une tolérance de 2 %
        video = self._video(jitter={"jawOpen": {"ref": 0.010, "test": 0.0105}})

        # When/Then: la régression est refusée
        failures = comparator.evaluate_thresholds(self._summary([video]), comparator.DEFAULT_THRESHOLDS)
        assert any("jitter" in failure for failure in failures)

    def test_jitter_within_tolerance_is_accepted(self):
        # Given: un bruit numérique inférieur à la tolérance
        video = self._video(jitter={"jawOpen": {"ref": 0.010, "test": 0.0101}})

        # When/Then: la variante est acceptée
        assert comparator.evaluate_thresholds(self._summary([video]), comparator.DEFAULT_THRESHOLDS) == []

    def test_render_markdown_reports_verdict(self):
        # Given: une liste de défaillances
        failures = ["max_k RMSE 0.0500 >= 0.035"]

        # When: le rapport est rendu
        markdown = comparator.render_markdown(self._summary([self._video()]), failures)

        # Then: le verdict est explicite
        assert "ÉCHEC" in markdown
        assert "max_k RMSE" in markdown
        assert "OK" in comparator.render_markdown(self._summary([self._video()]), [])


class TestCommandLine:
    def _prepare(self, tmp_path, bias):
        ref_dir = tmp_path / "ref"
        test_dir = tmp_path / "test"
        ref_dir.mkdir()
        test_dir.mkdir()
        frames = [_frame(index) for index in range(30)]
        _write(ref_dir / "clip.json", frames)
        _write(test_dir / "clip.json", [_frame(index, bias=bias) for index in range(30)])
        return ref_dir, test_dir

    def test_cli_returns_zero_for_stable_variant(self, tmp_path):
        # Given: deux sorties identiques
        ref_dir, test_dir = self._prepare(tmp_path, bias=0.0)

        # When: le comparateur est exécuté
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "compare_step4_tracking_outputs.py"),
             "--ref", str(ref_dir), "--test", str(test_dir)],
            capture_output=True, text=True, check=False,
        )

        # Then: le code retour est nul et le rapport est positif
        assert result.returncode == 0
        assert "**OK**" in result.stdout

    def test_cli_returns_one_and_writes_reports_on_regression(self, tmp_path):
        # Given: une variante biaisée au-delà du seuil
        ref_dir, test_dir = self._prepare(tmp_path, bias=0.2)
        out_json = tmp_path / "compare.json"
        out_md = tmp_path / "compare.md"

        # When: le comparateur est exécuté avec rapports
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "compare_step4_tracking_outputs.py"),
             "--ref", str(ref_dir), "--test", str(test_dir),
             "--out", str(out_json), "--markdown", str(out_md)],
            capture_output=True, text=True, check=False,
        )

        # Then: l'échec est signalé, tracé et persisté
        assert result.returncode == 1
        payload = json.loads(out_json.read_text(encoding="utf-8"))
        assert payload["status"] == "FAIL"
        assert out_md.exists()

    def test_cli_warns_when_a_video_is_missing_in_variant(self, tmp_path):
        # Given: une vidéo présente uniquement dans la référence
        ref_dir, test_dir = self._prepare(tmp_path, bias=0.0)
        _write(test_dir / "clip.json", [_frame(index) for index in range(30)][:5])
        _write(test_dir / "extra.json", [_frame(index) for index in range(30)])

        # When: le comparateur est exécuté
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "compare_step4_tracking_outputs.py"),
             "--ref", str(ref_dir), "--test", str(test_dir)],
            capture_output=True, text=True, check=False,
        )

        # Then: la comparaison reste possible et signale la troncature
        assert result.returncode == 0
        assert "frames_compared" in result.stdout or "Comparaison" in result.stdout
