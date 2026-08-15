"""Fast unit tests for the `sync` CLI subcommand's argument handling.

No database or network involved -- only argparse wiring and platform-string
parsing.
"""

import pytest

from chess_insights.domain.enums import ChessPlatform
from chess_insights.main import _parse_platform, build_parser


def test_parse_platform_lichess() -> None:
    assert _parse_platform("lichess") is ChessPlatform.LICHESS


def test_parse_platform_chess_com() -> None:
    assert _parse_platform("chess_com") is ChessPlatform.CHESS_COM


def test_parse_platform_chess_dot_com_alias() -> None:
    assert _parse_platform("chess.com") is ChessPlatform.CHESS_COM


def test_parse_platform_is_case_insensitive_and_trims() -> None:
    assert _parse_platform("  LiChess  ") is ChessPlatform.LICHESS


def test_parse_platform_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        _parse_platform("not-a-platform")


def test_sync_subcommand_parses_arguments() -> None:
    parser = build_parser()
    args = parser.parse_args(["sync", "lichess", "someone", "--max-games", "50"])
    assert args.command == "sync"
    assert args.platform == "lichess"
    assert args.username == "someone"
    assert args.max_games == 50


def test_sync_subcommand_default_max_games() -> None:
    parser = build_parser()
    args = parser.parse_args(["sync", "chess_com", "someone"])
    assert args.max_games == 100


def test_sync_subcommand_rejects_unknown_platform_choice() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["sync", "not-a-platform", "someone"])
