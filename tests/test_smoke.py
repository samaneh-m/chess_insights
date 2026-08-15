"""Smoke tests: package import, versioning, and the FastAPI app.

The FastAPI app must be importable/creatable without a running database
(engine creation is lazy), so these tests never require PostgreSQL.
"""

import chess_insights
from chess_insights.api.app import create_app


def test_package_imports() -> None:
    assert chess_insights is not None


def test_package_has_version() -> None:
    assert chess_insights.__version__ == "0.1.0"


def test_create_app_returns_fastapi_app_without_touching_database() -> None:
    app = create_app()
    assert app.title == "Chess Insights"


def test_root_endpoint(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Chess Insights"
    assert body["status"] == "running"
