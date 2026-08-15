"""Tests for analytics.color.analyze_by_color."""

from chess_insights.analytics.color import analyze_by_color
from chess_insights.domain.enums import GameResult, PlayerColor
from tests.conftest import make_game_record


def test_white_statistics() -> None:
    games = [
        make_game_record(player_color=PlayerColor.WHITE, result=GameResult.WIN),
        make_game_record(player_color=PlayerColor.WHITE, result=GameResult.LOSS),
    ]
    perf = analyze_by_color(games)
    assert perf.white.games == 2
    assert perf.white.wins == 1
    assert perf.white.losses == 1


def test_black_statistics() -> None:
    games = [
        make_game_record(player_color=PlayerColor.BLACK, result=GameResult.WIN),
        make_game_record(player_color=PlayerColor.BLACK, result=GameResult.WIN),
    ]
    perf = analyze_by_color(games)
    assert perf.black.games == 2
    assert perf.black.wins == 2


def test_mixed_colors_are_kept_separate() -> None:
    games = [
        make_game_record(player_color=PlayerColor.WHITE, result=GameResult.WIN),
        make_game_record(player_color=PlayerColor.BLACK, result=GameResult.LOSS),
    ]
    perf = analyze_by_color(games)
    assert perf.white.games == 1
    assert perf.white.wins == 1
    assert perf.black.games == 1
    assert perf.black.losses == 1


def test_missing_color_does_not_crash_and_is_excluded() -> None:
    games = [
        make_game_record(player_color=None, result=GameResult.WIN),
        make_game_record(player_color=PlayerColor.WHITE, result=GameResult.WIN),
    ]
    perf = analyze_by_color(games)
    assert perf.white.games == 1
    assert perf.black.games == 0


def test_color_sample_counts_do_not_include_the_other_color() -> None:
    games = [make_game_record(player_color=PlayerColor.WHITE) for _ in range(3)]
    perf = analyze_by_color(games)
    assert perf.white.games == 3
    assert perf.black.games == 0
