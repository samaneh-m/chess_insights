"""Tests for the pure Lichess record -> NormalizedGame normalizer.

No network access -- all inputs are fixture dicts under
tests/fixtures/lichess/.
"""

from datetime import timezone

import pytest

from chess_insights.domain.enums import ChessPlatform, GameResult, GameSpeed, PlayerColor
from chess_insights.integrations.lichess.exceptions import LichessDataError
from chess_insights.integrations.lichess.normalizer import normalize_game
from tests.conftest import load_json_fixture

TRACKED_USERNAME = "TrackedUser"


def _normalize(fixture_name: str):
    record = load_json_fixture("lichess", fixture_name)
    return normalize_game(record, tracked_username=TRACKED_USERNAME)


def test_white_tracked_player_win() -> None:
    game = _normalize("white_win.json")
    assert game.player_color is PlayerColor.WHITE
    assert game.result is GameResult.WIN


def test_white_tracked_player_loss() -> None:
    game = _normalize("white_loss.json")
    assert game.player_color is PlayerColor.WHITE
    assert game.result is GameResult.LOSS


def test_black_tracked_player_win() -> None:
    game = _normalize("black_win.json")
    assert game.player_color is PlayerColor.BLACK
    assert game.result is GameResult.WIN


def test_black_tracked_player_loss() -> None:
    game = _normalize("black_loss.json")
    assert game.player_color is PlayerColor.BLACK
    assert game.result is GameResult.LOSS


def test_draw_result() -> None:
    game = _normalize("draw.json")
    assert game.result is GameResult.DRAW


def test_ratings_extracted_correctly() -> None:
    game = _normalize("white_win.json")
    assert game.player_rating == 1500
    assert game.opponent_rating == 1490
    assert game.rating_change == 8


def test_missing_opponent_rating_is_none_not_zero() -> None:
    game = _normalize("missing_rating.json")
    assert game.player_rating == 1500
    assert game.opponent_rating is None
    assert game.opponent_username is None


def test_opening_metadata_extracted() -> None:
    game = _normalize("white_win.json")
    assert game.opening_name == "Scandinavian Defense"
    assert game.opening_eco == "B01"


def test_missing_opening_is_none() -> None:
    game = _normalize("missing_opening.json")
    assert game.opening_name is None
    assert game.opening_eco is None


def test_played_at_is_utc_aware() -> None:
    game = _normalize("white_win.json")
    assert game.played_at.tzinfo is not None
    assert game.played_at.utcoffset().total_seconds() == 0
    assert game.played_at.astimezone(timezone.utc) == game.played_at


def test_duration_seconds_derived_from_timestamps() -> None:
    game = _normalize("white_win.json")
    # createdAt=1700000000000, lastMoveAt=1700000300000 -> 300s
    assert game.duration_seconds == 300


def test_speed_mapping_known_value() -> None:
    game = _normalize("white_win.json")
    assert game.game_speed is GameSpeed.BLITZ


def test_unknown_speed_maps_to_unknown_enum_value() -> None:
    game = _normalize("unknown_speed.json")
    assert game.game_speed is GameSpeed.UNKNOWN


def test_move_count_is_ply_count() -> None:
    game = _normalize("white_win.json")
    # "e4 d5 exd5 Qxd5 Nc3 Qa5 d4 Nf6 Nf3 c6" -> 10 space-separated tokens (plies)
    assert game.number_of_moves == 10


def test_external_game_id_extracted() -> None:
    game = _normalize("white_win.json")
    assert game.external_game_id == "aaaa1111"
    assert game.platform is ChessPlatform.LICHESS


def test_aborted_game_is_skipped() -> None:
    assert _normalize("aborted.json") is None


def test_malformed_record_missing_id_raises() -> None:
    record = load_json_fixture("lichess", "malformed_missing_id.json")
    with pytest.raises(LichessDataError):
        normalize_game(record, tracked_username=TRACKED_USERNAME)


def test_record_without_tracked_player_raises() -> None:
    record = load_json_fixture("lichess", "white_win.json")
    with pytest.raises(LichessDataError):
        normalize_game(record, tracked_username="SomeoneElseEntirely")


def test_username_matching_is_case_insensitive() -> None:
    record = load_json_fixture("lichess", "white_win.json")
    game = normalize_game(record, tracked_username="trackeduser")
    assert game.player_color is PlayerColor.WHITE


def test_pgn_and_rated_and_termination_passed_through() -> None:
    game = _normalize("white_win.json")
    assert game.rated is True
    assert game.termination == "mate"
    assert game.pgn is not None and "TrackedUser" in game.pgn


def test_time_control_formatted_from_clock() -> None:
    game = _normalize("white_win.json")
    assert game.time_control == "300+3"
