"""Fast unit tests for repository logic that needs no database.

DB-touching repository behavior (get_or_create, dedup queries, actual
persistence) lives in tests/integration/test_repositories.py, since it
requires a real session/database to be meaningful.
"""

from chess_insights.domain.enums import ChessPlatform, GameResult, GameSpeed, PlayerColor
from chess_insights.repositories.game import normalized_game_to_game
from chess_insights.repositories.player import canonicalize_username
from tests.conftest import make_normalized_game


def test_canonicalize_username_lowercases_and_trims() -> None:
    assert canonicalize_username("  Hikaru  ") == "hikaru"
    assert canonicalize_username("HIKARU") == "hikaru"
    assert canonicalize_username("hikaru") == "hikaru"


def test_normalized_game_to_game_maps_every_field() -> None:
    normalized = make_normalized_game(
        platform=ChessPlatform.CHESS_COM,
        external_game_id="abc123",
        player_color=PlayerColor.BLACK,
        opponent_username="opp",
        player_rating=1600,
        opponent_rating=1610,
        rating_change=None,
        result=GameResult.LOSS,
        opening_name="Sicilian Defense",
        opening_eco="B20",
        number_of_moves=42,
        duration_seconds=None,
        time_control="600",
        game_speed=GameSpeed.RAPID,
        rated=False,
        termination="resigned",
        pgn="1. e4 c5 1-0",
    )

    game = normalized_game_to_game(normalized, player_id=99)

    assert game.player_id == 99
    assert game.platform is ChessPlatform.CHESS_COM
    assert game.external_game_id == "abc123"
    assert game.played_at == normalized.played_at
    assert game.player_color is PlayerColor.BLACK
    assert game.opponent_username == "opp"
    assert game.player_rating == 1600
    assert game.opponent_rating == 1610
    assert game.rating_change is None
    assert game.result is GameResult.LOSS
    assert game.opening_name == "Sicilian Defense"
    assert game.opening_eco == "B20"
    assert game.number_of_moves == 42
    assert game.duration_seconds is None
    assert game.time_control == "600"
    assert game.game_speed is GameSpeed.RAPID
    assert game.rated is False
    assert game.termination == "resigned"
    assert game.pgn == "1. e4 c5 1-0"


def test_normalized_game_to_game_does_not_set_persistence_only_fields() -> None:
    game = normalized_game_to_game(make_normalized_game(), player_id=1)
    # created_at/updated_at/id are database-assigned, not set by the mapper.
    assert "id" not in game.__dict__
    assert "created_at" not in game.__dict__
    assert "updated_at" not in game.__dict__
