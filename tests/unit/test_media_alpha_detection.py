# -*- coding: utf-8 -*-
"""Tests de la détection de couche alpha des .mov (ffprobe + plan B MediaInfo)."""
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from utils import media_filters


@pytest.fixture(autouse=True)
def _clear_alpha_cache():
    media_filters.reset_alpha_cache()
    yield
    media_filters.reset_alpha_cache()


class TestPixFmtDetection:
    """Classement des formats de pixels FFmpeg."""

    def test_pix_fmt_with_alpha(self):
        # Given / When / Then: tous les formats porteurs d'alpha sont reconnus
        for pix_fmt in (
            "yuva420p", "yuva444p12le", "argb", "rgba", "bgra", "abgr",
            "gbrap12le", "ayuv64le", "ya8", "ya16le",
        ):
            assert media_filters._pix_fmt_has_alpha(pix_fmt) is True, pix_fmt

    def test_pix_fmt_without_alpha(self):
        # Given / When / Then: les formats opaques ne sont jamais classés alpha
        for pix_fmt in ("yuv420p", "yuv422p10le", "yuv444p10le", "rgb24", "bgr24", "", None):
            assert media_filters._pix_fmt_has_alpha(pix_fmt) is False, pix_fmt


class TestFfprobeStage:
    """Étage 1 : verdict déduit du pix_fmt ffprobe."""

    def _patch_ffprobe(self, monkeypatch, payload=None, error=None):
        def fake_run(*_args, **_kwargs):
            if error is not None:
                raise error
            return SimpleNamespace(stdout=json.dumps(payload), stderr="")

        monkeypatch.setattr(media_filters.subprocess, "run", fake_run)

    def test_alpha_pix_fmt_wins(self, monkeypatch, tmp_path):
        # Given: un flux vidéo au pix_fmt alpha
        self._patch_ffprobe(
            monkeypatch,
            {"streams": [{"codec_name": "prores", "codec_tag_string": "ap4h", "pix_fmt": "yuva444p10le"}]},
        )

        # When / Then: l'alpha est détecté
        assert media_filters._probe_alpha_ffprobe(tmp_path / "a.mov") is True

    def test_all_streams_explicitly_without_alpha_is_definitive(self, monkeypatch, tmp_path):
        # Given: deux flux vidéo opaques au pix_fmt explicite
        self._patch_ffprobe(
            monkeypatch,
            {"streams": [{"pix_fmt": "yuv420p"}, {"pix_fmt": "yuv422p10le"}]},
        )

        # When / Then: le verdict négatif est définitif
        assert media_filters._probe_alpha_ffprobe(tmp_path / "a.mov") is False

    def test_missing_pix_fmt_with_alpha_tag(self, monkeypatch, tmp_path):
        # Given: un pix_fmt manquant mais un tag conteneur alpha-capable
        self._patch_ffprobe(monkeypatch, {"streams": [{"codec_tag_string": "ap4h"}]})

        # When / Then: le tag tranche en faveur de l'alpha
        assert media_filters._probe_alpha_ffprobe(tmp_path / "a.mov") is True

    def test_missing_pix_fmt_without_alpha_tag_is_undetermined(self, monkeypatch, tmp_path):
        # Given: un pix_fmt manquant et un tag non alpha-capable
        self._patch_ffprobe(monkeypatch, {"streams": [{"codec_tag_string": "avc1"}]})

        # When / Then: le verdict reste indéterminé (passage au plan B)
        assert media_filters._probe_alpha_ffprobe(tmp_path / "a.mov") is None

    def test_empty_streams_or_probe_failure_is_undetermined(self, monkeypatch, tmp_path):
        # Given / When / Then: aucun flux ou ffprobe en échec => indéterminé
        self._patch_ffprobe(monkeypatch, {"streams": []})
        assert media_filters._probe_alpha_ffprobe(tmp_path / "a.mov") is None

        self._patch_ffprobe(monkeypatch, error=OSError("ffprobe introuvable"))
        assert media_filters._probe_alpha_ffprobe(tmp_path / "a.mov") is None


class TestMediaInfoStage:
    """Étage 2 (plan B) : verdict déduit des deux schémas MediaInfo."""

    def _patch_payload(self, monkeypatch, payload):
        monkeypatch.setattr(media_filters, "_mediainfo_payload", lambda _path: payload)

    def test_cli_schema_prores_4444(self, monkeypatch, tmp_path):
        # Given: schéma CLI (media/track, clés PascalCase)
        self._patch_payload(
            monkeypatch,
            {"media": {"track": [{"@type": "Video", "Format": "ProRes", "Format_Profile": "4444", "CodecID": "ap4h"}]}},
        )

        # When / Then: ProRes 4444 => alpha
        assert media_filters._probe_alpha_mediainfo(tmp_path / "a.mov") is True

    def test_binding_schema_qtrle_and_png(self, monkeypatch, tmp_path):
        # Given: schéma pymediainfo (tracks, clés snake_case)
        self._patch_payload(monkeypatch, {"tracks": [{"track_type": "Video", "format": "RLE", "codec_id": "rle "}]})
        assert media_filters._probe_alpha_mediainfo(tmp_path / "a.mov") is True

        self._patch_payload(monkeypatch, {"tracks": [{"track_type": "Video", "format": "PNG", "codec_id": "png "}]})
        assert media_filters._probe_alpha_mediainfo(tmp_path / "a.mov") is True

    def test_non_alpha_formats(self, monkeypatch, tmp_path):
        # Given: AVC puis ProRes 422
        self._patch_payload(monkeypatch, {"tracks": [{"track_type": "Video", "format": "AVC", "codec_id": "avc1"}]})
        assert media_filters._probe_alpha_mediainfo(tmp_path / "a.mov") is False

        self._patch_payload(
            monkeypatch,
            {"media": {"track": [{"@type": "Video", "Format": "ProRes", "Format_Profile": "422", "CodecID": "apcn"}]}},
        )
        assert media_filters._probe_alpha_mediainfo(tmp_path / "a.mov") is False

    def test_unknown_format_or_no_video_track_is_undetermined(self, monkeypatch, tmp_path):
        # Given: un format inconnu puis une piste audio seule
        self._patch_payload(monkeypatch, {"tracks": [{"track_type": "Video", "format": "Weird"}]})
        assert media_filters._probe_alpha_mediainfo(tmp_path / "a.mov") is None

        self._patch_payload(monkeypatch, {"tracks": [{"track_type": "Audio", "format": "AAC"}]})
        assert media_filters._probe_alpha_mediainfo(tmp_path / "a.mov") is None

    def test_missing_payload_is_undetermined(self, monkeypatch, tmp_path):
        # Given: MediaInfo indisponible (None)
        self._patch_payload(monkeypatch, None)

        # When / Then: indéterminé
        assert media_filters._probe_alpha_mediainfo(tmp_path / "a.mov") is None


class TestAlphaCache:
    """Cache des verdicts définitifs, invalidé par mtime/taille."""

    def test_definitive_verdicts_are_cached(self, monkeypatch, tmp_path):
        # Given: un fichier réel et un probe compté
        video = tmp_path / "clip.mov"
        video.write_bytes(b"video")
        calls = []

        def fake_probe(path):
            calls.append(path)
            return False

        monkeypatch.setattr(media_filters, "_probe_alpha_ffprobe", fake_probe)
        monkeypatch.setattr(media_filters, "_probe_alpha_mediainfo", lambda _path: None)

        # When: deux interrogations du même fichier
        assert media_filters.has_alpha_channel(video) is False
        assert media_filters.has_alpha_channel(video) is False

        # Then: un seul probe a été lancé
        assert len(calls) == 1

    def test_undetermined_verdicts_are_not_cached(self, monkeypatch, tmp_path):
        # Given: un probe qui ne tranche jamais
        video = tmp_path / "clip.mov"
        video.write_bytes(b"video")
        calls = []

        def fake_probe(path):
            calls.append(path)
            return None

        monkeypatch.setattr(media_filters, "_probe_alpha_ffprobe", fake_probe)
        monkeypatch.setattr(media_filters, "_probe_alpha_mediainfo", lambda _path: None)

        # When: deux interrogations
        assert media_filters.has_alpha_channel(video) is None
        assert media_filters.has_alpha_channel(video) is None

        # Then: chaque appel re-sonde (pas de verdict périmé)
        assert len(calls) == 2

    def test_reset_alpha_cache_forces_reprobe(self, monkeypatch, tmp_path):
        # Given: un verdict déjà en cache
        video = tmp_path / "clip.mov"
        video.write_bytes(b"video")
        calls = []

        def fake_probe(path):
            calls.append(path)
            return False

        monkeypatch.setattr(media_filters, "_probe_alpha_ffprobe", fake_probe)
        monkeypatch.setattr(media_filters, "_probe_alpha_mediainfo", lambda _path: None)
        media_filters.has_alpha_channel(video)

        # When: le cache est vidé puis le fichier ré-interrogé
        media_filters.reset_alpha_cache()
        media_filters.has_alpha_channel(video)

        # Then: un second probe a eu lieu
        assert len(calls) == 2


def _encode(path: Path, *args: str) -> None:
    command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args, str(path)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        pytest.skip(f"encodage ffmpeg indisponible ({path.name}): {result.stderr.strip()[:200]}")


@pytest.fixture(scope="module")
def real_mov_matrix(tmp_path_factory):
    """Matrice de .mov réels : alpha (ProRes 4444, Animation, PNG), opaques, corrompu."""
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        pytest.skip("ffmpeg/ffprobe requis pour les fixtures réelles")

    root = tmp_path_factory.mktemp("mov-matrix")
    alpha_prores = root / "alpha_prores4444.mov"
    alpha_qtrle = root / "alpha_qtrle.mov"
    alpha_png = root / "alpha_png.mov"
    video_h264 = root / "video_h264.mov"
    video_prores422 = root / "video_prores422.mov"

    _encode(alpha_prores, "-f", "lavfi", "-i", "color=c=red@0.5:s=64x64:r=25,format=yuva444p10le",
            "-c:v", "prores_ks", "-profile:v", "4444", "-t", "0.2")
    _encode(alpha_qtrle, "-f", "lavfi", "-i", "color=c=green@0.5:s=64x64:r=25,format=argb",
            "-c:v", "qtrle", "-t", "0.2")
    _encode(alpha_png, "-f", "lavfi", "-i", "color=c=blue@0.5:s=64x64:r=25,format=rgba",
            "-c:v", "png", "-t", "0.2")
    _encode(video_h264, "-f", "lavfi", "-i", "testsrc=s=64x64:r=25",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-t", "0.2")
    _encode(video_prores422, "-f", "lavfi", "-i", "testsrc=s=64x64:r=25",
            "-c:v", "prores_ks", "-profile:v", "2", "-pix_fmt", "yuv422p10le", "-t", "0.2")

    m6 = root / "m6+.mov"
    shutil.copyfile(video_h264, m6)
    corrupt = root / "corrupt.mov"
    corrupt.write_bytes(b"not a video at all")

    return {
        "alpha_prores4444": alpha_prores,
        "alpha_qtrle": alpha_qtrle,
        "alpha_png": alpha_png,
        "video_h264": video_h264,
        "video_prores422": video_prores422,
        "m6": m6,
        "corrupt": corrupt,
    }


class TestRealFixtures:
    """Vérification de bout en bout sur de vrais fichiers encodés par ffmpeg."""

    def test_alpha_movs_are_preserved(self, real_mov_matrix):
        # Given / When / Then: les trois familles alpha sont détectées et préservées
        for key in ("alpha_prores4444", "alpha_qtrle", "alpha_png"):
            path = real_mov_matrix[key]
            assert media_filters.has_alpha_channel(path) is True, key
            assert media_filters.is_preserved_media(path) is True, key

    def test_non_alpha_movs_are_processable(self, real_mov_matrix):
        # Given / When / Then: AVC et ProRes 422 sont traitables
        for key in ("video_h264", "video_prores422"):
            path = real_mov_matrix[key]
            assert media_filters.has_alpha_channel(path) is False, key
            assert media_filters.is_preserved_media(path) is False, key

    def test_m6_mov_is_preserved_despite_no_alpha(self, real_mov_matrix):
        # Given: m6+.mov sans couche alpha
        path = real_mov_matrix["m6"]

        # When / Then: la liste noire le préserve quand même
        assert media_filters.has_alpha_channel(path) is False
        assert media_filters.is_preserved_media(path) is True

    def test_corrupt_mov_is_preserved_by_precaution(self, real_mov_matrix):
        # Given: un .mov illisible
        path = real_mov_matrix["corrupt"]

        # When / Then: alpha indéterminable => préservation par précaution
        assert media_filters.has_alpha_channel(path) is None
        assert media_filters.is_preserved_media(path) is True
