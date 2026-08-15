"""Shared pytest fixtures."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chess_insights.api.app import create_app
from chess_insights.domain.enums import ChessPlatform, GameResult, GameSpeed, PlayerColor
from chess_insights.schemas.game import NormalizedGame

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


def make_normalized_game(
    *,
    platform: ChessPlatform = ChessPlatform.LICHESS,
    external_game_id: str = "game-1",
    played_at: datetime | None = None,
    player_color: PlayerColor | None = PlayerColor.WHITE,
    opponent_username: str | None = "opponent",
    player_rating: int | None = 1500,
    opponent_rating: int | None = 1490,
    rating_change: int | None = 8,
    result: GameResult = GameResult.WIN,
    opening_name: str | None = "Italian Game",
    opening_eco: str | None = "C50",
    number_of_moves: int | None = 10,
    duration_seconds: int | None = 300,
    time_control: str | None = "300+3",
    game_speed: GameSpeed = GameSpeed.BLITZ,
    rated: bool | None = True,
    termination: str | None = "mate",
    pgn: str | None = "1. e4 e5 1-0",
) -> NormalizedGame:
    """Build a NormalizedGame with sane defaults, overriding only what a
    test cares about."""
    return NormalizedGame(
        platform=platform,
        external_game_id=external_game_id,
        played_at=played_at or datetime(2024, 1, 1, tzinfo=timezone.utc),
        player_color=player_color,
        opponent_username=opponent_username,
        player_rating=player_rating,
        opponent_rating=opponent_rating,
        rating_change=rating_change,
        result=result,
        opening_name=opening_name,
        opening_eco=opening_eco,
        number_of_moves=number_of_moves,
        duration_seconds=duration_seconds,
        time_control=time_control,
        game_speed=game_speed,
        rated=rated,
        termination=termination,
        pgn=pgn,
    )
