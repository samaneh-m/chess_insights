"""Tests for analytics.rating.analyze_rating."""

from datetime import datetime, timezone

from chess_insights.analytics.models import RatingDirection
from chess_insights.analytics.rating import (
    MIN_RATING_POINTS_FOR_TREND,
    RATING_TREND_THRESHOLD,
    analyze_rating,
)
from tests.conftest import make_game_record


def _dt(day: int) -> datetime:
    return datetime(2024, 1, day, tzinfo=timezone.utc)


def test_no_rated_games_is_insufficient_data() -> None:
    trend = analyze_rating([make_game_record(player_rating=None)])
    assert trend.data_points == ()
    assert trend.earliest_rating is None
    assert trend.direction is RatingDirection.INSUFFICIENT_DATA


def test_data_points_are_chronological_regardless_of_input_order() -> None:
    games = [
        make_game_record(played_at=_dt(3), player_rating=1520),
        make_game_record(played_at=_dt(1), player_rating=1500),
        make_game_record(played_at=_dt(2), player_rating=1510),
    ]
    trend = analyze_rating(games)
    assert [p.rating for p in trend.data_points] == [1500, 1510, 1520]


def test_earliest_and_latest_rating() -> None:
    games = [
        make_game_record(played_at=_dt(1), player_rating=1500),
        make_game_record(played_at=_dt(2), player_rating=1550),
    ]
    trend = analyze_rating(games)
    assert trend.earliest_rating == 1500
    assert trend.latest_rating == 1550


def test_highest_and_lowest_rating() -> None:
    games = [
        make_game_record(played_at=_dt(1), player_rating=1500),
        make_game_record(played_at=_dt(2), player_rating=1600),
        make_game_record(played_at=_dt(3), player_rating=1400),
    ]
    trend = analyze_rating(games)
    assert trend.highest_rating == 1600
    assert trend.lowest_rating == 1400


def test_positive_rating_change() -> None:
    games = [
        make_game_record(played_at=_dt(1), player_rating=1500),
        make_game_record(played_at=_dt(2), player_rating=1600),
    ]
    trend = analyze_rating(games)
    assert trend.rating_change == 100


def test_negative_rating_change() -> None:
    games = [
        make_game_record(played_at=_dt(1), player_rating=1600),
        make_game_record(played_at=_dt(2), player_rating=1500),
    ]
    trend = analyze_rating(games)
    assert trend.rating_change == -100


def test_games_with_missing_rating_are_ignored() -> None:
    games = [
        make_game_record(played_at=_dt(1), player_rating=1500),
        make_game_record(played_at=_dt(2), player_rating=None),
        make_game_record(played_at=_dt(3), player_rating=1600),
    ]
    trend = analyze_rating(games)
    assert len(trend.data_points) == 2
    assert trend.rating_change == 100


def test_insufficient_data_below_minimum_points() -> None:
    games = [
        make_game_record(played_at=_dt(d), player_rating=1500 + d * 50)
        for d in range(1, MIN_RATING_POINTS_FOR_TREND)  # one short of the minimum
    ]
    trend = analyze_rating(games)
    assert trend.direction is RatingDirection.INSUFFICIENT_DATA


def test_stable_trend_when_change_is_below_threshold() -> None:
    games = [
        make_game_record(played_at=_dt(d), player_rating=1500)
        for d in range(1, MIN_RATING_POINTS_FOR_TREND + 2)
    ]
    # Nudge the last point by less than the threshold.
    games[-1] = make_game_record(
        played_at=_dt(MIN_RATING_POINTS_FOR_TREND + 1),
        player_rating=1500 + RATING_TREND_THRESHOLD - 1,
    )
    trend = analyze_rating(games)
    assert trend.direction is RatingDirection.STABLE


def test_improving_trend_when_change_meets_threshold() -> None:
    games = [
        make_game_record(played_at=_dt(d), player_rating=1500)
        for d in range(1, MIN_RATING_POINTS_FOR_TREND + 2)
    ]
    games[-1] = make_game_record(
        played_at=_dt(MIN_RATING_POINTS_FOR_TREND + 1),
        player_rating=1500 + RATING_TREND_THRESHOLD,
    )
    trend = analyze_rating(games)
    assert trend.direction is RatingDirection.IMPROVING


def test_declining_trend_when_change_meets_negative_threshold() -> None:
    games = [
        make_game_record(played_at=_dt(d), player_rating=1500)
        for d in range(1, MIN_RATING_POINTS_FOR_TREND + 2)
    ]
    games[-1] = make_game_record(
        played_at=_dt(MIN_RATING_POINTS_FOR_TREND + 1),
        player_rating=1500 - RATING_TREND_THRESHOLD,
    )
    trend = analyze_rating(games)
    assert trend.direction is RatingDirection.DECLINING
