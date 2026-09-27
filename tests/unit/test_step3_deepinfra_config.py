"""Unit tests for STEP4 DeepInfra configuration resolution logic."""

from config.settings import DEEPINFRA_OFFICIAL_TRANSCRIPTIONS_URL, config


def test_resolve_deepinfra_transcriptions_url_rejects_wisper_typo(monkeypatch):
    monkeypatch.setattr(
        config,
        "DEEPINFRA_TRANSCRIPTIONS_URL",
        "https://api.deepinfra.com/v1/openai/audio/wisper",
        raising=False,
    )
    resolved = config.resolve_deepinfra_transcriptions_url()
    assert resolved == DEEPINFRA_OFFICIAL_TRANSCRIPTIONS_URL


def test_resolve_deepinfra_transcriptions_url_builds_absolute_url(monkeypatch):
    monkeypatch.setattr(config, "DEEPINFRA_TRANSCRIPTIONS_URL", "", raising=False)
    monkeypatch.setattr(config, "DEEPINFRA_BASE_URL", "https://api.deepinfra.com", raising=False)
    monkeypatch.setattr(config, "DEEPINFRA_TRANSCRIPTIONS_ENDPOINT", "/v1/openai/audio/transcriptions", raising=False)

    resolved = config.resolve_deepinfra_transcriptions_url()
    assert resolved == "https://api.deepinfra.com/v1/openai/audio/transcriptions"
