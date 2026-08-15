"""Performance split by the tracked player's color."""

from collections.abc import Sequence

from chess_insights.analytics.models import ColorPerformance, GameRecord, PerformanceStats
from chess_insights.domain.enums import PlayerColor


def analyze_by_color(games: Sequence[GameRecord]) -> ColorPerformance:
    """White/Black performance.

    Games with ``player_color is None`` are excluded from both -- they
    still count toward ``analyze_overall``, just not here, since we can't
    say which color they belong to.
    """
    white_results = (g.result for g in games if g.player_color is PlayerColor.WHITE)
    black_results = (g.result for g in games if g.player_color is PlayerColor.BLACK)
    return ColorPerformance(
        white=PerformanceStats.from_results(white_results),
        black=PerformanceStats.from_results(black_results),
    )
