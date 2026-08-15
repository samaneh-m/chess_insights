"""Opening performance, with deterministic best/worst ranking.

Grouping rule: games are grouped by ``(opening_eco, opening_name)``.
Games with ``opening_name is None`` are excluded entirely (not grouped
under "Unknown") -- they still count toward overall performance, just not
opening-specific analysis, since we have nothing meaningful to group them
by.
"""

from collections.abc import Sequence

from chess_insights.analytics.models import (
    GameRecord,
    OpeningAnalysis,
    OpeningStats,
    PerformanceStats,
)
from chess_insights.domain.enums import GameResult

DEFAULT_MINIMUM_OPENING_GAMES = 3
DEFAULT_TOP_OPENINGS_LIMIT = 5


def analyze_openings(
    games: Sequence[GameRecord],
    *,
    minimum_opening_games: int = DEFAULT_MINIMUM_OPENING_GAMES,
    limit: int = DEFAULT_TOP_OPENINGS_LIMIT,
) -> OpeningAnalysis:
    """Group games by opening and rank the best/worst by win rate.

    ``openings`` includes every opening with at least one game (sorted by
    name, ascending). ``top_openings``/``bottom_openings`` only consider
    openings with ``games >= minimum_opening_games`` -- a single win isn't
    a "best opening" -- and are ranked deterministically:

    - top: win_rate descending, then games descending, then name ascending
    - bottom: win_rate ascending, then games descending, then name ascending
    """
    groups: dict[tuple[str | None, str], list[GameResult]] = {}
    for game in games:
        if game.opening_name is None:
            continue
        key = (game.opening_eco, game.opening_name)
        groups.setdefault(key, []).append(game.result)

    all_openings = tuple(
        sorted(
            (
                OpeningStats(
                    opening_name=name,
                    opening_eco=eco,
                    stats=PerformanceStats.from_results(results),
                )
                for (eco, name), results in groups.items()
            ),
            key=lambda o: (o.opening_name, o.opening_eco or ""),
        )
    )

    qualifying = [o for o in all_openings if o.stats.games >= minimum_opening_games]

    top_openings = tuple(
        sorted(
            qualifying,
            key=lambda o: (-o.stats.win_rate, -o.stats.games, o.opening_name),
        )[:limit]
    )
    bottom_openings = tuple(
        sorted(
            qualifying,
            key=lambda o: (o.stats.win_rate, -o.stats.games, o.opening_name),
        )[:limit]
    )

    return OpeningAnalysis(
        minimum_opening_games=minimum_opening_games,
        openings=all_openings,
        top_openings=top_openings,
        bottom_openings=bottom_openings,
    )
