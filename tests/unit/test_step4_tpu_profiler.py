#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests unitaires du profiler par étage de la STEP4 TPU.

Ces tests nécessitent numpy (venv d'étape) : ils s'exécutent via
``scripts/run_step4_tests.sh`` et sont ignorés ailleurs.
"""

import importlib.util
import json
import time

import pytest

if importlib.util.find_spec("numpy") is None:
    pytestmark = pytest.mark.skip(reason="numpy non disponible dans cet environnement; tests ignorés.")
else:
    import numpy as np

    from utils.step4_tpu_profiler import (
        STAGE_NAMES,
        StageProfiler,
        merge_reports,
        profiling_capacity,
        resolve_profile_dir,
    )


class TestStageProfiler:
    def test_stage_names_are_unique_and_stable(self):
        # Given: l'énumération des étages du pipeline
        # When: les index sont construits
        # Then: chaque étage possède un index distinct et le count correspond
        assert len(STAGE_NAMES) == len(set(STAGE_NAMES))
        assert "worker_total" in STAGE_NAMES
        assert "e2e_frame" in STAGE_NAMES

    def test_add_accumulates_statistics(self):
        # Given: un profiler de capacité suffisante
        profiler = StageProfiler("test", capacity=1024)

        # When: 100 durées croissantes sont enregistrées
        for value in range(1, 101):
            profiler.add("blazeface_tpu", value * 1_000_000)

        # Then: les compteurs et statistiques reflètent les mesures
        result = profiler.finalize(warmup_frames=0)
        stage = result["stages"]["blazeface_tpu"]
        assert stage["count"] == 100
        assert stage["count_analyzed"] == 100
        assert stage["mean_ms"] == pytest.approx(50.5, abs=1e-3)
        assert stage["p50_ms"] == pytest.approx(50.0, abs=2.0)
        assert stage["p99_ms"] == pytest.approx(99.0, abs=2.0)
        assert stage["max_ms"] == pytest.approx(100.0, abs=1e-3)
        assert stage["total_ms"] == pytest.approx(5050.0, abs=1e-2)

    def test_ring_wraps_and_keeps_exact_count(self):
        # Given: un profiler dont la capacité est inférieure au nombre de mesures
        profiler = StageProfiler("wrap", capacity=1024)

        # When: 1500 mesures sont enregistrées
        for _ in range(1500):
            profiler.add("json_write", 500_000)

        # Then: le compteur reste exact mais l'agrégation n'analyse que l'anneau
        result = profiler.finalize(warmup_frames=0)
        stage = result["stages"]["json_write"]
        assert stage["count"] == 1500
        assert stage["count_analyzed"] == 1024
        assert stage["total_ms"] == pytest.approx(750.0, abs=1e-2)
        assert result["warmup_applied"] is False

    def test_warmup_frames_are_excluded(self):
        # Given: 50 frames de chauffe lentes suivies de 10 frames rapides
        profiler = StageProfiler("warmup", capacity=1024)
        for _ in range(50):
            profiler.add("blendshapes_cpu", 10_000_000)
        for _ in range(10):
            profiler.add("blendshapes_cpu", 1_000_000)

        # When: l'agrégation exclut les 50 premières frames
        result = profiler.finalize(warmup_frames=50)

        # Then: seules les mesures en régime établi sont analysées
        stage = result["stages"]["blendshapes_cpu"]
        assert result["warmup_applied"] is True
        assert stage["count_analyzed"] == 10
        assert stage["mean_ms"] == pytest.approx(1.0, abs=1e-3)
        assert stage["total_ms"] == pytest.approx(10.0, abs=1e-2)

    def test_gauges_report_distribution(self):
        # Given: un profiler recevant des jauges de remplissage de queue
        profiler = StageProfiler("gauges", capacity=1024)

        # When: des valeurs de 0 à 7 sont enregistrées
        for value in range(8):
            profiler.gauge("queue_fill", value)

        # Then: la distribution est restituée
        gauge = profiler.finalize(warmup_frames=0)["gauges"]["queue_fill"]
        assert gauge["count"] == 8
        assert gauge["max"] == 7
        assert gauge["mean"] == pytest.approx(3.5, abs=1e-3)

    def test_finalize_without_measurement_is_empty(self):
        # Given: un profiler neuf
        profiler = StageProfiler("empty", capacity=1024)

        # When: l'agrégation est demandée
        result = profiler.finalize(warmup_frames=0)

        # Then: aucun étage ni jauge n'est rapporté et le débit est indéfini
        assert result["stages"] == {}
        assert result["gauges"] == {}
        assert result["frames"] == 0
        assert result["fps"] is None

    def test_wall_clock_and_fps(self):
        # Given: un profiler démarré puis arrêté après 20 frames comptées et une attente mesurable
        profiler = StageProfiler("wall", capacity=1024)
        profiler.start()
        for _ in range(20):
            profiler.count_frame()
        time.sleep(0.02)
        profiler.stop()

        # When: le rapport est produit
        result = profiler.finalize(warmup_frames=0)

        # Then: la durée murale et le débit sont cohérents
        assert result["frames"] == 20
        assert result["wall_ms"] >= 20.0
        assert result["budget_ms_per_frame"] > 0
        assert result["fps"] > 0

    def test_write_creates_json_report(self, tmp_path):
        # Given: un profiler avec une mesure
        profiler = StageProfiler("write", capacity=1024)
        profiler.add("parent_total", 2_000_000)
        profiler.count_frame()

        # When: le rapport est écrit sur disque
        target = profiler.write(tmp_path / "nested" / "report.json")

        # Then: le JSON contient le label et l'étage mesuré
        payload = json.loads(target.read_text(encoding="utf-8"))
        assert payload["label"] == "write"
        assert payload["stages"]["parent_total"]["count"] == 1

    def test_profiling_capacity_bounds(self):
        # Given/When/Then: la capacité reste dans les bornes définies
        assert profiling_capacity(None) == 8192
        assert profiling_capacity(100) == 1024
        assert profiling_capacity(5_000) == 5_000
        assert profiling_capacity(10_000_000) == 65536


class TestMergeReports:
    def test_merge_prefixes_sources_and_keeps_primary(self):
        # Given: un rapport parent et un rapport worker
        primary = {"stages": {"tracking_serial": {"count": 10, "total_ms": 5.0}}, "gauges": {}}
        worker = {"frames": 10, "wall_ms": 100.0, "fps": 100.0, "stages": {"blazeface_tpu": {"count": 10, "total_ms": 25.0}}, "gauges": {"queue_fill": {"mean": 4.0}}}

        # When: les rapports sont fusionnés
        merged = merge_reports(primary, {"worker": worker, "acq": None})

        # Then: les étages du worker sont préfixés et la source absente est tracée
        assert "tracking_serial" in merged["stages"]
        assert "worker_blazeface_tpu" in merged["stages"]
        assert merged["worker"]["frames"] == 10
        assert merged["acq"] is None


class TestResolveProfileDir:
    def test_cli_value_wins_over_environment(self, monkeypatch, tmp_path):
        # Given: une valeur CLI et une variable d'environnement distinctes
        monkeypatch.setenv("STEP4_TPU_PROFILING_DIR", str(tmp_path / "env"))

        # When: le répertoire est résolu
        resolved = resolve_profile_dir(str(tmp_path / "cli"))

        # Then: la valeur CLI est prioritaire
        assert resolved == tmp_path / "cli"

    def test_environment_used_when_cli_absent(self, monkeypatch, tmp_path):
        # Given: seule la variable d'environnement est définie
        monkeypatch.setenv("STEP4_TPU_PROFILING_DIR", str(tmp_path / "env"))

        # When/Then: elle est utilisée
        assert resolve_profile_dir(None) == tmp_path / "env"

    def test_returns_none_when_nothing_set(self, monkeypatch):
        # Given: ni CLI ni environnement
        monkeypatch.delenv("STEP4_TPU_PROFILING_DIR", raising=False)

        # When/Then: le profilage reste désactivé
        assert resolve_profile_dir(None) is None
