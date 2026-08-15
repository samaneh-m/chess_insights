"""Shared pytest fixtures."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chess_insights.api.app import create_app

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def client():
    """A TestClient for a freshly created app, with lifespan events run."""
    with TestClient(create_app()) as test_client:
        yield test_client


def load_fixture(*parts: str) -> str:
    """Read a fixture file's raw text, e.g. load_fixture('lichess', 'draw.json')."""
    return (FIXTURES_DIR.joinpath(*parts)).read_text(encoding="utf-8")


def load_json_fixture(*parts: str) -> dict:
    """Read and parse a fixture file as a single JSON object."""
    return json.loads(load_fixture(*parts))
