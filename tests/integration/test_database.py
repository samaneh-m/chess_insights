"""Integration tests against a real PostgreSQL database.

Requires a reachable database (e.g. `docker compose up -d db`) and is
excluded from the default test run. See tests/integration/README.md.
"""

import pytest

from chess_insights.core.config import get_settings
from chess_insights.db.health import check_database_connection
from chess_insights.db.session import get_engine

pytestmark = pytest.mark.integration


async def test_database_health_check_succeeds_against_real_postgres() -> None:
    get_settings.cache_clear()
    get_engine.cache_clear()
    assert await check_database_connection(get_engine()) is True


async def test_health_endpoint_reports_database_ok(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
