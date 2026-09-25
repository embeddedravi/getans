"""Application configuration, loaded from environment variables / .env file."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ADPLATFORM_")

    # Database
    database_url: str = "mysql+aiomysql://root:password@localhost:3306/mydb"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 12

    # CORS - restrict this to your dashboard's origin(s) in production
    cors_origins: list[str] = ["http://localhost:5173"]

    # Socket.IO
    socketio_async_mode: str = "asgi"
    socketio_cors_allowed_origins: str = "*"  # publisher sites vary; tighten via api_key auth instead


settings = Settings()
