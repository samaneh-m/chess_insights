"""Tests for database-related settings assembly."""

from chess_insights.core.config import Settings


def test_database_url_assembled_from_parts() -> None:
    settings = Settings(
        postgres_user="alice",
        postgres_password="secret",
        postgres_host="db",
        postgres_port=5433,
        postgres_db="chessdb",
        database_url="",
    )
    assert settings.sqlalchemy_database_url == "postgresql+asyncpg://alice:secret@db:5433/chessdb"


def test_explicit_database_url_takes_precedence() -> None:
    explicit_url = "postgresql+asyncpg://override:pw@otherhost:5432/otherdb"
    settings = Settings(database_url=explicit_url)
    assert settings.sqlalchemy_database_url == explicit_url


def test_default_settings_point_at_localhost() -> None:
    settings = Settings(database_url="")
    assert (
        settings.sqlalchemy_database_url
        == "postgresql+asyncpg://chess:chess@localhost:5432/chess_insights"
    )
