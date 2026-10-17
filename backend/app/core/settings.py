"""Typed application settings (ENVIRONMENT.md). The only place that reads the environment."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from cryptography.fernet import Fernet
from pydantic import AliasChoices, Field, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
PLACEHOLDER_PREFIX = "change-me"

REQUIRED_SECRETS = (
    "jwt_secret",
    "service_api_key",
    "pii_encryption_key",
    "hmac_key",
)


class SettingsError(RuntimeError):
    """Configuration is missing or unsafe. The app refuses to start (fail closed)."""


def _env(name: str) -> AliasChoices:
    return AliasChoices(name)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
        populate_by_name=True,
    )

    # App
    env: Literal["development", "test", "production"] = Field(
        "development", validation_alias=_env("THUNAI_ENV")
    )
    demo_mode: bool = Field(False, validation_alias=_env("THUNAI_DEMO_MODE"))
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        "INFO", validation_alias=_env("THUNAI_LOG_LEVEL")
    )
    public_web_url: str = Field(
        "http://localhost:5173", validation_alias=_env("THUNAI_PUBLIC_WEB_URL")
    )
    cors_origins: str = Field("http://localhost:5173", validation_alias=_env("THUNAI_CORS_ORIGINS"))

    # Database
    database_url: str = Field(validation_alias=_env("DATABASE_URL"))
    test_database_url: str | None = Field(None, validation_alias=_env("TEST_DATABASE_URL"))

    # Security
    jwt_secret: str = Field("", validation_alias=_env("THUNAI_JWT_SECRET"))
    jwt_ttl_minutes: int = Field(60, ge=1, le=1440, validation_alias=_env("THUNAI_JWT_TTL_MINUTES"))
    service_api_key: str = Field("", validation_alias=_env("THUNAI_SERVICE_API_KEY"))
    pii_encryption_key: str = Field("", validation_alias=_env("THUNAI_PII_ENCRYPTION_KEY"))
    hmac_key: str = Field("", validation_alias=_env("THUNAI_HMAC_KEY"))
    seed_password: str | None = Field(None, validation_alias=_env("THUNAI_SEED_PASSWORD"))
    contact_token_ttl_minutes: int = Field(
        30, ge=1, le=1440, validation_alias=_env("THUNAI_CONTACT_TOKEN_TTL_MINUTES")
    )

    # Risk engine
    scoring_config_path: str = Field(
        "config/scoring_v1.yaml", validation_alias=_env("THUNAI_SCORING_CONFIG_PATH")
    )
    cooling_off_minutes: int = Field(
        240, ge=1, le=10080, validation_alias=_env("THUNAI_COOLING_OFF_MINUTES")
    )
    trusted_contact_activation_hours: int = Field(
        72, ge=0, le=720, validation_alias=_env("THUNAI_TRUSTED_CONTACT_ACTIVATION_HOURS")
    )
    fri_timeout_ms: int = Field(300, ge=1, le=10000, validation_alias=_env("THUNAI_FRI_TIMEOUT_MS"))

    # Notifications
    notifier: Literal["console", "twilio", "telegram"] = Field(
        "console", validation_alias=_env("THUNAI_NOTIFIER")
    )
    twilio_account_sid: str | None = Field(None, validation_alias=_env("TWILIO_ACCOUNT_SID"))
    twilio_auth_token: str | None = Field(None, validation_alias=_env("TWILIO_AUTH_TOKEN"))
    twilio_from_number: str | None = Field(None, validation_alias=_env("TWILIO_FROM_NUMBER"))
    telegram_bot_token: str | None = Field(None, validation_alias=_env("TELEGRAM_BOT_TOKEN"))
    demo_contact_phone_e164: str | None = Field(
        None, validation_alias=_env("THUNAI_DEMO_CONTACT_PHONE_E164")
    )
    demo_contact_telegram_chat_id: str | None = Field(
        None, validation_alias=_env("THUNAI_DEMO_CONTACT_TELEGRAM_CHAT_ID")
    )

    # LLM (FR-21)
    llm_enabled: bool = Field(False, validation_alias=_env("THUNAI_LLM_ENABLED"))
    anthropic_api_key: str | None = Field(None, validation_alias=_env("ANTHROPIC_API_KEY"))
    llm_model: str = Field("claude-opus-5-5", validation_alias=_env("THUNAI_LLM_MODEL"))
    llm_timeout_seconds: float = Field(
        10, gt=0, le=120, validation_alias=_env("THUNAI_LLM_TIMEOUT_SECONDS")
    )

    # Simulator
    api_base_url: str = Field(
        "http://localhost:8000/api/v1", validation_alias=_env("THUNAI_API_BASE_URL")
    )
    sim_default_speed: float = Field(4320, gt=0, validation_alias=_env("THUNAI_SIM_DEFAULT_SPEED"))

    @field_validator(
        "twilio_account_sid",
        "twilio_auth_token",
        "twilio_from_number",
        "telegram_bot_token",
        "demo_contact_phone_e164",
        "demo_contact_telegram_chat_id",
        "anthropic_api_key",
        "seed_password",
        "test_database_url",
        mode="before",
    )
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        return None if value == "" else value

    @model_validator(mode="after")
    def _check_safety(self) -> "Settings":
        missing = [f"THUNAI_{name.upper()}" for name in REQUIRED_SECRETS if not getattr(self, name)]
        if missing:
            raise ValueError(f"required secret(s) missing: {', '.join(missing)}")
        if len(self.jwt_secret.encode()) < 32:
            raise ValueError("THUNAI_JWT_SECRET must be at least 32 bytes")
        if self.env == "production":
            placeholders = [
                f"THUNAI_{name.upper()}"
                for name in REQUIRED_SECRETS
                if getattr(self, name).startswith(PLACEHOLDER_PREFIX)
            ]
            if placeholders:
                raise ValueError(f"placeholder secret(s) in production: {', '.join(placeholders)}")
            if self.demo_mode:
                raise ValueError("THUNAI_DEMO_MODE=true is refused when THUNAI_ENV=production")
            if "*" in self.cors_origins:
                raise ValueError("THUNAI_CORS_ORIGINS must not contain wildcards in production")
        if not self.pii_encryption_key.startswith(PLACEHOLDER_PREFIX):
            try:
                Fernet(self.pii_encryption_key.encode())
            except ValueError as exc:
                raise ValueError("THUNAI_PII_ENCRYPTION_KEY is not a valid Fernet key") from exc
        if self.llm_enabled and not self.anthropic_api_key:
            raise ValueError("THUNAI_LLM_ENABLED=true needs ANTHROPIC_API_KEY")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def scoring_config_file(self) -> Path:
        path = Path(self.scoring_config_path)
        return path if path.is_absolute() else BACKEND_DIR / path

    @property
    def rate_limits_enabled(self) -> bool:
        return self.env != "test"


def load_settings(**overrides: object) -> Settings:
    """Build settings, turning validation errors into one clear startup message."""
    try:
        return Settings(**overrides)  # type: ignore[arg-type]
    except ValidationError as exc:
        problems = "; ".join(_describe(err) for err in exc.errors())
        raise SettingsError(f"Invalid configuration: {problems}") from None


def _describe(err: object) -> str:
    if not isinstance(err, dict):
        return str(err)
    loc = ".".join(str(p) for p in err.get("loc", ()))
    msg = str(err.get("msg", "invalid"))
    if err.get("type") == "missing":
        return f"{loc} is required"
    return f"{loc}: {msg}" if loc else msg


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
