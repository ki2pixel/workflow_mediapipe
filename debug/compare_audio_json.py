#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de comparaison des sorties JSON STEP4 GPU vs CPU
pour diagnostiquer les divergences sur is_speech_present
"""

import json
import sys
from pathlib import Path


def analyze_json(json_path: Path) -> dict:
    """Analyse un JSON audio et retourne des statistiques."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    frames_analysis = data.get('frames_analysis', [])
    
    total_frames_header = data.get('total_frames')
    fps = data.get('fps') or 25
    
    max_frame_in_data = 0
    for frame_data in frames_analysis:
        frame_num = frame_data.get('frame')
        if isinstance(frame_num, int) and frame_num > max_frame_in_data:
            max_frame_in_data = frame_num
    
    # Compatibilité: certains anciens JSON n'ont pas de header total_frames.
    # On l'infère de façon robuste via len(frames_analysis) et/ou le max(frame).
    total_frames_candidates = [
        int(total_frames_header) if isinstance(total_frames_header, int) and total_frames_header > 0 else 0,
        len(frames_analysis),
        max_frame_in_data,
    ]
    total_frames = max(total_frames_candidates)
    
    speech_frames = []
    first_speech_frame = None
    last_speech_frame = None
    
    for frame_data in frames_analysis:
        frame_num = frame_data.get('frame')
        audio_info = frame_data.get('audio_info', {})
        is_speech = audio_info.get('is_speech_present', False)
        
        if is_speech:
            speech_frames.append(frame_num)
            if first_speech_frame is None:
                first_speech_frame = frame_num
            last_speech_frame = frame_num
    
    num_speech_frames = len(speech_frames)
    speech_percentage = (num_speech_frames / total_frames * 100) if total_frames > 0 else 0
    
    return {
        'total_frames': total_frames,
        'fps': fps,
        'num_speech_frames': num_speech_frames,
        'speech_percentage': speech_percentage,
        'first_speech_frame': first_speech_frame,
        'last_speech_frame': last_speech_frame,
        'first_speech_timecode': (first_speech_frame - 1) / fps if first_speech_frame else None,
        'last_speech_timecode': (last_speech_frame - 1) / fps if last_speech_frame else None,
    }


def main():
    if len(sys.argv) != 3:
        print("Usage: python compare_audio_json.py <gpu_json> <cpu_json>")
        sys.exit(1)
    
    gpu_json = Path(sys.argv[1])
    cpu_json = Path(sys.argv[2])
    
    if not gpu_json.exists():
        print(f"Erreur: {gpu_json} n'existe pas")
        sys.exit(1)
    
    if not cpu_json.exists():
        print(f"Erreur: {cpu_json} n'existe pas")
        sys.exit(1)
    
    print("=== Analyse des JSON STEP4 (GPU vs CPU) ===\n")
    
    print(f"GPU JSON: {gpu_json.name}")
    gpu_stats = analyze_json(gpu_json)
    print(f"  Total frames: {gpu_stats['total_frames']}")
    print(f"  FPS: {gpu_stats['fps']}")
    print(f"  Frames avec parole: {gpu_stats['num_speech_frames']} ({gpu_stats['speech_percentage']:.2f}%)")
    print(f"  Première frame parole: {gpu_stats['first_speech_frame']} (timecode: {gpu_stats['first_speech_timecode']:.2f}s)")
    print(f"  Dernière frame parole: {gpu_stats['last_speech_frame']} (timecode: {gpu_stats['last_speech_timecode']:.2f}s)")
    print()
    
    print(f"CPU JSON: {cpu_json.name}")
    cpu_stats = analyze_json(cpu_json)
    print(f"  Total frames: {cpu_stats['total_frames']}")
    print(f"  FPS: {cpu_stats['fps']}")
    print(f"  Frames avec parole: {cpu_stats['num_speech_frames']} ({cpu_stats['speech_percentage']:.2f}%)")
    print(f"  Première frame parole: {cpu_stats['first_speech_frame']} (timecode: {cpu_stats['first_speech_timecode']:.2f}s)")
    print(f"  Dernière frame parole: {cpu_stats['last_speech_frame']} (timecode: {cpu_stats['last_speech_timecode']:.2f}s)")
    print()
    
    print("=== Différences ===")
    diff_frames = cpu_stats['num_speech_frames'] - gpu_stats['num_speech_frames']
    diff_pct = cpu_stats['speech_percentage'] - gpu_stats['speech_percentage']
    if diff_pct == 0:
        diff_pct_desc = "0.00%"
    else:
        diff_pct_desc = f"{abs(diff_pct):.2f}% {'plus' if diff_pct > 0 else 'moins'}"
    print(f"  Différence frames parole: {diff_frames:+d} frames (CPU a {diff_pct_desc} de parole)")
    
    if gpu_stats['first_speech_frame'] and cpu_stats['first_speech_frame']:
        diff_first = gpu_stats['first_speech_frame'] - cpu_stats['first_speech_frame']
        diff_first_time = gpu_stats['first_speech_timecode'] - cpu_stats['first_speech_timecode']
        print(f"  Décalage première détection: {diff_first:+d} frames ({diff_first_time:+.2f}s)")
        if diff_first == 0:
            print("    GPU et CPU détectent la parole au même moment")
        else:
            print(f"    GPU détecte la parole {'plus tard' if diff_first > 0 else 'plus tôt'} que CPU")
    
    print()
    print("=== Diagnostic ===")
    if abs(diff_pct) > 5:
        print("⚠️  DIVERGENCE SIGNIFICATIVE détectée (>5% de différence)")
        print("    Causes possibles:")
        print("    - AMP/mixed precision sur GPU change les scores de diarisation")
        print("    - Différence de seuils/confidence entre GPU et CPU")
        print("    - Bug dans le mapping segments→frames (bords, arrondis)")
        print("    - Segments diarization différents entre GPU et CPU (non-déterminisme)")
    else:
        print("✓ Divergence acceptable (<5%)")


if __name__ == "__main__":
    main()
