"""Application configuration, loaded from environment variables, a .env file,
or mounted secret files (Docker/Kubernetes secrets).

Secrets have NO defaults. The app refuses to start if a required secret is
missing, still a placeholder, or too weak, so a misconfigured deploy fails
loudly instead of running with a well-known key.

Sources, highest priority first:
    1. Environment variables          ADPLATFORM_JWT_SECRET=...
    2. .env file (local dev only)
    3. Secret files in /run/secrets   /run/secrets/adplatform_jwt_secret
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

_SECRETS_DIR = "/run/secrets" if Path("/run/secrets").is_dir() else None

_MIN_JWT_SECRET_LEN = 32
_WEAK_VALUES = {
    "password", "adplatform", "postgres", "root", "admin",
    "secret", "changeme", "change-me", "change-me-in-production",
}
_GENERATE_HINT = 'python -c "import secrets; print(secrets.token_urlsafe(48))"'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="ADPLATFORM_",
        secrets_dir=_SECRETS_DIR,
        extra="ignore",
        # Keep rejected secret values out of validation error output/logs.
        hide_input_in_errors=True,
    )

    # "production" is the default on purpose: local dev must opt in to the
    # relaxed checks with ADPLATFORM_ENVIRONMENT=development.
    environment: Literal["development", "test", "production"] = "production"

    # --- Secrets: required, no defaults -----------------------------------
    database_url: SecretStr
    jwt_secret: SecretStr

    # --- Auth ---------------------------------------------------------------
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 12

    # --- CORS - restrict to your dashboard's origin(s) ---------------------
    cors_origins: list[str] = ["http://localhost:5173"]

    # --- Socket.IO -----------------------------------------------------------
    socketio_async_mode: str = "asgi"
    socketio_cors_allowed_origins: str = "*"  # publisher sites vary; auth is via api_key

    # --- OTP / SMS -------------------------------------------------------------
    otp_length: int = 6
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60
    otp_max_per_hour: int = 5
    sms_backend: str = "console"  # dev only; logs the OTP
    require_verified_mobile: bool = False
    allow_self_signup: bool = True

    @field_validator("jwt_secret")
    @classmethod
    def _strong_jwt_secret(cls, v: SecretStr) -> SecretStr:
        s = v.get_secret_value()
        if (
            len(s) < _MIN_JWT_SECRET_LEN
            or s.lower() in _WEAK_VALUES
            or "change-me" in s.lower()
        ):
            raise ValueError(
                f"must be at least {_MIN_JWT_SECRET_LEN} random characters and not a "
                f"placeholder. Generate one with: {_GENERATE_HINT}"
            )
        return v

    @model_validator(mode="after")
    def _production_guards(self) -> "Settings":
        if self.environment != "production":
            return self

        problems: list[str] = []

        if self.sms_backend == "console":
            problems.append("sms_backend='console' logs OTP codes; configure a real SMS backend")
        if "*" in self.cors_origins:
            problems.append("cors_origins must list explicit origins, not '*'")

        password = make_url(self.database_url.get_secret_value()).password
        if not password or password.lower() in _WEAK_VALUES:
            problems.append("database_url must contain a strong, non-default password")

        if problems:
            raise ValueError("unsafe production configuration: " + "; ".join(problems))
        return self


settings = Settings()