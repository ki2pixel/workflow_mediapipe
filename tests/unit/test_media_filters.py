# -*- coding: utf-8 -*-
from utils import media_filters
from utils.media_filters import (
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


def test_is_preserved_media_matches_mov_case_insensitive(monkeypatch, tmp_path):
    # Given: la préservation active et des fichiers aux extensions variées
    monkeypatch.setenv("SKIP_MOV_FILES", "true")

    # When / Then: les .mov sont préservés indépendamment de la casse
    assert is_preserved_media(tmp_path / "logo.mov") is True
    assert is_preserved_media(tmp_path / "logo.MOV") is True
    assert is_preserved_media(tmp_path / "reel.mp4") is False
    assert is_preserved_media(tmp_path / "audio_audio.json") is False


def test_is_preserved_media_disabled_keeps_mov_processable(monkeypatch, tmp_path):
    # Given: la préservation désactivée
    monkeypatch.setenv("SKIP_MOV_FILES", "0")

    # When / Then: un .mov redevient traitable par le pipeline
    assert is_preserved_media(tmp_path / "logo.mov") is False


def test_split_preserved_media_separates_logos(monkeypatch, tmp_path):
    # Given: un lot mixte de vidéos et logos
    monkeypatch.setenv("SKIP_MOV_FILES", "true")
    paths = [tmp_path / "a.mp4", tmp_path / "logo.mov", tmp_path / "b.avi"]

    # When: séparation du lot
    to_process, preserved = split_preserved_media(paths)

    # Then: les .mov sont isolés du traitement
    assert to_process == [tmp_path / "a.mp4", tmp_path / "b.avi"]
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
    # Given: la règle métier porte sur les logos .mov
    # When / Then: seule cette extension est préservée, pilotée par SKIP_MOV_FILES
    assert media_filters.PRESERVED_EXTENSIONS == (".mov",)
    assert media_filters.SKIP_MOV_ENV_VAR == "SKIP_MOV_FILES"
