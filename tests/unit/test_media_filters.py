# -*- coding: utf-8 -*-
from pathlib import Path

from utils import media_filters
from utils.media_filters import (
    get_preserved_mov_names,
    is_preserved_media,
    is_skip_preserved_media_enabled,
    split_preserved_media,
)


def test_skip_preserved_media_enabled_by_default(monkeypatch):
    # Given: aucune variable SKIP_MOV_FILES n'est définie
    monkeypatch.delenv("SKIP_MOV_FILES", raising=False)

    # When: interrogation du flag
    enabled = is_skip_preserved_media_enabled()

    # Then: la préservation est active par défaut
    assert enabled is True


def test_skip_preserved_media_can_be_disabled(monkeypatch):
    # Given: la variable SKIP_MOV_FILES est explicitement désactivée
    monkeypatch.setenv("SKIP_MOV_FILES", "false")

    # When: interrogation du flag
    enabled = is_skip_preserved_media_enabled()

    # Then: la préservation est désactivée
    assert enabled is False


def test_preserved_mov_names_default(monkeypatch):
    # Given: aucune variable PRESERVED_MOV_NAMES n'est définie
    monkeypatch.delenv("PRESERVED_MOV_NAMES", raising=False)

    # When / Then: seule la liste noire historique est appliquée
    assert get_preserved_mov_names() == ("m6+.mov",)


def test_preserved_mov_names_env_override(monkeypatch):
    # Given: une liste noire surchargée, casse et espaces compris
    monkeypatch.setenv("PRESERVED_MOV_NAMES", "Autre.MOV, logo2.mov")

    # When: lecture des noms préservés
    names = get_preserved_mov_names()

    # Then: les noms sont normalisés en minuscules
    assert names == ("autre.mov", "logo2.mov")


def test_preserved_mov_names_env_empty_disables_blacklist(monkeypatch):
    # Given: une liste noire explicitement vidée
    monkeypatch.setenv("PRESERVED_MOV_NAMES", "")

    # When / Then: plus aucun nom n'est préservé d'office
    assert get_preserved_mov_names() == ()


def test_is_preserved_media_alpha_mov_preserved(monkeypatch, tmp_path):
    # Given: un .mov porteur d'une couche alpha
    monkeypatch.setenv("SKIP_MOV_FILES", "true")
    monkeypatch.setattr(media_filters, "has_alpha_channel", lambda _path: True)

    # When / Then: le logo est préservé
    assert is_preserved_media(tmp_path / "logo.mov") is True


def test_is_preserved_media_without_alpha_is_processed(monkeypatch, tmp_path):
    # Given: un .mov sans couche alpha hors liste noire
    monkeypatch.setenv("SKIP_MOV_FILES", "true")
    monkeypatch.setattr(media_filters, "has_alpha_channel", lambda _path: False)

    # When / Then: le fichier redevient une vidéo à traiter
    assert is_preserved_media(tmp_path / "reel.mov") is False


def test_is_preserved_media_m6_name_short_circuits_probe(monkeypatch, tmp_path):
    # Given: le nom de la liste noire (casse variée) et un probe piégé
    monkeypatch.setenv("SKIP_MOV_FILES", "true")
    monkeypatch.delenv("PRESERVED_MOV_NAMES", raising=False)

    def fail_probe(_path):
        raise AssertionError("aucun probe alpha ne doit être lancé pour la liste noire")

    monkeypatch.setattr(media_filters, "has_alpha_channel", fail_probe)

    # When / Then: le nom est préservé sans interrogé la couche alpha
    assert is_preserved_media(tmp_path / "m6+.mov") is True
    assert is_preserved_media(tmp_path / "M6+.MOV") is True


def test_is_preserved_media_indeterminate_alpha_is_preserved(monkeypatch, tmp_path):
    # Given: une détection alpha indéterminable
    monkeypatch.setenv("SKIP_MOV_FILES", "true")
    monkeypatch.setattr(media_filters, "has_alpha_channel", lambda _path: None)

    # When / Then: le fichier est préservé par précaution
    assert is_preserved_media(tmp_path / "unknown.mov") is True


def test_is_preserved_media_never_probes_other_extensions(monkeypatch, tmp_path):
    # Given: des fichiers hors .mov et un probe piégé
    monkeypatch.setenv("SKIP_MOV_FILES", "true")

    def fail_probe(_path):
        raise AssertionError("seuls les .mov portent la règle alpha")

    monkeypatch.setattr(media_filters, "has_alpha_channel", fail_probe)

    # When / Then: aucune autre extension n'est sondée
    assert is_preserved_media(tmp_path / "reel.mp4") is False
    assert is_preserved_media(tmp_path / "clip.MKV") is False
    assert is_preserved_media(tmp_path / "audio_audio.json") is False


def test_is_preserved_media_disabled_never_probes(monkeypatch, tmp_path):
    # Given: la préservation désactivée et un probe piégé
    monkeypatch.setenv("SKIP_MOV_FILES", "0")

    def fail_probe(_path):
        raise AssertionError("la préservation désactivée ne sonde aucun fichier")

    monkeypatch.setattr(media_filters, "has_alpha_channel", fail_probe)

    # When / Then: même un .mov alpha redevient traitable sans probe
    assert is_preserved_media(tmp_path / "logo.mov") is False


def test_split_preserved_media_mixed_batch(monkeypatch, tmp_path):
    # Given: un lot mixte avec un logo alpha et un .mov sans alpha
    monkeypatch.setenv("SKIP_MOV_FILES", "true")
    monkeypatch.setattr(
        media_filters, "has_alpha_channel",
        lambda path: Path(path).name == "logo.mov",
    )
    paths = [tmp_path / "a.mp4", tmp_path / "logo.mov", tmp_path / "reel.mov", tmp_path / "b.avi"]

    # When: séparation du lot
    to_process, preserved = split_preserved_media(paths)

    # Then: seul le logo alpha est isolé
    assert to_process == [tmp_path / "a.mp4", tmp_path / "reel.mov", tmp_path / "b.avi"]
    assert preserved == [tmp_path / "logo.mov"]


def test_split_preserved_media_keeps_everything_when_disabled(monkeypatch, tmp_path):
    # Given: la préservation désactivée
    monkeypatch.setenv("SKIP_MOV_FILES", "false")
    paths = [tmp_path / "a.mp4", tmp_path / "logo.mov"]

    # When: séparation du lot
    to_process, preserved = split_preserved_media(paths)

    # Then: aucun fichier n'est écarté
    assert to_process == [tmp_path / "a.mp4", tmp_path / "logo.mov"]
    assert preserved == []


def test_media_filters_constants():
    # Given: la règle métier porte sur les .mov préservés
    # When / Then: extension et variables d'environnement documentées
    assert media_filters.PRESERVED_EXTENSIONS == (".mov",)
    assert media_filters.SKIP_MOV_ENV_VAR == "SKIP_MOV_FILES"
    assert media_filters.PRESERVED_MOV_NAMES_ENV_VAR == "PRESERVED_MOV_NAMES"
