"""Tests for the pure Chess.com record -> NormalizedGame normalizer.

No network access -- all inputs are fixture dicts under
tests/fixtures/chess_com/.
"""

from datetime import timezone

import pytest

from chess_insights.domain.enums import ChessPlatform, GameResult, GameSpeed, PlayerColor
from chess_insights.integrations.chess_com.exceptions import ChessComDataError
from chess_insights.integrations.chess_com.normalizer import normalize_game
from tests.conftest import load_json_fixture

TRACKED_USERNAME = "TrackedUser"


def _normalize(fixture_name: str):
    record = load_json_fixture("chess_com", fixture_name)
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


def test_player_color_detection_is_case_insensitive() -> None:
    record = load_json_fixture("chess_com", "white_win.json")
    game = normalize_game(record, tracked_username="trackeduser")
    assert game.player_color is PlayerColor.WHITE


def test_player_rating_extracted() -> None:
    game = _normalize("white_win.json")
    assert game.player_rating == 1500


def test_opponent_rating_extracted() -> None:
    game = _normalize("white_win.json")
    assert game.opponent_rating == 1490


def test_missing_opponent_rating_is_none_not_zero() -> None:
    game = _normalize("missing_rating.json")
    assert game.player_rating == 1500
    assert game.opponent_rating is None


def test_rating_change_is_always_none() -> None:
    # Chess.com's Published Data API doesn't expose a per-game rating
    # delta; we deliberately never estimate one.
    game = _normalize("white_win.json")
    assert game.rating_change is None


def test_external_game_id_is_stable_uuid() -> None:
    game = _normalize("white_win.json")
    assert game.external_game_id == "aaaa-0001"
    assert game.platform is ChessPlatform.CHESS_COM


def test_external_game_id_repeated_normalization_is_identical() -> None:
    first = _normalize("white_win.json")
    second = _normalize("white_win.json")
    assert first.external_game_id == second.external_game_id


def test_external_game_id_falls_back_to_url_when_uuid_missing() -> None:
    record = load_json_fixture("chess_com", "white_win.json")
    del record["uuid"]
    game = normalize_game(record, tracked_username=TRACKED_USERNAME)
    assert game.external_game_id == "1000000001"


def test_played_at_is_utc_aware() -> None:
    game = _normalize("white_win.json")
    assert game.played_at.tzinfo is not None
    assert game.played_at.utcoffset().total_seconds() == 0
    assert game.played_at.astimezone(timezone.utc) == game.played_at


def test_pgn_extracted() -> None:
    game = _normalize("white_win.json")
    assert game.pgn is not None
    assert "TrackedUser" in game.pgn


def test_eco_extracted() -> None:
    game = _normalize("white_win.json")
    assert game.opening_eco == "C50"


def test_opening_name_extracted_from_eco_url() -> None:
    game = _normalize("white_win.json")
    assert game.opening_name == "Italian Game"


def test_missing_opening_is_none() -> None:
    game = _normalize("missing_opening.json")
    assert game.opening_name is None
    assert game.opening_eco is None


def test_move_count_is_ply_count() -> None:
    game = _normalize("white_win.json")
    # "1. e4 e5 2. Nf3 Nc6" -> 4 plies, unaffected by {[%clk ...]} comments
    assert game.number_of_moves == 4


def test_time_control_preserved_raw() -> None:
    game = _normalize("white_win.json")
    assert game.time_control == "600"


def test_bullet_speed_mapping() -> None:
    game = _normalize("missing_opening.json")
    assert game.game_speed is GameSpeed.BULLET


def test_blitz_speed_mapping() -> None:
    game = _normalize("white_win.json")
    assert game.game_speed is GameSpeed.BLITZ


def test_rapid_speed_mapping() -> None:
    game = _normalize("black_win.json")
    assert game.game_speed is GameSpeed.RAPID


def test_daily_maps_to_correspondence() -> None:
    record = load_json_fixture("chess_com", "white_win.json")
    record["time_class"] = "daily"
    game = normalize_game(record, tracked_username=TRACKED_USERNAME)
    assert game.game_speed is GameSpeed.CORRESPONDENCE


def test_unknown_speed_maps_to_unknown_enum_value() -> None:
    game = _normalize("unknown_speed.json")
    assert game.game_speed is GameSpeed.UNKNOWN


def test_rated_extracted() -> None:
    assert _normalize("white_win.json").rated is True
    assert _normalize("missing_rating.json").rated is False


def test_duration_seconds_is_always_none() -> None:
    # No start timestamp is available from this endpoint; never approximated.
    game = _normalize("white_win.json")
    assert game.duration_seconds is None


def test_termination_uses_descriptive_losing_side_reason() -> None:
    game = _normalize("white_win.json")
    assert game.termination == "checkmated"


def test_termination_when_tracked_player_lost() -> None:
    game = _normalize("white_loss.json")
    assert game.termination == "resigned"


def test_malformed_record_missing_end_time_raises() -> None:
    record = load_json_fixture("chess_com", "malformed.json")
    with pytest.raises(ChessComDataError):
        normalize_game(record, tracked_username=TRACKED_USERNAME)


def test_record_without_tracked_player_raises() -> None:
    record = load_json_fixture("chess_com", "white_win.json")
    with pytest.raises(ChessComDataError):
        normalize_game(record, tracked_username="SomeoneElseEntirely")
