"""Shared pytest fixtures."""

import pytest
from fastapi.testclient import TestClient

from chess_insights.api.app import create_app


@pytest.fixture
def client():
    """A TestClient for a freshly created app, with lifespan events run."""
    with TestClient(create_app()) as test_client:
        yield test_client
