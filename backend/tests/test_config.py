import pytest


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import get_settings

    monkeypatch.setenv("DATABASE_URL", "x")
    monkeypatch.setenv("LLM_API_KEY", "super-secret-value")
    settings = get_settings()

    assert settings.embed_dim == 1536
    assert settings.llm_base_url == "https://api.gapgpt.app/v1"
    assert settings.llm_model_generate == "gpt-4.1"
    assert settings.llm_model_embed == "text-embedding-3-small"
    assert settings.llm_api_key.get_secret_value() == "super-secret-value"
    assert "super-secret-value" not in str(settings)
    assert "super-secret-value" not in repr(settings)


def test_settings_cors_from_json_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import get_settings

    monkeypatch.setenv("CORS_ORIGINS", '["https://a.example","https://b.example"]')
    assert get_settings().cors_origins == ["https://a.example", "https://b.example"]


def test_blank_hrcando_key_keeps_the_public_default(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import _HRCANDO_PUBLIC_CAREER_AUTH_KEY, get_settings

    monkeypatch.setenv("DATABASE_URL", "x")
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("HRCANDO_CAREER_AUTH_KEY", "")
    assert get_settings().hrcando_career_auth_key == _HRCANDO_PUBLIC_CAREER_AUTH_KEY
