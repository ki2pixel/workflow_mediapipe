#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests unitaires du harnais de benchmark STEP4 TPU (``scripts/bench_step4_tpu.py``).

Le harnais n'utilise que la bibliothèque standard : ces tests tournent dans le
venv principal, sans Coral ni venv d'étape.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_harness():
    spec = importlib.util.spec_from_file_location(
        "bench_step4_tpu", PROJECT_ROOT / "scripts" / "bench_step4_tpu.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


harness = _load_harness()


def _make_report(video, frames, worker_mean=8.0, acq_mean=3.0, parent_mean=1.5):
    return {
        "video": video,
        "label": f"{video}:parent",
        "frames": frames,
        "wall_ms": frames * 12.0,
        "warmup_frames": 50,
        "warmup_applied": True,
        "stages": {
            "worker_worker_total": {"count": frames, "count_analyzed": frames - 50, "total_ms": worker_mean * (frames - 50), "mean_ms": worker_mean, "p95_ms": worker_mean * 1.2, "p99_ms": worker_mean * 1.4, "max_ms": worker_mean * 3},
            "worker_blazeface_tpu": {"count": frames, "count_analyzed": frames - 50, "total_ms": 1.5 * (frames - 50), "mean_ms": 1.5, "p95_ms": 1.7, "p99_ms": 1.9, "max_ms": 4.0},
            "acq_acq_read_pipe": {"count": frames, "count_analyzed": frames - 50, "total_ms": acq_mean * (frames - 50), "mean_ms": acq_mean, "p95_ms": acq_mean * 1.1, "p99_ms": acq_mean * 1.2, "max_ms": acq_mean * 2},
            "parent_total": {"count": frames, "count_analyzed": frames - 50, "total_ms": parent_mean * (frames - 50), "mean_ms": parent_mean, "p95_ms": parent_mean * 1.1, "p99_ms": parent_mean * 1.2, "max_ms": parent_mean * 2},
            "tracking_serial": {"count": frames, "count_analyzed": frames - 50, "total_ms": 1.0 * (frames - 50), "mean_ms": 1.0, "p95_ms": 1.1, "p99_ms": 1.2, "max_ms": 2.0},
            "json_write": {"count": frames, "count_analyzed": frames - 50, "total_ms": 0.5 * (frames - 50), "mean_ms": 0.5, "p95_ms": 0.6, "p99_ms": 0.7, "max_ms": 1.0},
        },
        "worker": {"frames": frames, "wall_ms": frames * worker_mean, "fps": 125.0, "gauges": {"queue_fill": {"mean": 5.2, "max": 8, "p50": 5, "p95": 8, "p99": 8}}},
        "acq": {"frames": frames, "wall_ms": frames * acq_mean, "fps": 300.0, "gauges": {}},
        "gauges": {"active_objects": {"mean": 1.4, "max": 1, "p50": 1, "p95": 1, "p99": 1}},
    }


class TestEnvFile:
    def test_parse_ignores_comments_and_quotes(self, tmp_path):
        # Given: un fichier .env avec commentaires, export et guillemets
        env_file = tmp_path / ".env"
        env_file.write_text(
            "# commentaire\nENABLE_CORAL_TPU_ACCELERATION=true\n"
            'export STEP4_ENABLE_OBJECT_DETECTION="1"\n\nSTEP4_COCOMPILED_MODELS=0\n',
            encoding="utf-8",
        )

        # When: le fichier est analysé
        values = harness.parse_env_file(env_file)

        # Then: seules les paires clé/valeur utiles sont conservées
        assert values == {
            "ENABLE_CORAL_TPU_ACCELERATION": "true",
            "STEP4_ENABLE_OBJECT_DETECTION": "1",
            "STEP4_COCOMPILED_MODELS": "0",
        }

    def test_missing_file_returns_empty_mapping(self, tmp_path):
        # Given/When: un chemin inexistant
        # Then: l'analyse est silencieusement vide
        assert harness.parse_env_file(tmp_path / "absent.env") == {}

    def test_environment_precedence(self, tmp_path, monkeypatch):
        # Given: une variable ambiante, un .env et une surcharge explicite
        monkeypatch.setenv("STEP4_COCOMPILED_MODELS", "ambient")
        env_file = tmp_path / ".env"
        env_file.write_text(
            "STEP4_COCOMPILED_MODELS=env_file\nSTEP4_ENABLE_OBJECT_DETECTION=env_file\n",
            encoding="utf-8",
        )

        # When: l'environnement du run est construit
        environment = harness.build_environment(env_file, {"STEP4_ENABLE_OBJECT_DETECTION": "override"})

        # Then: le processus courant gagne sur le .env, et la surcharge gagne sur tout
        assert environment["STEP4_COCOMPILED_MODELS"] == "ambient"
        assert environment["STEP4_ENABLE_OBJECT_DETECTION"] == "override"


class TestVideoSelection:
    def test_collect_filters_extension_pattern_and_limit(self, tmp_path):
        # Given: une arborescence mixte (vidéos, JSON, sous-dossiers)
        (tmp_path / "dos").mkdir()
        for name in ("a.mp4", "b.mp4", "c.mkv", "notes.txt"):
            (tmp_path / name).write_text("x", encoding="utf-8")
        (tmp_path / "dos" / "d.mp4").write_text("x", encoding="utf-8")

        # When: la collecte applique motif, extension et limite
        videos = harness.collect_videos(tmp_path, "**/*.*", limit=2)

        # Then: seules les vidéos triées sont retenues, dans la limite demandée
        assert [path.name for path in videos] == ["a.mp4", "b.mp4"]
        assert all(path.is_absolute() for path in videos)

    def test_collect_applies_name_filters(self, tmp_path):
        # Given: trois vidéos aux noms distincts
        for name in ("Cynthia pleure.mp4", "Greg craque.mp4"):
            (tmp_path / name).write_text("x", encoding="utf-8")

        # When: un filtre partiel insensible à la casse est appliqué
        videos = harness.collect_videos(tmp_path, "**/*.mp4", filters=["cynthia"])

        # Then: seule la vidéo correspondante est retenue
        assert [path.name for path in videos] == ["Cynthia pleure.mp4"]

    def test_prerequisites_warn_on_missing_artifacts(self, tmp_path):
        # Given: une vidéo sans CSV de scènes ni diarisation
        video = tmp_path / "seule.mp4"
        video.write_text("x", encoding="utf-8")

        # When: les prérequis sont vérifiés
        warnings = harness.check_prerequisites([video])

        # Then: les deux manques sont signalés
        assert len(warnings) == 2
        assert any("STEP2" in warning for warning in warnings)
        assert any("STEP3" in warning for warning in warnings)

    def test_prerequisites_silent_when_complete(self, tmp_path):
        # Given: une vidéo accompagnée de ses artefacts STEP2 et STEP3
        video = tmp_path / "complete.mp4"
        video.write_text("x", encoding="utf-8")
        (tmp_path / "complete.csv").write_text("No\n", encoding="utf-8")
        (tmp_path / "complete_audio.json").write_text("{}", encoding="utf-8")

        # When/Then: aucune alerte n'est émise
        assert harness.check_prerequisites([video]) == []


class TestAggregation:
    def test_role_budgets_and_bottleneck(self):
        # Given: deux vidéos dont le worker domine le budget
        reports = {"v1": _make_report("v1", 500), "v2": _make_report("v2", 400)}
        durations = {"v1": 10.0, "v2": 8.0}

        # When: les rapports sont agrégés
        aggregation = harness.aggregate_reports(reports, durations)

        # Then: les budgets par rôle et le goulot sont identifiés
        assert aggregation["videos"] == 2
        assert aggregation["frames"] == 900
        assert aggregation["fps"] == pytest.approx(50.0, abs=0.01)
        assert aggregation["role_budgets_ms"]["worker"] == pytest.approx(8.0)
        assert aggregation["role_budgets_ms"]["acquisition"] == pytest.approx(3.0)
        assert aggregation["role_budgets_ms"]["parent"] == pytest.approx(1.5)
        assert aggregation["bottleneck"]["role"] == "worker"
        assert aggregation["bottleneck"]["stage"] == "worker_blazeface_tpu"

    def test_stage_totals_sum_counts_and_take_max_percentiles(self):
        # Given: deux vidéos de tailles différentes
        reports = {"v1": _make_report("v1", 500), "v2": _make_report("v2", 100)}

        # When: l'agrégation est calculée
        aggregation = harness.aggregate_reports(reports, {"v1": 5.0, "v2": 1.0})

        # Then: les compteurs s'additionnent et les p95 sont conservés au maximum
        stage = aggregation["stages"]["worker_blazeface_tpu"]
        assert stage["count"] == 450 + 50
        assert stage["mean_ms"] == pytest.approx(1.5, abs=1e-3)
        assert stage["p95_ms_max"] == pytest.approx(1.7, abs=1e-3)

    def test_duration_falls_back_to_report_wall(self):
        # Given: un rapport sans durée issue du log
        reports = {"v1": _make_report("v1", 500)}

        # When: l'agrégation est calculée sans durée externe
        aggregation = harness.aggregate_reports(reports, {})

        # Then: la durée du rapport sert de repli
        assert aggregation["per_video"][0]["wall_s"] == pytest.approx(6.0, abs=0.01)

    def test_ignores_reports_without_frames(self):
        # Given: un rapport vide (échec du run)
        reports = {"vide": {"video": "vide", "frames": 0, "stages": {}}}

        # When/Then: il est ignoré de l'agrégation
        aggregation = harness.aggregate_reports(reports, {})
        assert aggregation["videos"] == 0
        assert aggregation["stages"] == {}

    def test_render_markdown_contains_bottleneck_and_stage_table(self):
        # Given: une agrégation issue de deux vidéos
        aggregation = harness.aggregate_reports({"v1": _make_report("v1", 500)}, {"v1": 6.0})

        # When: le rapport Markdown est rendu
        markdown = harness.render_markdown(
            "fast1",
            {"wall_seconds": 6.0, "return_code": 0, "overrides": {"STEP4_TPU_FAST": "1"}, "missing_outputs": []},
            aggregation,
            {"pipeline_mode": "multiprocessing", "cocompiled_models": True},
        )

        # Then: le goulot, les rôles et les étages sont présents
        assert "variante `fast1`" in markdown
        assert "Goulot identifié" in markdown
        assert "worker_blazeface_tpu" in markdown
        assert "| acquisition |" in markdown

    def test_write_summaries_creates_three_artifacts(self, tmp_path):
        # Given: une agrégation minimale
        aggregation = harness.aggregate_reports({"v1": _make_report("v1", 500)}, {"v1": 6.0})

        # When: les rapports sont écrits
        harness.write_summaries(
            tmp_path,
            "baseline",
            {"wall_seconds": 6.0, "return_code": 0, "overrides": {}, "missing_outputs": []},
            aggregation,
            {},
        )

        # Then: les trois fichiers attendus existent et le CSV contient l'entête
        assert (tmp_path / "report.md").exists()
        summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
        assert summary["variant"] == "baseline"
        csv_lines = (tmp_path / "summary.csv").read_text(encoding="utf-8").splitlines()
        assert csv_lines[0].startswith("video,frames,wall_s,fps")
        assert len(csv_lines) == 2


class TestPublish:
    def test_publish_copies_outputs_next_to_videos(self, tmp_path):
        # Given: une variante contenant le JSON d'une vidéo
        run_dir = tmp_path / "run"
        (run_dir / "outputs").mkdir(parents=True)
        (run_dir / "outputs" / "clip.json").write_text('{"frames": []}', encoding="utf-8")
        video = tmp_path / "projets" / "clip.mp4"
        video.parent.mkdir()
        video.write_text("x", encoding="utf-8")

        # When: la variante est publiée
        published = harness.publish_outputs(run_dir, [video])

        # Then: le JSON est recopié à côté de la vidéo
        assert published == 1
        assert video.with_suffix(".json").exists()


class TestInvocation:
    def test_script_exposes_main_entrypoint(self):
        # Given/When/Then: le harnais est exécutable en ligne de commande
        assert callable(harness.main)
        assert harness.DEFAULT_TRACKING_SCRIPT.name == "run_tracking_tpu.py"

    def test_missing_videos_returns_error_code(self, tmp_path, capsys):
        # Given: une racine sans vidéo et une variante quelconque
        argv = ["bench_step4_tpu.py", "--variant", "test", "--root", str(tmp_path), "--bench-root", str(tmp_path / "bench")]
        original = sys.argv

        # When: le harnais est lancé
        try:
            sys.argv = argv
            return_code = harness.main()
        finally:
            sys.argv = original

        # Then: il s'arrête proprement avec un code d'erreur
        assert return_code == 2
        assert "Aucune vidéo" in capsys.readouterr().err
