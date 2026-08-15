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

    postgres_db: str = "chess_insights"
    postgres_user: str = "chess"
    postgres_password: str = "chess"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str = ""

    @property
    def sqlalchemy_database_url(self) -> str:
        """The effective database URL.

        Uses ``DATABASE_URL`` when set (e.g. Docker Compose overrides it to
        point at the ``db`` service); otherwise assembles it from the
        individual ``POSTGRES_*`` fields, which is convenient for local
        host-based development.
        """
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance."""
    return Settings()
