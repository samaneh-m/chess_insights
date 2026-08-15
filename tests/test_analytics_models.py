"""Tests for PerformanceStats.from_results -- the shared stats primitive
every analytics module builds on."""

from chess_insights.analytics.models import PerformanceStats
from chess_insights.domain.enums import GameResult


def test_zero_games() -> None:
    stats = PerformanceStats.from_results([])
    assert stats.games == 0
    assert stats.wins == 0
    assert stats.losses == 0
    assert stats.draws == 0
    assert stats.win_rate == 0.0
    assert stats.loss_rate == 0.0
    assert stats.draw_rate == 0.0


def test_one_win() -> None:
    stats = PerformanceStats.from_results([GameResult.WIN])
    assert stats.games == 1
    assert stats.wins == 1
    assert stats.win_rate == 100.0
    assert stats.loss_rate == 0.0
    assert stats.draw_rate == 0.0


def test_mixture_of_results() -> None:
    results = [GameResult.WIN, GameResult.WIN, GameResult.LOSS, GameResult.DRAW]
    stats = PerformanceStats.from_results(results)
    assert stats.games == 4
    assert stats.wins == 2
    assert stats.losses == 1
    assert stats.draws == 1


def test_percentages_are_on_a_0_to_100_scale() -> None:
    stats = PerformanceStats.from_results([GameResult.WIN, GameResult.LOSS])
    assert stats.win_rate == 50.0
    assert stats.loss_rate == 50.0


def test_percentage_rounding_to_two_decimal_places() -> None:
    # 2/3 = 66.666...% -> rounds to 66.67
    results = [GameResult.WIN, GameResult.WIN, GameResult.LOSS]
    stats = PerformanceStats.from_results(results)
    assert stats.win_rate == 66.67
    assert stats.loss_rate == 33.33
