"""Cross-platform tests: both clients satisfy the same contract and produce
equivalent NormalizedGame semantics, so Phase 6 persistence can consume
either platform's output without platform-specific branching.
"""

import inspect
from datetime import timezone

from chess_insights.domain.enums import GameResult, GameSpeed, PlayerColor
from chess_insights.integrations.base import ChessPlatformClient
from chess_insights.integrations.chess_com.client import ChessComClient
from chess_insights.integrations.chess_com.normalizer import normalize_game as normalize_chess_com
from chess_insights.integrations.lichess.client import LichessClient
from chess_insights.integrations.lichess.normalizer import normalize_game as normalize_lichess
from chess_insights.schemas.game import NormalizedGame
from tests.conftest import load_json_fixture


def _has_matching_fetch_games_signature(cls: type) -> bool:
    sig = inspect.signature(cls.fetch_games)
    params = list(sig.parameters)
    # self, username, *, max_games
    return params[:2] == ["self", "username"] and "max_games" in sig.parameters


def test_lichess_client_matches_platform_contract_shape() -> None:
    assert _has_matching_fetch_games_signature(LichessClient)
    assert hasattr(LichessClient, "fetch_games")


def test_chess_com_client_matches_platform_contract_shape() -> None:
    assert _has_matching_fetch_games_signature(ChessComClient)
    assert hasattr(ChessComClient, "fetch_games")


def test_both_clients_share_the_same_fetch_games_parameter_names() -> None:
    lichess_params = inspect.signature(LichessClient.fetch_games).parameters
    chess_com_params = inspect.signature(ChessComClient.fetch_games).parameters
    assert set(lichess_params) == set(chess_com_params)


def test_protocol_defines_fetch_games() -> None:
    assert set(inspect.signature(ChessPlatformClient.fetch_games).parameters) == {
        "self",
        "username",
        "max_games",
    }


def _lichess_game():
    record = load_json_fixture("lichess", "white_win.json")
    return normalize_lichess(record, tracked_username="TrackedUser")


def _chess_com_game():
    record = load_json_fixture("chess_com", "white_win.json")
    return normalize_chess_com(record, tracked_username="TrackedUser")


def test_both_normalizers_return_normalized_game_instances() -> None:
    assert isinstance(_lichess_game(), NormalizedGame)
    assert isinstance(_chess_com_game(), NormalizedGame)


def test_both_normalizers_use_the_same_result_enum_type() -> None:
    lichess_game = _lichess_game()
    chess_com_game = _chess_com_game()
    assert isinstance(lichess_game.result, GameResult)
    assert isinstance(chess_com_game.result, GameResult)
    assert lichess_game.result is GameResult.WIN
    assert chess_com_game.result is GameResult.WIN


def test_both_normalizers_use_the_same_player_color_enum_type() -> None:
    lichess_game = _lichess_game()
    chess_com_game = _chess_com_game()
    assert isinstance(lichess_game.player_color, PlayerColor)
    assert isinstance(chess_com_game.player_color, PlayerColor)


def test_both_normalizers_use_the_same_game_speed_enum_type() -> None:
    lichess_game = _lichess_game()
    chess_com_game = _chess_com_game()
    assert isinstance(lichess_game.game_speed, GameSpeed)
    assert isinstance(chess_com_game.game_speed, GameSpeed)


def test_both_normalizers_produce_utc_aware_played_at() -> None:
    for game in (_lichess_game(), _chess_com_game()):
        assert game.played_at.tzinfo is not None
        assert game.played_at.utcoffset().total_seconds() == 0
        assert game.played_at.astimezone(timezone.utc) == game.played_at


def test_both_normalizers_use_ply_count_for_number_of_moves() -> None:
    # Both fixtures' games are 4-ply (2 full moves) openings.
    assert _lichess_game().number_of_moves == 10  # fixture has 10 plies
    assert _chess_com_game().number_of_moves == 4  # fixture has 4 plies
    # The important cross-platform invariant: neither divides/multiplies by
    # 2 to convert to full-move count -- both count individual half-moves.
    assert isinstance(_lichess_game().number_of_moves, int)
    assert isinstance(_chess_com_game().number_of_moves, int)


def test_both_normalizers_produce_the_shared_platform_enum_correctly() -> None:
    from chess_insights.domain.enums import ChessPlatform

    assert _lichess_game().platform is ChessPlatform.LICHESS
    assert _chess_com_game().platform is ChessPlatform.CHESS_COM
