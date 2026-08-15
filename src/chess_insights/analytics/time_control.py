"""Performance by ``GameSpeed`` (bullet/blitz/rapid/classical/correspondence).

``game_speed is None`` is grouped under ``GameSpeed.UNKNOWN`` -- the same
bucket already used for platform values normalizers couldn't classify --
rather than excluded, since a speed breakdown with silently-dropped games
would be misleading.
"""

from collections.abc import Sequence

from chess_insights.analytics.models import GameRecord, PerformanceStats, SpeedPerformance
from chess_insights.domain.enums import GameResult, GameSpeed


def analyze_speed(games: Sequence[GameRecord]) -> SpeedPerformance:
    """Win/loss/draw performance grouped by game speed."""
    buckets: dict[GameSpeed, list[GameResult]] = {speed: [] for speed in GameSpeed}
    for game in games:
        speed = game.game_speed if game.game_speed is not None else GameSpeed.UNKNOWN
        buckets[speed].append(game.result)

    return SpeedPerformance(
        by_speed={speed: PerformanceStats.from_results(r) for speed, r in buckets.items()}
    )
