# -*- coding: utf-8 -*-
import importlib.util
from pathlib import Path
from types import SimpleNamespace


def _load_convert_videos_module():
    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "workflow_scripts" / "step2" / "convert_videos.py"
    spec = importlib.util.spec_from_file_location("step2_convert_videos_preserved", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _analyzed_info(path: Path) -> dict:
    return {
        "path": path,
        "fps": 25.0,
        "audio_codec": None,
        "needs_fps_fix": False,
        "error": None,
    }


def test_find_and_analyze_videos_skips_preserved_mov(monkeypatch, tmp_path):
    # Given: un dossier de travail avec un logo .mov et une vidéo .mp4
    module = _load_convert_videos_module()
    work_dir = tmp_path / "docs"
    work_dir.mkdir()
    (work_dir / "logo.mov").write_bytes(b"alpha")
    (work_dir / "reel.mp4").write_bytes(b"video")
    monkeypatch.setattr(module, "WORK_DIR", work_dir)
    monkeypatch.setenv("SKIP_MOV_FILES", "true")

    analyzed = []

    def fake_analyze(path):
        analyzed.append(path.name)
        return _analyzed_info(path)

    monkeypatch.setattr(module, "analyze_video", fake_analyze)

    # When: recherche et analyse des vidéos à convertir
    videos = module.find_and_analyze_videos()

    # Then: seul le .mp4 est analysé, le .mov n'est même pas passé à ffprobe
    assert [v["path"].name for v in videos] == ["reel.mp4"]
    assert analyzed == ["reel.mp4"]


def test_find_and_analyze_videos_includes_mov_when_disabled(monkeypatch, tmp_path):
    # Given: la préservation désactivée et un dossier avec un .mov et un .mp4
    module = _load_convert_videos_module()
    work_dir = tmp_path / "docs"
    work_dir.mkdir()
    (work_dir / "logo.mov").write_bytes(b"alpha")
    (work_dir / "reel.mp4").write_bytes(b"video")
    monkeypatch.setattr(module, "WORK_DIR", work_dir)
    monkeypatch.setenv("SKIP_MOV_FILES", "false")

    analyzed = []

    def fake_analyze(path):
        analyzed.append(path.name)
        return _analyzed_info(path)

    monkeypatch.setattr(module, "analyze_video", fake_analyze)

    # When: recherche et analyse des vidéos à convertir
    videos = module.find_and_analyze_videos()

    # Then: le .mov redevient une cible de conversion
    assert sorted(v["path"].name for v in videos) == ["logo.mov", "reel.mp4"]
    assert sorted(analyzed) == ["logo.mov", "reel.mp4"]


def test_process_single_video_leaves_preserved_mov_untouched(monkeypatch, tmp_path):
    # Given: un logo .mov et la préservation active
    module = _load_convert_videos_module()
    logo = tmp_path / "logo.mov"
    logo.write_bytes(b"alpha")
    monkeypatch.setenv("SKIP_MOV_FILES", "true")

    def fail_run(*_args, **_kwargs):
        raise AssertionError("ffmpeg ne doit jamais être invoqué pour un logo préservé")

    monkeypatch.setattr(module.subprocess, "run", fail_run)

    # When: un worker tente de traiter le fichier
    result = module.process_single_video(_analyzed_info(logo))

    # Then: succès immédiat, fichier intact (alpha conservé)
    assert result is True
    assert logo.exists()
    assert logo.read_bytes() == b"alpha"


def test_process_single_video_converts_when_preservation_disabled(monkeypatch, tmp_path):
    # Given: la préservation désactivée et un worker simulé qui réussit
    module = _load_convert_videos_module()
    video = tmp_path / "clip.avi"
    video.write_bytes(b"video")
    monkeypatch.setenv("SKIP_MOV_FILES", "false")

    calls = []

    def fake_run(command, **_kwargs):
        calls.append(command)
        Path(command[-1]).write_bytes(b"converted")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    # When: traitement de la vidéo
    result = module.process_single_video(_analyzed_info(video))

    # Then: la conversion a bien lieu et l'original est remplacé
    assert result is True
    assert len(calls) == 1
    assert (tmp_path / "clip.mp4").exists()
    assert not video.exists()
