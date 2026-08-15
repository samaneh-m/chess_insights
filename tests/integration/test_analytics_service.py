"""Integration tests for PlayerAnalyticsService against a real PostgreSQL
database. See tests/integration/README.md.

No network calls -- this only exercises persistence + the analytics
service against known, hand-inserted Game rows.
"""

import uuid
from datetime import datetime, timezone

import pytest

from chess_insights.domain.enums import ChessPlatform, GameResult, GameSpeed, PlayerColor
from chess_insights.repositories.game import GameRepository
from chess_insights.repositories.player import PlayerRepository
from chess_insights.services.analytics import PlayerAnalyticsService, PlayerNotFoundError
from tests.conftest import make_normalized_game

pytestmark = pytest.mark.integration


def _unique_username() -> str:
    return f"itest-{uuid.uuid4().hex[:12]}"


async def _make_player_with_games(session_factory, normalized_games) -> int:
    async with session_factory() as session:
        players = PlayerRepository(session)
        games = GameRepository(session)
        player, _ = await players.get_or_create(ChessPlatform.LICHESS, _unique_username())
        await games.add_many(normalized_games, player_id=player.id)
        await session.commit()
        return player.id


async def test_report_matches_expected_overall_results(session_factory) -> None:
    normalized_games = [
        make_normalized_game(external_game_id="g1", result=GameResult.WIN),
        make_normalized_game(external_game_id="g2", result=GameResult.WIN),
        make_normalized_game(external_game_id="g3", result=GameResult.LOSS),
        make_normalized_game(external_game_id="g4", result=GameResult.DRAW),
    ]
    player_id = await _make_player_with_games(session_factory, normalized_games)

    async with session_factory() as session:
        report = await PlayerAnalyticsService(session).build_report(player_id)

    assert report.player_id == player_id
    assert report.overall.games == 4
    assert report.overall.wins == 2
    assert report.overall.losses == 1
    assert report.overall.draws == 1
    assert report.overall.win_rate == 50.0


async def test_report_matches_expected_opening_results(session_factory) -> None:
    normalized_games = [
        make_normalized_game(
            external_game_id="g1",
            opening_name="Italian Game",
            opening_eco="C50",
            result=GameResult.WIN,
        ),
        make_normalized_game(
            external_game_id="g2",
            opening_name="Italian Game",
            opening_eco="C50",
            result=GameResult.WIN,
        ),
        make_normalized_game(
            external_game_id="g3",
            opening_name="Italian Game",
            opening_eco="C50",
            result=GameResult.LOSS,
        ),
        make_normalized_game(
            external_game_id="g4", opening_name="Sicilian Defense", opening_eco="B20"
        ),
    ]
    player_id = await _make_player_with_games(session_factory, normalized_games)

    async with session_factory() as session:
        report = await PlayerAnalyticsService(session).build_report(
            player_id, minimum_opening_games=1
        )

    by_name = {o.opening_name: o for o in report.openings.openings}
    assert by_name["Italian Game"].stats.games == 3
    assert by_name["Italian Game"].stats.wins == 2
    assert by_name["Sicilian Defense"].stats.games == 1
    # Sicilian Defense (1 game, 100% win rate) ranks above Italian Game (3
    # games, 66.67%) since win rate is the primary ranking key.
    assert report.openings.top_openings[0].opening_name == "Sicilian Defense"
    assert report.openings.top_openings[1].opening_name == "Italian Game"


async def test_report_matches_expected_rating_results(session_factory) -> None:
    normalized_games = [
        make_normalized_game(
            external_game_id="g1",
            player_rating=1500,
            played_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ),
        make_normalized_game(
            external_game_id="g2",
            player_rating=1550,
            played_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        ),
        make_normalized_game(
            external_game_id="g3",
            player_rating=1480,
            played_at=datetime(2024, 1, 3, tzinfo=timezone.utc),
        ),
    ]
    player_id = await _make_player_with_games(session_factory, normalized_games)

    async with session_factory() as session:
        report = await PlayerAnalyticsService(session).build_report(player_id)

    assert [p.rating for p in report.rating.data_points] == [1500, 1550, 1480]
    assert report.rating.earliest_rating == 1500
    assert report.rating.latest_rating == 1480
    assert report.rating.highest_rating == 1550
    assert report.rating.lowest_rating == 1480
    assert report.rating.rating_change == -20


async def test_report_for_player_with_zero_games(session_factory) -> None:
    player_id = await _make_player_with_games(session_factory, [])

    async with session_factory() as session:
        report = await PlayerAnalyticsService(session).build_report(player_id)

    assert report.overall.games == 0
    assert report.overall.win_rate == 0.0
    assert report.rating.data_points == ()


async def test_missing_player_raises_against_real_database(session_factory) -> None:
    async with session_factory() as session:
        with pytest.raises(PlayerNotFoundError):
            await PlayerAnalyticsService(session).build_report(-1)


async def test_report_uses_only_the_targeted_players_games(session_factory) -> None:
    player_a_games = [make_normalized_game(external_game_id="shared-id", result=GameResult.WIN)]
    player_b_games = [make_normalized_game(external_game_id="shared-id", result=GameResult.LOSS)]

    player_a_id = await _make_player_with_games(session_factory, player_a_games)
    player_b_id = await _make_player_with_games(session_factory, player_b_games)

    async with session_factory() as session:
        report_a = await PlayerAnalyticsService(session).build_report(player_a_id)
        report_b = await PlayerAnalyticsService(session).build_report(player_b_id)

    assert report_a.overall.wins == 1
    assert report_a.overall.losses == 0
    assert report_b.overall.wins == 0
    assert report_b.overall.losses == 1


async def test_color_and_speed_breakdowns_against_real_data(session_factory) -> None:
    normalized_games = [
        make_normalized_game(
            external_game_id="g1",
            player_color=PlayerColor.WHITE,
            game_speed=GameSpeed.BULLET,
            result=GameResult.WIN,
        ),
        make_normalized_game(
            external_game_id="g2",
            player_color=PlayerColor.BLACK,
            game_speed=GameSpeed.RAPID,
            result=GameResult.LOSS,
        ),
    ]
    player_id = await _make_player_with_games(session_factory, normalized_games)

    async with session_factory() as session:
        report = await PlayerAnalyticsService(session).build_report(player_id)

    assert report.by_color.white.games == 1
    assert report.by_color.white.wins == 1
    assert report.by_color.black.games == 1
    assert report.by_color.black.losses == 1
    assert report.by_speed.by_speed[GameSpeed.BULLET].games == 1
    assert report.by_speed.by_speed[GameSpeed.RAPID].games == 1
