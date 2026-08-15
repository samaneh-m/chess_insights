"""Tests for analytics.overall.analyze_overall (mostly covered by
test_analytics_models.py's PerformanceStats tests; this checks the
GameRecord-level wiring)."""

from chess_insights.analytics.overall import analyze_overall
from chess_insights.domain.enums import GameResult
from tests.conftest import make_game_record


def test_overall_with_zero_games() -> None:
    stats = analyze_overall([])
    assert stats.games == 0
    assert stats.win_rate == 0.0


def test_overall_counts_every_game_regardless_of_color_or_opening() -> None:
    games = [
        make_game_record(result=GameResult.WIN, player_color=None, opening_name=None),
        make_game_record(result=GameResult.LOSS),
        make_game_record(result=GameResult.DRAW),
    ]
    stats = analyze_overall(games)
    assert stats.games == 3
    assert stats.wins == 1
    assert stats.losses == 1
    assert stats.draws == 1
