import os

import config


def test_settings_defaults(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("CHROMA_PATH", "/tmp/chroma-test")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "12")
    config.reset_settings_cache()
    settings = config.get_settings()
    assert settings.chroma_path == "/tmp/chroma-test"
    assert settings.rate_limit_per_minute == 12
    assert settings.groq_configured is False


def test_groq_configured_rejects_placeholder(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "your_key_here")
    config.reset_settings_cache()
    assert config.get_settings().groq_configured is False
