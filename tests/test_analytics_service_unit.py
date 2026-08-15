"""Fast unit tests for PlayerAnalyticsService using a fake session -- no
real database needed. Full behavior against real Postgres lives in
tests/integration/test_analytics_service.py.
"""

from datetime import datetime, timezone

import pytest

from chess_insights.analytics.models import AnalyticsReport, GameLengthBucket
from chess_insights.db.models.game import Game
from chess_insights.db.models.player import Player
from chess_insights.domain.enums import ChessPlatform, GameResult, GameSpeed, PlayerColor
from chess_insights.services.analytics import PlayerAnalyticsService, PlayerNotFoundError


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _FakeSession:
    """Satisfies only what PlayerAnalyticsService actually calls: get() and
    execute() -- no real SQLAlchemy engine/database involved."""

    def __init__(self, player=None, games=()):
        self._player = player
        self._games = list(games)

    async def get(self, model, pk):
        return self._player

    async def execute(self, stmt):
        return _FakeResult(self._games)


def _make_player(player_id: int = 1) -> Player:
    player = Player(platform=ChessPlatform.LICHESS, username="tester")
    player.id = player_id
    return player


def _make_game(**overrides) -> Game:
    defaults = {
        "player_id": 1,
        "platform": ChessPlatform.LICHESS,
        "external_game_id": "g1",
        "played_at": datetime(2024, 1, 1, 12, tzinfo=timezone.utc),
        "player_color": PlayerColor.WHITE,
        "opponent_username": "opp",
        "player_rating": 1500,
        "opponent_rating": 1490,
        "rating_change": 8,
        "result": GameResult.WIN,
        "opening_name": "Italian Game",
        "opening_eco": "C50",
        "number_of_moves": 30,
        "duration_seconds": 300,
        "time_control": "300+3",
        "game_speed": GameSpeed.BLITZ,
        "rated": True,
        "termination": "mate",
        "pgn": "1. e4 e5 1-0",
    }
    defaults.update(overrides)
    return Game(**defaults)


async def test_valid_player_report() -> None:
    session = _FakeSession(player=_make_player(1), games=[_make_game()])
    report = await PlayerAnalyticsService(session).build_report(1)
    assert report.player_id == 1
    assert report.overall.games == 1
    assert report.overall.wins == 1


async def test_player_with_zero_games_produces_an_empty_report() -> None:
    session = _FakeSession(player=_make_player(1), games=[])
    report = await PlayerAnalyticsService(session).build_report(1)
    assert report.overall.games == 0
    assert report.overall.win_rate == 0.0
    assert report.openings.openings == ()
    assert report.rating.data_points == ()


async def test_missing_player_raises_player_not_found_error() -> None:
    session = _FakeSession(player=None, games=[])
    with pytest.raises(PlayerNotFoundError):
        await PlayerAnalyticsService(session).build_report(999)


async def test_games_are_transformed_correctly_into_analytics_input() -> None:
    game = _make_game(
        player_color=PlayerColor.BLACK,
        result=GameResult.LOSS,
        opening_name="Sicilian Defense",
        opening_eco="B20",
        number_of_moves=55,
        game_speed=GameSpeed.RAPID,
    )
    session = _FakeSession(player=_make_player(1), games=[game])
    report = await PlayerAnalyticsService(session).build_report(1)

    assert report.by_color.black.games == 1
    assert report.by_color.black.losses == 1
    assert report.by_color.white.games == 0
    assert report.openings.openings[0].opening_name == "Sicilian Defense"
    assert report.openings.openings[0].opening_eco == "B20"
    assert report.by_game_length.by_bucket[GameLengthBucket.MEDIUM].games == 1
    assert report.by_speed.by_speed[GameSpeed.RAPID].games == 1


async def test_service_returns_an_analytics_report_instance() -> None:
    session = _FakeSession(player=_make_player(1), games=[])
    report = await PlayerAnalyticsService(session).build_report(1)
    assert isinstance(report, AnalyticsReport)


async def test_minimum_opening_games_is_forwarded_to_openings_analysis() -> None:
    session = _FakeSession(player=_make_player(1), games=[_make_game(opening_name="Once")])
    report = await PlayerAnalyticsService(session).build_report(1, minimum_opening_games=1)
    assert len(report.openings.top_openings) == 1
    assert report.openings.minimum_opening_games == 1


async def test_timezone_is_forwarded_to_time_of_day_analysis() -> None:
    session = _FakeSession(player=_make_player(1), games=[_make_game()])
    report = await PlayerAnalyticsService(session).build_report(1, timezone_name="Europe/Berlin")
    assert report.by_time_of_day.timezone_name == "Europe/Berlin"
