#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aggregate Step 5 tracking metrics from generated JSON files.
Outputs a concise table (CSV) with: video, total_frames, fps, face_frames, face_rate_pct.
"""
import os
import json
import argparse
from pathlib import Path


def compute_metrics(json_path: Path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    meta = data.get('metadata', {})
    frames = data.get('frames', [])
    total_frames = int(meta.get('total_frames', len(frames)))
    fps = float(meta.get('fps', 0.0))
    # Count frames that contain at least one tracked object with label 'face'
    face_frames = 0
    for fr in frames:
        tracked = fr.get('tracked_objects', []) or []
        if any((obj.get('label') == 'face') for obj in tracked):
            face_frames += 1
    face_rate = (face_frames / total_frames * 100.0) if total_frames > 0 else 0.0
    return total_frames, fps, face_frames, face_rate


VIDEO_EXTS = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}


def is_tracking_json(path: Path) -> bool:
    if path.name.endswith('_audio.json'):
        return False
    # Require sibling video with same stem
    stem = path.with_suffix('')
    parent = path.parent
    for ext in VIDEO_EXTS:
        if (parent / (stem.name + ext)).exists():
            return True
    return False


def find_jsons(root: Path):
    for dp, _, files in os.walk(root):
        for f in files:
            if not f.lower().endswith('.json'):
                continue
            p = Path(dp) / f
            if is_tracking_json(p):
                yield p


def main():
    parser = argparse.ArgumentParser(description='Aggregate metrics from Step 5 JSON outputs')
    parser.add_argument('--root', default='projets_extraits', help='Root directory to scan for JSON results')
    parser.add_argument('--out', default='step5_metrics.csv', help='Output CSV path')
    args = parser.parse_args()

    rows = [("video", "total_frames", "fps", "face_frames", "face_rate_pct")]
    json_files = list(find_jsons(Path(args.root)))
    json_files.sort()

    for jf in json_files:
        try:
            with open(jf, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Ensure tracking schema
            if not isinstance(data.get('frames'), list):
                raise ValueError('missing frames[] in JSON')
            total_frames, fps, face_frames, face_rate = compute_metrics(jf)
            rows.append((jf.stem, total_frames, f"{fps:.2f}", face_frames, f"{face_rate:.2f}"))
        except Exception as e:
            rows.append((jf.stem, 'ERR', 'ERR', 'ERR', f'error: {e}'))

    with open(args.out, 'w', encoding='utf-8') as out:
        for r in rows:
            out.write(','.join(map(str, r)) + '\n')

    print(f"Wrote {len(rows)-1} rows to {args.out}")


if __name__ == '__main__':
    main()
