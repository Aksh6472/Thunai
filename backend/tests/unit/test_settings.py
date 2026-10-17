"""T-005: settings validation (TESTING.md §2)."""

import pytest
from cryptography.fernet import Fernet

from app.core.settings import SettingsError, load_settings

VALID = {
    "THUNAI_ENV": "development",
    "THUNAI_DEMO_MODE": "true",
    "DATABASE_URL": "postgresql+psycopg://u:p@localhost:5432/db",
    "THUNAI_JWT_SECRET": "x" * 64,
    "THUNAI_SERVICE_API_KEY": "s" * 48,
    "THUNAI_PII_ENCRYPTION_KEY": Fernet.generate_key().decode(),
    "THUNAI_HMAC_KEY": "h" * 64,
}


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Isolate from the developer's .env and shell."""
    monkeypatch.setitem(load_settings.__globals__["Settings"].model_config, "env_file", None)
    for key in list(VALID) + ["THUNAI_LLM_ENABLED", "THUNAI_CORS_ORIGINS"]:
        monkeypatch.delenv(key, raising=False)
    for key, value in VALID.items():
        monkeypatch.setenv(key, value)
    return monkeypatch


def test_valid_settings_load(env: pytest.MonkeyPatch) -> None:
    settings = load_settings()
    assert settings.env == "development"
    assert settings.demo_mode is True
    assert settings.cooling_off_minutes == 240
    assert settings.cors_origin_list == ["http://localhost:5173"]


def test_missing_jwt_secret_fails_with_clear_message(env: pytest.MonkeyPatch) -> None:
    env.delenv("THUNAI_JWT_SECRET")
    with pytest.raises(SettingsError, match="THUNAI_JWT_SECRET"):
        load_settings()


def test_short_jwt_secret_fails(env: pytest.MonkeyPatch) -> None:
    env.setenv("THUNAI_JWT_SECRET", "short")
    with pytest.raises(SettingsError, match="at least 32 bytes"):
        load_settings()


def test_missing_database_url_fails(env: pytest.MonkeyPatch) -> None:
    env.delenv("DATABASE_URL")
    with pytest.raises(SettingsError, match="DATABASE_URL is required"):
        load_settings()


def test_placeholder_secret_refused_in_production(env: pytest.MonkeyPatch) -> None:
    env.setenv("THUNAI_ENV", "production")
    env.setenv("THUNAI_DEMO_MODE", "false")
    env.setenv("THUNAI_HMAC_KEY", "change-me-openssl-rand-hex-32")
    with pytest.raises(SettingsError, match="placeholder"):
        load_settings()


def test_placeholder_secret_allowed_in_development(env: pytest.MonkeyPatch) -> None:
    env.setenv("THUNAI_HMAC_KEY", "change-me-openssl-rand-hex-32")
    assert load_settings().hmac_key.startswith("change-me")


def test_demo_mode_refused_in_production(env: pytest.MonkeyPatch) -> None:
    env.setenv("THUNAI_ENV", "production")
    with pytest.raises(SettingsError, match="DEMO_MODE"):
        load_settings()


def test_invalid_fernet_key_fails(env: pytest.MonkeyPatch) -> None:
    env.setenv("THUNAI_PII_ENCRYPTION_KEY", "not-a-fernet-key")
    with pytest.raises(SettingsError, match="Fernet"):
        load_settings()


def test_llm_enabled_needs_api_key(env: pytest.MonkeyPatch) -> None:
    env.setenv("THUNAI_LLM_ENABLED", "true")
    with pytest.raises(SettingsError, match="ANTHROPIC_API_KEY"):
        load_settings()


def test_rate_limits_disabled_only_in_test_env(env: pytest.MonkeyPatch) -> None:
    assert load_settings().rate_limits_enabled is True
    env.setenv("THUNAI_ENV", "test")
    assert load_settings().rate_limits_enabled is False
