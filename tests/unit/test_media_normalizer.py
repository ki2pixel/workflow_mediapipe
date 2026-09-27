# -*- coding: utf-8 -*-
"""Tests de la normalisation vidéo portée par STEP1 (ex-STEP2)."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from utils import media_normalizer


def _analyzed_info(path: Path, fps: float = 25.0, video_codec: str = "h264", audio_codec: str | None = None) -> dict:
    return {
        "path": path,
        "fps": fps,
        "video_codec": video_codec,
        "audio_codec": audio_codec,
        "needs_fps_fix": fps is not None and abs(fps - media_normalizer.TARGET_FPS) > media_normalizer.FPS_TOLERANCE,
        "error": None,
    }


class TestFfprobeParsing:
    """Analyse du framerate via ffprobe."""

    def test_parse_ffprobe_fps_prefers_counts_over_nominal_rates(self):
        # Given: des taux nominaux à 25 fps mais un comptage réel à ~12.7 fps
        payload = {
            "streams": [
                {
                    "codec_type": "video",
                    "avg_frame_rate": "25/1",
                    "r_frame_rate": "25/1",
                    "nb_frames": "2318",
                    "duration": "182.20",
                }
            ]
        }

        # When: parsing du payload ffprobe
        fps = media_normalizer._parse_ffprobe_fps(payload)

        # Then: le comptage réel primes sur les taux nominaux
        assert fps is not None
        assert 12.6 < fps < 12.8

    def test_parse_ffprobe_fps_falls_back_to_avg_rate(self):
        # Given: aucun comptage, avg et r_frame_rate divergents
        payload = {"streams": [{"codec_type": "video", "avg_frame_rate": "25/1", "r_frame_rate": "50/1"}]}

        # When: parsing du payload ffprobe
        fps = media_normalizer._parse_ffprobe_fps(payload)

        # Then: avg_frame_rate est retenu
        assert fps == 25.0

    def test_parse_ffprobe_fraction_rejects_invalid_values(self):
        # Given / When / Then: les fractions illisibles ou dégénérées sont rejetées
        assert media_normalizer._parse_ffprobe_fraction("") is None
        assert media_normalizer._parse_ffprobe_fraction("0/0") is None
        assert media_normalizer._parse_ffprobe_fraction("25/0") is None
        assert media_normalizer._parse_ffprobe_fraction("25/2") == 12.5

    def test_analyze_video_uses_ffprobe_json(self, monkeypatch, tmp_path):
        # Given: un ffprobe simulé renvoyant un comptage exploitable
        fake_payload = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "avg_frame_rate": "0/0",
                    "r_frame_rate": "25/1",
                    "nb_frames": "2318",
                    "duration": "182.20",
                }
            ]
        }

        def fake_run(*_args, **_kwargs):
            return SimpleNamespace(stdout=json.dumps(fake_payload))

        monkeypatch.setattr(media_normalizer.subprocess, "run", fake_run)
        video_path = tmp_path / "video.mp4"
        video_path.write_bytes(b"")

        # When: analyse de la vidéo
        info = media_normalizer.analyze_video(video_path)

        # Then: fps et codec vidéo sont extraits
        assert info["error"] is None
        assert info["video_codec"] == "h264"
        assert 12.6 < info["fps"] < 12.8


class TestConformance:
    """Contrat MP4 / H.264 / 25 fps."""

    def test_is_conformant_accepts_normalized_mp4(self, tmp_path):
        # Given / When / Then: un MP4 H.264 à 25 fps est conforme
        assert media_normalizer.is_conformant(_analyzed_info(tmp_path / "clip.mp4")) is True

    def test_is_conformant_rejects_other_container_codec_and_fps(self, tmp_path):
        # Given: trois écarts au contrat
        wrong_container = _analyzed_info(tmp_path / "clip.mkv")
        wrong_codec = _analyzed_info(tmp_path / "clip.mp4", video_codec="mpeg4")
        wrong_fps = _analyzed_info(tmp_path / "clip.mp4", fps=30.0)

        # When / Then: chacun est refusé
        assert media_normalizer.is_conformant(wrong_container) is False
        assert media_normalizer.is_conformant(wrong_codec) is False
        assert media_normalizer.is_conformant(wrong_fps) is False

    def test_is_conformant_rejects_unknown_fps_and_errors(self, tmp_path):
        # Given: fps indéterminable d'un côté, erreur d'analyse de l'autre
        unknown_fps = _analyzed_info(tmp_path / "clip.mp4", fps=None)
        failed = dict(_analyzed_info(tmp_path / "clip.mp4"), error="ffprobe indisponible")

        # When / Then: dans les deux cas le fichier doit être traité
        assert media_normalizer.is_conformant(unknown_fps) is False
        assert media_normalizer.is_conformant(failed) is False


class TestDiscovery:
    """Découverte des vidéos à normaliser."""

    def test_discover_videos_skips_preserved_mov(self, monkeypatch, tmp_path):
        # Given: un dossier avec un logo .mov et une vidéo .mp4
        work_dir = tmp_path / "docs"
        work_dir.mkdir()
        (work_dir / "logo.mov").write_bytes(b"alpha")
        (work_dir / "reel.mp4").write_bytes(b"video")
        monkeypatch.setenv("SKIP_MOV_FILES", "true")

        # When: découverte des vidéos candidates
        candidates, preserved = media_normalizer.discover_videos(work_dir)

        # Then: le logo est isolé et ne sera jamais encodé
        assert [p.name for p in candidates] == ["reel.mp4"]
        assert [p.name for p in preserved] == ["logo.mov"]

    def test_discover_videos_includes_mov_when_preservation_disabled(self, monkeypatch, tmp_path):
        # Given: la préservation désactivée
        work_dir = tmp_path / "docs"
        work_dir.mkdir()
        (work_dir / "logo.mov").write_bytes(b"alpha")
        (work_dir / "reel.mp4").write_bytes(b"video")
        monkeypatch.setenv("SKIP_MOV_FILES", "false")

        # When: découverte des vidéos candidates
        candidates, preserved = media_normalizer.discover_videos(work_dir)

        # Then: le .mov redevient une cible de normalisation
        assert sorted(p.name for p in candidates) == ["logo.mov", "reel.mp4"]
        assert preserved == []

    def test_discover_videos_skips_internal_temp_files(self, monkeypatch, tmp_path):
        # Given: un dossier contenant un artefact temporaire d'un run interrompu
        work_dir = tmp_path / "docs"
        work_dir.mkdir()
        (work_dir / "clip.temp_normalize.mp4").write_bytes(b"partial")
        (work_dir / "clip.mp4").write_bytes(b"video")
        monkeypatch.setenv("SKIP_MOV_FILES", "true")

        # When: découverte des vidéos candidates
        candidates, _ = media_normalizer.discover_videos(work_dir)

        # Then: le fichier temporaire est ignoré
        assert [p.name for p in candidates] == ["clip.mp4"]


class TestNormalizeVideo:
    """Encodage ffmpeg unitaire."""

    def test_normalize_video_leaves_preserved_mov_untouched(self, monkeypatch, tmp_path):
        # Given: un logo .mov et la préservation active
        logo = tmp_path / "logo.mov"
        logo.write_bytes(b"alpha")
        monkeypatch.setenv("SKIP_MOV_FILES", "true")

        def fail_run(*_args, **_kwargs):
            raise AssertionError("ffmpeg ne doit jamais être invoqué pour un logo préservé")

        monkeypatch.setattr(media_normalizer.subprocess, "run", fail_run)

        # When: le worker traite le fichier
        result = media_normalizer.normalize_video(_analyzed_info(logo))

        # Then: succès immédiat, alpha intact
        assert result is True
        assert logo.exists()
        assert logo.read_bytes() == b"alpha"

    def test_normalize_video_converts_and_replaces_source(self, monkeypatch, tmp_path):
        # Given: une vidéo .avi à normaliser et un ffmpeg simulé qui réussit
        video = tmp_path / "clip.avi"
        video.write_bytes(b"video")
        monkeypatch.setenv("SKIP_MOV_FILES", "false")

        calls = []

        def fake_run(command, **_kwargs):
            calls.append(command)
            Path(command[-1]).write_bytes(b"converted")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(media_normalizer.subprocess, "run", fake_run)

        # When: normalisation de la vidéo (chemin CPU pour vérifier l'encodeur)
        result = media_normalizer.normalize_video(_analyzed_info(video, fps=30.0), use_gpu=False)

        # Then: un MP4 H.264 remplace l'original, avec le filtre fps
        assert result is True
        assert len(calls) == 1
        assert (tmp_path / "clip.mp4").exists()
        assert not video.exists()
        assert "-vf" in calls[0]
        assert "libx264" in calls[0]

    def test_normalize_video_removes_temp_file_on_ffmpeg_failure(self, monkeypatch, tmp_path):
        # Given: un ffmpeg simulé qui échoue
        video = tmp_path / "clip.avi"
        video.write_bytes(b"video")

        def failing_run(command, **_kwargs):
            Path(command[-1]).write_bytes(b"partial")
            return SimpleNamespace(returncode=1, stdout="", stderr="boom")

        monkeypatch.setattr(media_normalizer.subprocess, "run", failing_run)

        # When: normalisation de la vidéo
        result = media_normalizer.normalize_video(_analyzed_info(video), use_gpu=False)

        # Then: échec signalé, aucun artefact temporaire laissé derrière
        assert result is False
        assert not (tmp_path / "clip.temp_normalize.mp4").exists()
        assert video.exists()

    def test_normalize_video_with_fallback_retries_on_cpu(self, monkeypatch, tmp_path):
        # Given: un encodage GPU qui échoue
        video = tmp_path / "clip.avi"
        video.write_bytes(b"video")
        attempts = []

        def fake_normalize(_info, use_gpu=True, **_kwargs):
            attempts.append(use_gpu)
            return use_gpu is False

        monkeypatch.setattr(media_normalizer, "normalize_video", fake_normalize)

        # When: normalisation avec fallback
        result = media_normalizer.normalize_video_with_fallback(_analyzed_info(video))

        # Then: le CPU prend le relais
        assert result is True
        assert attempts == [True, False]


class TestNormalizeVideosIn:
    """Passe complète sur un dossier."""

    def test_normalize_videos_in_skips_conformant_files(self, monkeypatch, tmp_path):
        # Given: un fichier déjà conforme et un fichier à normaliser
        work_dir = tmp_path / "docs"
        work_dir.mkdir()
        conformant = work_dir / "ready.mp4"
        legacy = work_dir / "legacy.avi"
        conformant.write_bytes(b"video")
        legacy.write_bytes(b"video")
        monkeypatch.setenv("SKIP_MOV_FILES", "true")

        def fake_analyze(path, _target_fps=media_normalizer.TARGET_FPS):
            if Path(path).name == "ready.mp4":
                return _analyzed_info(Path(path))
            return _analyzed_info(Path(path), fps=30.0, video_codec="mpeg4")

        processed = []

        def fake_fallback(video_info, **_kwargs):
            processed.append(Path(video_info["path"]).name)
            return True

        monkeypatch.setattr(media_normalizer, "analyze_video", fake_analyze)
        monkeypatch.setattr(media_normalizer, "normalize_video_with_fallback", fake_fallback)

        # When: passe de normalisation sans --force
        summary = media_normalizer.normalize_videos_in(work_dir)

        # Then: seul le fichier non conforme est encodé
        assert processed == ["legacy.avi"]
        assert summary.total == 1
        assert summary.success == 1
        assert summary.failed == 0
        assert summary.skipped == 1
        assert summary.is_success is True

    def test_normalize_videos_in_force_reencodes_conformant_files(self, monkeypatch, tmp_path):
        # Given: un fichier déjà conforme
        work_dir = tmp_path / "docs"
        work_dir.mkdir()
        (work_dir / "ready.mp4").write_bytes(b"video")
        monkeypatch.setenv("SKIP_MOV_FILES", "true")

        monkeypatch.setattr(
            media_normalizer, "analyze_video",
            lambda path, _target_fps=media_normalizer.TARGET_FPS: _analyzed_info(Path(path)),
        )
        processed = []

        def fake_fallback(video_info, **_kwargs):
            processed.append(Path(video_info["path"]).name)
            return True

        monkeypatch.setattr(media_normalizer, "normalize_video_with_fallback", fake_fallback)

        # When: passe de normalisation forcée (sources brutes fraîchement extraites)
        summary = media_normalizer.normalize_videos_in(work_dir, force=True)

        # Then: le fichier est ré-encodé malgré sa conformité
        assert processed == ["ready.mp4"]
        assert summary.total == 1
        assert summary.skipped == 0

    def test_normalize_videos_in_reports_failures(self, monkeypatch, tmp_path):
        # Given: une vidéo dont l'encodage échoue
        work_dir = tmp_path / "docs"
        work_dir.mkdir()
        (work_dir / "legacy.avi").write_bytes(b"video")

        monkeypatch.setattr(
            media_normalizer, "analyze_video",
            lambda path, _target_fps=media_normalizer.TARGET_FPS: _analyzed_info(Path(path), fps=30.0),
        )
        monkeypatch.setattr(media_normalizer, "normalize_video_with_fallback", lambda *_a, **_k: False)

        # When: passe de normalisation
        summary = media_normalizer.normalize_videos_in(work_dir)

        # Then: l'échec est comptabilisé et la passe est déclarée en erreur
        assert summary.total == 1
        assert summary.failed == 1
        assert summary.is_success is False

    def test_normalize_videos_in_handles_empty_directory(self, tmp_path):
        # Given: un dossier sans vidéo
        work_dir = tmp_path / "docs"
        work_dir.mkdir()

        # When: passe de normalisation
        summary = media_normalizer.normalize_videos_in(work_dir)

        # Then: aucune vidéo traitée, aucune erreur
        assert summary.total == 0
        assert summary.success == 0
        assert summary.failed == 0
        assert summary.is_success is True


class TestFpsGuard:
    """Garde-fou utilisé par les étapes d'analyse en aval."""

    def test_check_fps_conformance_returns_none_for_conformant_file(self, monkeypatch, tmp_path):
        # Given: une vidéo normalisée à 25 fps
        video = tmp_path / "clip.mp4"
        video.write_bytes(b"video")
        monkeypatch.setattr(
            media_normalizer, "analyze_video",
            lambda path, _target_fps=media_normalizer.TARGET_FPS: _analyzed_info(Path(path)),
        )

        # When / Then: aucune anomalie signalée
        assert media_normalizer.check_fps_conformance(video) is None

    def test_check_fps_conformance_reports_deviation(self, monkeypatch, tmp_path):
        # Given: une vidéo non normalisée à 30 fps
        video = tmp_path / "clip.mp4"
        video.write_bytes(b"video")
        monkeypatch.setattr(
            media_normalizer, "analyze_video",
            lambda path, _target_fps=media_normalizer.TARGET_FPS: _analyzed_info(Path(path), fps=30.0),
        )

        # When: contrôle du framerate
        detected = media_normalizer.check_fps_conformance(video)

        # Then: l'écart est remonté pour avertir l'opérateur
        assert detected == pytest.approx(30.0)
