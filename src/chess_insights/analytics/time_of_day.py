"""Performance by local hour-of-day bucket.

Buckets (local time, inclusive of both ends):

    Morning:     06:00-11:59
    Afternoon:   12:00-17:59
    Evening:     18:00-22:59
    Late Night:  23:00-05:59

Database timestamps are UTC. Every ``GameRecord.played_at`` must be
timezone-aware; it is converted to ``timezone_name`` (via
``zoneinfo.ZoneInfo``) before bucketing -- UTC is never silently treated
as local time. An unknown ``timezone_name`` raises
``zoneinfo.ZoneInfoNotFoundError``; a naive ``played_at`` raises
``ValueError``.
"""

from collections.abc import Sequence
from zoneinfo import ZoneInfo

from chess_insights.analytics.models import (
    GameRecord,
    PerformanceStats,
    TimeOfDayBucket,
    TimeOfDayPerformance,
)
from chess_insights.domain.enums import GameResult


def _bucket_for_hour(hour: int) -> TimeOfDayBucket:
    if 6 <= hour <= 11:
        return TimeOfDayBucket.MORNING
    if 12 <= hour <= 17:
        return TimeOfDayBucket.AFTERNOON
    if 18 <= hour <= 22:
        return TimeOfDayBucket.EVENING
    return TimeOfDayBucket.LATE_NIGHT  # 23:00-05:59


def analyze_time_of_day(
    games: Sequence[GameRecord], *, timezone_name: str = "UTC"
) -> TimeOfDayPerformance:
    """Win/loss/draw performance grouped by local hour-of-day bucket."""
    tz = ZoneInfo(timezone_name)  # raises ZoneInfoNotFoundError for an unknown name

    buckets: dict[TimeOfDayBucket, list[GameResult]] = {b: [] for b in TimeOfDayBucket}
    for game in games:
        if game.played_at.tzinfo is None:
            raise ValueError(
                f"GameRecord.played_at must be timezone-aware, got a naive datetime "
                f"for external data at {game.played_at!r}"
            )
        local_dt = game.played_at.astimezone(tz)
        buckets[_bucket_for_hour(local_dt.hour)].append(game.result)

    return TimeOfDayPerformance(
        timezone_name=timezone_name,
        by_bucket={bucket: PerformanceStats.from_results(r) for bucket, r in buckets.items()},
    )
