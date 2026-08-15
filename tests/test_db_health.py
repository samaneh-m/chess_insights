"""Unit test for the database health-check failure path.

Uses a real engine pointed at a port nothing listens on, so the connection
is refused immediately -- this validates error handling without requiring
an actual running PostgreSQL server.
"""

from sqlalchemy.ext.asyncio import create_async_engine

from chess_insights.db.health import check_database_connection


async def test_check_database_connection_returns_false_when_unreachable() -> None:
    engine = create_async_engine(
        "postgresql+asyncpg://user:pass@127.0.0.1:1/nonexistent",
        pool_pre_ping=False,
    )
    try:
        result = await check_database_connection(engine)
    finally:
        await engine.dispose()

    assert result is False
