"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Chess Insights application.

    Values are read from environment variables (or a local ``.env`` file)
    and fall back to sensible development defaults.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Chess Insights"
    app_env: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""
    return Settings()
