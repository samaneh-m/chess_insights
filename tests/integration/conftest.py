"""Shared fixtures for integration tests (require a real PostgreSQL)."""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from chess_insights.db.session import get_engine


@pytest.fixture
def session_factory():
    return async_sessionmaker(get_engine(), expire_on_commit=False)
