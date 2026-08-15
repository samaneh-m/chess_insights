"""Tests for the /health endpoint's database connectivity reporting.

Database connectivity is mocked here so these tests run without a live
PostgreSQL instance. See tests/integration for tests against a real database.
"""

from unittest.mock import AsyncMock

import chess_insights.api.app as app_module


def test_health_ok_when_database_reachable(client, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "check_database_connection", AsyncMock(return_value=True))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_degraded_when_database_unreachable(client, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "check_database_connection", AsyncMock(return_value=False))

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}
