"""
Profiler par étage pour le pipeline STEP4 TPU (BlazeFace -> FaceMesh -> Blendshapes).

Collecte des durées en nanosecondes dans des anneaux NumPy préalloués : aucun
log, aucune allocation, aucun formatage de chaîne dans la boucle chaude. Les
statistiques (moyenne, P50, P95, P99, max, part du budget) sont calculées à la
fin de chaque vidéo.

Activation : ``--profile-dir`` (CLI de run_tracking_tpu.py) ou variable
d'environnement ``STEP4_TPU_PROFILING_DIR``. Sans activation, le module n'est pas
instancié et le pipeline garde son comportement d'origine.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

# Étages chronométrés : l'ordre définit l'index de colonne dans l'anneau.
STAGE_NAMES = (
    "acq_read_pipe",
    "acq_shm_write",
    "acq_push",
    "queue_wait",
    "blazeface_tpu",
    "affine_crop",
    "facemesh_tpu",
    "blendshapes_cpu",
    "one_euro",
    "object_detector_tpu",
    "tracking_serial",
    "json_write",
    "worker_total",
    "parent_total",
    "e2e_frame",
)
N_STAGES = len(STAGE_NAMES)
STAGE_INDEX = {name: index for index, name in enumerate(STAGE_NAMES)}

# Grandeurs ponctuelles (non cumulables) relevées par frame.
GAUGE_NAMES = (
    "queue_fill",
    "active_objects",
)
N_GAUGES = len(GAUGE_NAMES)
GAUGE_INDEX = {name: index for index, name in enumerate(GAUGE_NAMES)}

DEFAULT_CAPACITY = 8192
MIN_CAPACITY = 1024
MAX_CAPACITY = 65536


def resolve_profile_dir(cli_value: Optional[str] = None) -> Optional[Path]:
    """Résout le répertoire de profilage depuis le CLI puis l'environnement."""
    raw = (cli_value or os.environ.get("STEP4_TPU_PROFILING_DIR") or "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def profiling_capacity(expected_frames: Optional[int]) -> int:
    """Dimensionne l'anneau pour couvrir la vidéo sans débordement."""
    if not expected_frames or expected_frames <= 0:
        return DEFAULT_CAPACITY
    return int(max(MIN_CAPACITY, min(expected_frames, MAX_CAPACITY)))


class StageProfiler:
    """Accumulateur de durées par étage, sûr dans une boucle temps réel."""

    __slots__ = (
        "label",
        "capacity",
        "_durations",
        "_cursors",
        "_counts",
        "_totals",
        "_gauges",
        "_gauge_cursors",
        "_gauge_counts",
        "_start_ns",
        "_stop_ns",
        "frames",
    )

    def __init__(self, label: str, capacity: int = DEFAULT_CAPACITY):
        self.label = label
        self.capacity = int(max(MIN_CAPACITY, min(capacity or DEFAULT_CAPACITY, MAX_CAPACITY)))
        self.frames = 0
        self._durations = np.zeros((N_STAGES, self.capacity), dtype=np.int64)
        self._cursors = np.zeros(N_STAGES, dtype=np.int64)
        self._counts = np.zeros(N_STAGES, dtype=np.int64)
        self._totals = np.zeros(N_STAGES, dtype=np.int64)
        self._gauges = np.zeros((N_GAUGES, self.capacity), dtype=np.int64)
        self._gauge_cursors = np.zeros(N_GAUGES, dtype=np.int64)
        self._gauge_counts = np.zeros(N_GAUGES, dtype=np.int64)
        self._start_ns = 0
        self._stop_ns = 0

    # --- boucle chaude -------------------------------------------------

    def start(self) -> None:
        self._start_ns = time.perf_counter_ns()

    def stop(self) -> None:
        self._stop_ns = time.perf_counter_ns()

    def count_frame(self) -> None:
        self.frames += 1

    def add(self, stage: str, duration_ns: int) -> None:
        index = STAGE_INDEX[stage]
        cursor = int(self._cursors[index])
        self._durations[index, cursor] = duration_ns
        self._cursors[index] = (cursor + 1) % self.capacity
        self._counts[index] += 1
        self._totals[index] += duration_ns

    def gauge(self, name: str, value: int) -> None:
        index = GAUGE_INDEX[name]
        cursor = int(self._gauge_cursors[index])
        self._gauges[index, cursor] = value
        self._gauge_cursors[index] = (cursor + 1) % self.capacity
        self._gauge_counts[index] += 1

    # --- agrégation ----------------------------------------------------

    @staticmethod
    def _percentiles(samples: np.ndarray) -> tuple:
        p50, p95, p99 = np.percentile(samples, [50.0, 95.0, 99.0])
        return float(p50), float(p95), float(p99)

    def finalize(self, warmup_frames: Optional[int] = None) -> Dict[str, Any]:
        """Agrège les mesures ; ``warmup_frames`` retire les N premières frames de chaque étage.

        Sans valeur explicite, la variable d'environnement ``STEP4_TPU_PROFILE_WARMUP``
        est utilisée (les 50 premières frames absorbent la compilation Numba et le
        chargement des poids en SRAM).
        """
        if warmup_frames is None:
            try:
                warmup_frames = int(os.environ.get("STEP4_TPU_PROFILE_WARMUP", "0") or 0)
            except ValueError:
                warmup_frames = 0
        warmup_frames = max(0, int(warmup_frames or 0))

        stages: Dict[str, Dict[str, float]] = {}
        warmup_applied = False
        for index, name in enumerate(STAGE_NAMES):
            count = int(self._counts[index])
            if count == 0:
                continue
            retained = min(count, self.capacity)
            samples = self._durations[index, :retained]
            use_samples = warmup_frames > 0 and count <= self.capacity and retained > warmup_frames
            if use_samples:
                samples = samples[warmup_frames:]
                retained = samples.size
                total_ns = int(samples.sum())
                warmup_applied = True
            else:
                total_ns = int(self._totals[index])
            p50, p95, p99 = self._percentiles(samples)
            stages[name] = {
                "count": count,
                "count_analyzed": int(retained),
                "total_ms": round(total_ns / 1e6, 3),
                "mean_ms": round(total_ns / retained / 1e6, 4),
                "max_ms": round(float(samples.max()) / 1e6, 4),
                "p50_ms": round(p50 / 1e6, 4),
                "p95_ms": round(p95 / 1e6, 4),
                "p99_ms": round(p99 / 1e6, 4),
            }

        gauges: Dict[str, Dict[str, float]] = {}
        for index, name in enumerate(GAUGE_NAMES):
            count = int(self._gauge_counts[index])
            if count == 0:
                continue
            samples = self._gauges[index, : min(count, self.capacity)]
            if warmup_frames > 0 and count <= self.capacity and samples.size > warmup_frames:
                samples = samples[warmup_frames:]
            p50, p95, p99 = self._percentiles(samples)
            gauges[name] = {
                "count": count,
                "mean": round(float(samples.mean()), 4),
                "max": int(samples.max()),
                "p50": round(p50, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
            }

        wall_ns = self._stop_ns - self._start_ns if self._stop_ns > self._start_ns else 0
        result: Dict[str, Any] = {
            "label": self.label,
            "frames": int(self.frames),
            "capacity": self.capacity,
            "warmup_frames": warmup_frames,
            "warmup_applied": warmup_applied,
            "wall_ms": round(wall_ns / 1e6, 2),
            "fps": round(self.frames / (wall_ns / 1e9), 2) if wall_ns > 0 and self.frames else None,
            "budget_ms_per_frame": (
                round(wall_ns / 1e6 / self.frames, 4) if self.frames and wall_ns > 0 else None
            ),
            "stages": stages,
            "gauges": gauges,
        }

        worker_total = stages.get("worker_total", {}).get("total_ms")
        if worker_total:
            result["share_of_worker_pct"] = {
                name: round(data["total_ms"] / worker_total * 100.0, 2)
                for name, data in stages.items()
                if name != "worker_total"
            }
        return result

    def write(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as file_obj:
            json.dump(self.finalize(), file_obj, indent=2, ensure_ascii=False)
        return path


def merge_reports(primary: Dict[str, Any], sources: Dict[str, Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    """Fusionne des rapports frères (thread d'acquisition, worker) dans le rapport parent.

    Chaque source voit ses étages préfixés (``acq_``, ``worker_``) pour rester
    lisible dans le rapport agrégé, et ses métadonnées (frames, wall, fps, jauges)
    conservées sous sa clé d'origine.
    """
    stages = dict(primary.get("stages", {}))
    for prefix, source in sources.items():
        if not source:
            primary[prefix] = None
            continue
        primary[prefix] = {
            "frames": source.get("frames"),
            "wall_ms": source.get("wall_ms"),
            "fps": source.get("fps"),
            "gauges": source.get("gauges", {}),
        }
        for name, data in source.get("stages", {}).items():
            stages[f"{prefix}_{name}"] = data
    primary["stages"] = stages
    return primary
