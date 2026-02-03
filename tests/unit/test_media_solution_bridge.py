import importlib.util
import json
from pathlib import Path

import pytest


def _load_bridge_module():
    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "scripts" / "after_effects" / "media_solution_bridge.py"
    spec = importlib.util.spec_from_file_location("scripts.after_effects.media_solution_bridge", module_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _write_csv(path: Path, lines):
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_analyze_manifest_parses_timecodes_and_snaps_end_to_next_start(tmp_path):
    mod = _load_bridge_module()

    # Given: Preconditions
    csv_path = tmp_path / "video.csv"
    _write_csv(
        csv_path,
        [
            "num,start,end,frame_in,frame_out",
            "1,00:00:00.000,00:00:01.000,1,25",
            "2,00:00:01.040,00:00:02.000,26,50",
        ],
    )
    manifest = {
        "mode": "cuts",
        "csv_path": str(csv_path),
        "frame_rate": 25.0,
        "comp_duration": 100.0,
        "config": {"SNAP_FACTOR": 1.1},
    }

    # When:  Operation to execute
    results = mod.analyze_manifest(manifest)

    # Then:  Expected result/verification
    assert "segments" in results
    assert results["stats"]["raw_segments"] == 2
    assert results["stats"]["kept_segments"] == 2

    seg1 = results["segments"][0]
    seg2 = results["segments"][1]

    assert seg1["num"] == "1"
    assert seg2["num"] == "2"

    # 00:00:01.000 == 1.0 ; next startTime is 1.04 so gap=0.04 which is exactly 1 frame at 25fps
    assert pytest.approx(seg1["endTime"], rel=1e-6) == seg2["startTime"]


def test_analyze_manifest_parses_first_line_without_header(tmp_path):
    mod = _load_bridge_module()

    # Given: Preconditions
    csv_path = tmp_path / "video.csv"
    _write_csv(
        csv_path,
        [
            "1,00:00:00.000,00:00:01.000,1,25",
            "2,00:00:01.000,00:00:02.000,26,50",
        ],
    )
    manifest = {
        "mode": "cuts",
        "csv_path": str(csv_path),
        "frame_rate": 25.0,
        "comp_duration": 10.0,
    }

    # When:  Operation to execute
    results = mod.analyze_manifest(manifest)

    # Then:  Expected result/verification
    assert results["stats"]["raw_segments"] == 2
    assert len(results["segments"]) == 2


def test_analyze_manifest_clamps_to_comp_duration(tmp_path):
    mod = _load_bridge_module()

    # Given: Preconditions
    csv_path = tmp_path / "video.csv"
    _write_csv(
        csv_path,
        [
            "num,start,end",
            "1,00:00:00.000,00:00:05.000",
        ],
    )
    manifest = {
        "mode": "cuts",
        "csv_path": str(csv_path),
        "frame_rate": 25.0,
        "comp_duration": 2.0,
    }

    # When:  Operation to execute
    results = mod.analyze_manifest(manifest)

    # Then:  Expected result/verification
    assert len(results["segments"]) == 1
    assert pytest.approx(results["segments"][0]["endTime"], rel=1e-6) == 2.0


def test_analyze_manifest_skips_too_short_segment_and_emits_warning(tmp_path):
    mod = _load_bridge_module()

    # Given: Preconditions
    csv_path = tmp_path / "video.csv"
    _write_csv(
        csv_path,
        [
            "num,start,end",
            "1,00:00:00.000,00:00:02.000",
            "2,00:00:00.010,00:00:01.000",
        ],
    )
    manifest = {
        "mode": "cuts",
        "csv_path": str(csv_path),
        "frame_rate": 25.0,
        "comp_duration": 10.0,
    }

    # When:  Operation to execute
    results = mod.analyze_manifest(manifest)

    # Then:  Expected result/verification
    assert results["stats"]["raw_segments"] == 2
    assert results["stats"]["kept_segments"] == 1
    assert len(results["segments"]) == 1
    assert results["segments"][0]["num"] == "2"
    assert results["warnings"] == ["segment_too_short:1"]


def test_analyze_manifest_rejects_invalid_mode(tmp_path):
    mod = _load_bridge_module()

    # Given: Preconditions
    csv_path = tmp_path / "video.csv"
    _write_csv(csv_path, ["num,start,end", "1,00:00:00,000,00:00:01,000"])
    manifest = {"mode": "unknown", "csv_path": str(csv_path), "frame_rate": 25.0}

    # When:  Operation to execute
    with pytest.raises(ValueError) as exc:
        mod.analyze_manifest(manifest)

    # Then:  Expected result/verification
    assert "manifest.mode" in str(exc.value)


def test_analyze_manifest_rejects_invalid_frame_rate(tmp_path):
    mod = _load_bridge_module()

    # Given: Preconditions
    csv_path = tmp_path / "video.csv"
    _write_csv(csv_path, ["num,start,end", "1,00:00:00,000,00:00:01,000"])
    manifest = {"mode": "cuts", "csv_path": str(csv_path), "frame_rate": 0}

    # When:  Operation to execute
    with pytest.raises(ValueError) as exc:
        mod.analyze_manifest(manifest)

    # Then:  Expected result/verification
    assert "frame_rate" in str(exc.value)


def test_analyze_manifest_rejects_missing_csv_file(tmp_path):
    mod = _load_bridge_module()

    # Given: Preconditions
    missing_path = tmp_path / "missing.csv"
    manifest = {"mode": "cuts", "csv_path": str(missing_path), "frame_rate": 25.0}

    # When:  Operation to execute
    with pytest.raises(ValueError) as exc:
        mod.analyze_manifest(manifest)

    # Then:  Expected result/verification
    assert "CSV introuvable" in str(exc.value)


def test_main_writes_error_json_on_failure(tmp_path, monkeypatch):
    mod = _load_bridge_module()

    # Given: Preconditions
    manifest_path = tmp_path / "manifest.json"
    out_path = tmp_path / "out.json"
    manifest_path.write_text(json.dumps({"mode": "cuts"}), encoding="utf-8")

    monkeypatch.setattr(
        mod.argparse.ArgumentParser,
        "parse_args",
        lambda self: type("Args", (), {"manifest_path": str(manifest_path), "output_path": str(out_path)})(),
    )

    # When:  Operation to execute
    mod.main()

    # Then:  Expected result/verification
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert "error" in payload
