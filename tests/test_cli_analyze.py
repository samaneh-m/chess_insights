"""Fast unit tests for the `analyze` CLI subcommand's argument handling.

No database or network involved -- only argparse wiring.
"""

import pytest

from chess_insights.analytics.openings import DEFAULT_MINIMUM_OPENING_GAMES
from chess_insights.main import build_parser


def test_analyze_subcommand_parses_arguments() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["analyze", "42", "--timezone", "Europe/Berlin", "--minimum-opening-games", "5"]
    )
    assert args.command == "analyze"
    assert args.player_id == 42
    assert args.timezone == "Europe/Berlin"
    assert args.minimum_opening_games == 5


def test_analyze_subcommand_defaults() -> None:
    parser = build_parser()
    args = parser.parse_args(["analyze", "1"])
    assert args.timezone == "UTC"
    assert args.minimum_opening_games == DEFAULT_MINIMUM_OPENING_GAMES


def test_analyze_subcommand_requires_integer_player_id() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["analyze", "not-a-number"])


def test_analyze_subcommand_requires_player_id() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["analyze"])
