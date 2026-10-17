#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare les fournisseurs ONNX Runtime du modèle ECAPA-TDNN.

Le script s'exécute dans un venv contenant ``onnxruntime`` ou
``onnxruntime-openvino`` et ne dépend que de numpy. Il mesure le temps
d'inférence moyen par lot pour CPUExecutionProvider et, si disponible,
OpenVINOExecutionProvider (CPU_FP32).

Exemple :
    scratch/ort_ov_venv/bin/python scripts/bench_ecapa_providers.py \
        --batch-sizes 1,8,16,32 --runs 3
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = PROJECT_ROOT / "assets" / "ecapa_tdnn_speaker_float.onnx"
DEFAULT_CACHE = PROJECT_ROOT / "scratch" / "ort_openvino_cache"


def build_session(provider, model_path, threads, cache_dir):
    import onnxruntime as ort

    options = ort.SessionOptions()
    options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    options.intra_op_num_threads = threads
    options.inter_op_num_threads = 1
    options.add_session_config_entry("session.intra_op.allow_spinning", "0")

    if provider == "cpu":
        providers = ["CPUExecutionProvider"]
    elif provider == "openvino":
        if "OpenVINOExecutionProvider" not in ort.get_available_providers():
            raise RuntimeError("OpenVINOExecutionProvider indisponible")
        cache_dir.mkdir(parents=True, exist_ok=True)
        providers = [
            ("OpenVINOExecutionProvider", {
                "device_type": "CPU",
                "precision": "FP32",
                "num_of_threads": str(threads),
                "cache_dir": str(cache_dir),
            }),
            "CPUExecutionProvider",
        ]
    else:
        raise ValueError(f"Fournisseur inconnu: {provider}")

    return ort.InferenceSession(str(model_path), sess_options=options, providers=providers)


def measure(session, batch_size, runs):
    input_name = session.get_inputs()[0].name
    data = np.zeros((batch_size, 80, 300), dtype=np.float32)
    session.run(None, {input_name: data})
    durations = []
    for _ in range(runs):
        started = time.perf_counter()
        session.run(None, {input_name: data})
        durations.append((time.perf_counter() - started) * 1000.0)
    return {
        "batch_size": batch_size,
        "runs": runs,
        "mean_ms": round(float(np.mean(durations)), 2),
        "min_ms": round(float(np.min(durations)), 2),
        "max_ms": round(float(np.max(durations)), 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Banc CPU vs OpenVINO pour ECAPA-TDNN")
    parser.add_argument("--model", default=str(DEFAULT_MODEL))
    parser.add_argument("--providers", default="cpu,openvino")
    parser.add_argument("--batch-sizes", default="1,8,16,32")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--threads", type=int, default=11)
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE))
    parser.add_argument("--output", default=None, help="Rapport JSON optionnel")
    args = parser.parse_args()

    model_path = Path(args.model).resolve()
    if not model_path.exists():
        print(f"Modèle introuvable: {model_path}", file=sys.stderr)
        return 2
    batch_sizes = [int(item) for item in args.batch_sizes.split(",") if item.strip()]
    providers = [item.strip() for item in args.providers.split(",") if item.strip()]

    report = {"model": str(model_path), "threads": args.threads, "results": {}}
    for provider in providers:
        try:
            session = build_session(provider, model_path, args.threads, Path(args.cache_dir))
        except Exception as exc:
            print(f"{provider}: initialisation impossible ({exc})")
            report["results"][provider] = {"error": str(exc)}
            continue

        print(f"\n{provider}:")
        provider_results = []
        for batch_size in batch_sizes:
            try:
                result = measure(session, batch_size, args.runs)
                print(
                    f"  batch {batch_size:>2}: {result['mean_ms']:>9.1f} ms "
                    f"(min {result['min_ms']:.1f}, max {result['max_ms']:.1f})"
                )
                provider_results.append(result)
            except Exception as exc:
                print(f"  batch {batch_size:>2}: échec ({exc})")
                provider_results.append({"batch_size": batch_size, "error": str(exc)})
        report["results"][provider] = provider_results

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nRapport écrit: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
