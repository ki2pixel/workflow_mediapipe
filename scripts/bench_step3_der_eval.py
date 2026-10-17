#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Évaluation DER/JER d'une sortie STEP3 au format ``<video>_audio.json``.

Ce script s'exécute dans ``audio_env`` (pyannote.metrics). Le JSON STEP3 ne
contient pas de liste de segments : l'hypothèse est reconstruite depuis
``frames_analysis`` à la résolution de la timeline (25 fps par défaut), ce qui
correspond à la granularité de sortie du pipeline.

Exemple :
    /mnt/venv_ext4/audio_env/bin/python scripts/bench_step3_der_eval.py \\
        --reference-dir scratch/bench_step3_der/voxconverse/rttm \\
        --hypothesis-dir scratch/bench_step3_der/run/outputs \\
        --output scratch/bench_step3_der/run/der_report.json
"""

import argparse
import json
import sys
from pathlib import Path

from pyannote.core import Annotation, Segment
from pyannote.metrics.diarization import DiarizationErrorRate, JaccardErrorRate

DEFAULT_FPS = 25.0


def load_reference_rttm(rttm_path: Path) -> Annotation:
    """Charge une référence NIST RTTM dans une Annotation pyannote."""
    annotation = Annotation(uri=rttm_path.stem)
    with open(rttm_path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            parts = line.split()
            if parts[0].upper() != "SPEAKER" or len(parts) < 8:
                continue
            start = float(parts[3])
            duration = float(parts[4])
            speaker = parts[7]
            if duration > 0.0:
                annotation[Segment(start, start + duration), f"{speaker}_{line_number}"] = speaker
    return annotation


def load_hypothesis_json(json_path: Path) -> Annotation:
    """Reconstruit l'hypothèse depuis ``frames_analysis`` (1 segment par frame)."""
    with open(json_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    frames = payload.get("frames_analysis")
    if not isinstance(frames, list):
        raise ValueError(f"{json_path.name}: clé frames_analysis absente ou invalide")

    fps = float(payload.get("fps") or DEFAULT_FPS)
    frame_duration = 1.0 / fps
    annotation = Annotation(uri=json_path.stem)
    for item in frames:
        info = item.get("audio_info") or {}
        if not info.get("is_speech_present"):
            continue
        start = float(info.get("timecode_sec", 0.0))
        frame_index = item.get("frame", 0)
        for speaker in info.get("active_speaker_labels") or []:
            annotation[Segment(start, start + frame_duration), f"{frame_index}_{speaker}"] = str(speaker)
    return annotation


def evaluate_pair(reference: Annotation, hypothesis: Annotation) -> dict:
    """Calcule DER/JER et la décomposition à collar=0.0 et 0.25."""
    results = {}
    for collar in (0.0, 0.25):
        der_metric = DiarizationErrorRate(collar=collar, skip_overlap=False)
        jer_metric = JaccardErrorRate(collar=collar, skip_overlap=False)

        components = der_metric(reference, hypothesis, detailed=True)
        jer_score = float(jer_metric(reference, hypothesis))

        total_ref = max(float(components["total"]), 1e-9)
        results[f"collar_{collar:.2f}s"] = {
            "DER_pct": round((components["missed detection"] + components["false alarm"] + components["confusion"]) / total_ref * 100.0, 4),
            "JER_pct": round(jer_score * 100.0, 4),
            "Missed_Speech_pct": round(components["missed detection"] / total_ref * 100.0, 4),
            "False_Alarm_pct": round(components["false alarm"] / total_ref * 100.0, 4),
            "Speaker_Confusion_pct": round(components["confusion"] / total_ref * 100.0, 4),
            "Total_Ref_Speech_sec": round(total_ref, 2),
        }
    return results


def summarize(per_file: dict) -> dict:
    """Moyenne les métriques par durée de référence de parole."""
    summary = {}
    for collar_key in ("collar_0.00s", "collar_0.25s"):
        entries = [item[collar_key] for item in per_file.values() if collar_key in item]
        total_weight = sum(entry["Total_Ref_Speech_sec"] for entry in entries)
        if not entries or total_weight <= 0.0:
            continue
        summary[collar_key] = {
            "DER_pct": round(sum(entry["DER_pct"] * entry["Total_Ref_Speech_sec"] for entry in entries) / total_weight, 4),
            "JER_pct": round(sum(entry["JER_pct"] * entry["Total_Ref_Speech_sec"] for entry in entries) / total_weight, 4),
            "Missed_Speech_pct": round(sum(entry["Missed_Speech_pct"] * entry["Total_Ref_Speech_sec"] for entry in entries) / total_weight, 4),
            "False_Alarm_pct": round(sum(entry["False_Alarm_pct"] * entry["Total_Ref_Speech_sec"] for entry in entries) / total_weight, 4),
            "Speaker_Confusion_pct": round(sum(entry["Speaker_Confusion_pct"] * entry["Total_Ref_Speech_sec"] for entry in entries) / total_weight, 4),
            "Total_Ref_Speech_sec": round(total_weight, 2),
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Évaluation DER/JER d'une sortie STEP3")
    parser.add_argument("--reference-dir", required=True, help="Répertoire des fichiers RTTM")
    parser.add_argument("--hypothesis-dir", required=True, help="Répertoire des fichiers <uri>_audio.json")
    parser.add_argument("--output", required=True, help="Rapport JSON de sortie")
    parser.add_argument("--baseline", default=None, help="Rapport JSON de référence (contrôle ΔDER)")
    parser.add_argument("--max-delta", type=float, default=0.05, help="ΔDER maximal autorisé (points de %%)")
    parser.add_argument("--require-parity", action="store_true",
                        help="Exiger |ΔDER| ≤ limite (interdit aussi les améliorations)")
    args = parser.parse_args()

    reference_dir = Path(args.reference_dir).resolve()
    hypothesis_dir = Path(args.hypothesis_dir).resolve()
    rttm_files = sorted(reference_dir.glob("*.rttm"))
    if not rttm_files:
        print(f"Aucune annotation RTTM dans {reference_dir}", file=sys.stderr)
        return 1

    per_file = {}
    missing = []
    for rttm_path in rttm_files:
        hypothesis_path = hypothesis_dir / f"{rttm_path.stem}_audio.json"
        if not hypothesis_path.exists():
            missing.append(rttm_path.stem)
            continue
        reference = load_reference_rttm(rttm_path)
        hypothesis = load_hypothesis_json(hypothesis_path)
        per_file[rttm_path.stem] = evaluate_pair(reference, hypothesis)
        strict = per_file[rttm_path.stem]["collar_0.00s"]
        print(
            f"{rttm_path.stem}: DER={strict['DER_pct']}% JER={strict['JER_pct']}% "
            f"(miss={strict['Missed_Speech_pct']}% fa={strict['False_Alarm_pct']}% conf={strict['Speaker_Confusion_pct']}%)",
            flush=True,
        )

    if not per_file:
        print("Aucun couple référence/hypothèse évaluable.", file=sys.stderr)
        return 1

    report = {"files": per_file, "summary": summarize(per_file), "missing": missing}

    if args.baseline:
        baseline_path = Path(args.baseline).resolve()
        baseline_report = json.loads(baseline_path.read_text(encoding="utf-8"))
        baseline_der = baseline_report["summary"]["collar_0.00s"]["DER_pct"]
        baseline_jer = baseline_report["summary"]["collar_0.00s"]["JER_pct"]
        measured = report["summary"]["collar_0.00s"]
        delta_der = measured["DER_pct"] - baseline_der
        report["regression_check"] = {
            "baseline_der_pct": baseline_der,
            "baseline_jer_pct": baseline_jer,
            "measured_der_pct": measured["DER_pct"],
            "measured_jer_pct": measured["JER_pct"],
            "delta_der_pct": round(delta_der, 4),
            "delta_jer_pct": round(measured["JER_pct"] - baseline_jer, 4),
            "max_delta_pct": args.max_delta,
            "passed": delta_der <= args.max_delta,
            "parity_passed": abs(delta_der) <= args.max_delta,
            "require_parity": args.require_parity,
        }

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Rapport écrit : {output_path}")

    if missing:
        print(f"{len(missing)} vidéo(s) sans JSON d'hypothèse : {', '.join(missing[:5])}", file=sys.stderr)

    check = report.get("regression_check")
    if check:
        failed = (not check["parity_passed"]) if args.require_parity else (not check["passed"])
        if failed:
            label = "Écart de parité" if args.require_parity else "Régression DER"
            print(
                f"{label} : {check['delta_der_pct']:+.4f} points "
                f"(limite {check['max_delta_pct']} points)",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
