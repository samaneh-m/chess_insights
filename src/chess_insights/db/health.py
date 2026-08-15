"""Database connectivity health check.

Executes a trivial query that does not depend on any application table
existing, so it works before any domain schema/migration has been applied.
"""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def check_database_connection(engine: AsyncEngine) -> bool:
    """Return ``True`` if a trivial query succeeds against the database."""
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database health check failed")
        return False
    return True
