"""Async SQLAlchemy engine and session management.

Engine/session construction is lazy: importing this module (or the package)
never opens a network connection. Connections are only attempted when a
session is actually used (e.g. during a request or a health check).
"""

from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from chess_insights.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    """Return the application's async SQLAlchemy engine (created once, cached)."""
    settings = get_settings()
    return create_async_engine(settings.sqlalchemy_database_url)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the application's async session factory (created once, cached)."""
    return async_sessionmaker(bind=get_engine(), expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a request-scoped ``AsyncSession``."""
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        yield session


async def dispose_engine() -> None:
    """Dispose of the engine's connection pool (call on application shutdown)."""
    if get_engine.cache_info().currsize:
        await get_engine().dispose()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
