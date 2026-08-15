"""Tests for analytics.time_of_day.analyze_time_of_day.

Buckets (local time): Morning 06:00-11:59, Afternoon 12:00-17:59,
Evening 18:00-22:59, Late Night 23:00-05:59.
"""

from datetime import datetime, timezone

import pytest

from chess_insights.analytics.models import GameRecord, TimeOfDayBucket
from chess_insights.analytics.time_of_day import analyze_time_of_day
from chess_insights.domain.enums import GameResult
from tests.conftest import make_game_record


def _utc_at(hour: int, minute: int = 0) -> datetime:
    return datetime(2024, 6, 15, hour, minute, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("hour", "minute", "expected_bucket"),
    [
        (5, 59, TimeOfDayBucket.LATE_NIGHT),
        (6, 0, TimeOfDayBucket.MORNING),
        (11, 59, TimeOfDayBucket.MORNING),
        (12, 0, TimeOfDayBucket.AFTERNOON),
        (17, 59, TimeOfDayBucket.AFTERNOON),
        (18, 0, TimeOfDayBucket.EVENING),
        (22, 59, TimeOfDayBucket.EVENING),
        (23, 0, TimeOfDayBucket.LATE_NIGHT),
    ],
)
def test_bucket_boundaries(hour, minute, expected_bucket) -> None:
    game = make_game_record(played_at=_utc_at(hour, minute))
    perf = analyze_time_of_day([game], timezone_name="UTC")
    assert perf.by_bucket[expected_bucket].games == 1
    for bucket in TimeOfDayBucket:
        if bucket is not expected_bucket:
            assert perf.by_bucket[bucket].games == 0


def test_timezone_conversion_crosses_a_bucket_boundary() -> None:
    # 05:30 UTC -> 07:30 in Europe/Berlin (UTC+2 in June) -> Morning,
    # while in UTC itself 05:30 is Late Night.
    game = make_game_record(played_at=_utc_at(5, 30))
    perf_utc = analyze_time_of_day([game], timezone_name="UTC")
    perf_berlin = analyze_time_of_day([game], timezone_name="Europe/Berlin")
    assert perf_utc.by_bucket[TimeOfDayBucket.LATE_NIGHT].games == 1
    assert perf_berlin.by_bucket[TimeOfDayBucket.MORNING].games == 1


def test_default_timezone_is_utc() -> None:
    game = make_game_record(played_at=_utc_at(8))
    perf = analyze_time_of_day([game])
    assert perf.timezone_name == "UTC"
    assert perf.by_bucket[TimeOfDayBucket.MORNING].games == 1


def test_invalid_timezone_raises_clearly() -> None:
    from zoneinfo import ZoneInfoNotFoundError

    with pytest.raises(ZoneInfoNotFoundError):
        analyze_time_of_day([make_game_record()], timezone_name="Not/ARealZone")


def test_naive_played_at_raises_value_error() -> None:
    naive_game = GameRecord(
        played_at=datetime(2024, 1, 1, 8),  # no tzinfo
        player_color=None,
        player_rating=None,
        result=GameResult.WIN,
        opening_name=None,
        opening_eco=None,
        number_of_moves=None,
        duration_seconds=None,
        game_speed=None,
        time_control=None,
    )
    with pytest.raises(ValueError, match="timezone-aware"):
        analyze_time_of_day([naive_game])


def test_bucket_statistics_are_computed_per_bucket() -> None:
    games = [
        make_game_record(played_at=_utc_at(8), result=GameResult.WIN),
        make_game_record(played_at=_utc_at(9), result=GameResult.LOSS),
        make_game_record(played_at=_utc_at(20), result=GameResult.WIN),
    ]
    perf = analyze_time_of_day(games, timezone_name="UTC")
    assert perf.by_bucket[TimeOfDayBucket.MORNING].games == 2
    assert perf.by_bucket[TimeOfDayBucket.MORNING].wins == 1
    assert perf.by_bucket[TimeOfDayBucket.EVENING].games == 1
    assert perf.by_bucket[TimeOfDayBucket.EVENING].wins == 1
