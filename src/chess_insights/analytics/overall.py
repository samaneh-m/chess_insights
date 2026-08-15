"""Overall performance: every game, regardless of color/opening/etc."""

from collections.abc import Sequence

from chess_insights.analytics.models import GameRecord, PerformanceStats


def analyze_overall(games: Sequence[GameRecord]) -> PerformanceStats:
    """Win/loss/draw counts and rates across all given games."""
    return PerformanceStats.from_results(game.result for game in games)
