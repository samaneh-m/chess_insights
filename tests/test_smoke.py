"""Phase 1 smoke tests: package import, versioning, and the FastAPI app."""

from fastapi.testclient import TestClient

import chess_insights
from chess_insights.api.app import create_app


def test_package_imports() -> None:
    assert chess_insights is not None


def test_package_has_version() -> None:
    assert chess_insights.__version__ == "0.1.0"


def test_create_app_returns_fastapi_app() -> None:
    app = create_app()
    assert app.title == "Chess Insights"


def test_health_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Chess Insights"
    assert body["status"] == "running"
