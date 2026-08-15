"""Performance by game length, measured in **plies** (half-moves).

``GameRecord.number_of_moves`` is a ply count, not a full-move count (the
convention established when normalizing Lichess/Chess.com games). Buckets:

    Short:  0-39 plies   (roughly <20 full moves)
    Medium: 40-79 plies  (roughly 20-39 full moves)
    Long:   80+ plies    (roughly 40+ full moves)

Games with ``number_of_moves is None`` are excluded entirely -- never
assigned to "short".
"""

from collections.abc import Sequence

from chess_insights.analytics.models import (
    GameLengthBucket,
    GameLengthPerformance,
    GameRecord,
    PerformanceStats,
)
from chess_insights.domain.enums import GameResult

SHORT_GAME_MAX_PLIES = 39
MEDIUM_GAME_MAX_PLIES = 79


def _bucket_for_plies(plies: int) -> GameLengthBucket:
    if plies <= SHORT_GAME_MAX_PLIES:
        return GameLengthBucket.SHORT
    if plies <= MEDIUM_GAME_MAX_PLIES:
        return GameLengthBucket.MEDIUM
    return GameLengthBucket.LONG


def analyze_game_length(games: Sequence[GameRecord]) -> GameLengthPerformance:
    """Win/loss/draw performance grouped by ply-count bucket."""
    buckets: dict[GameLengthBucket, list[GameResult]] = {b: [] for b in GameLengthBucket}
    for game in games:
        if game.number_of_moves is None:
            continue
        buckets[_bucket_for_plies(game.number_of_moves)].append(game.result)

    return GameLengthPerformance(
        by_bucket={bucket: PerformanceStats.from_results(r) for bucket, r in buckets.items()}
    )
