"""Rating trend over time.

Games with no ``player_rating`` are ignored entirely. Direction
classification is a deliberately simple, transparent, deterministic rule
(no regression/ML): at least ``MIN_RATING_POINTS_FOR_TREND`` rated games
are required, and the change from the earliest to the latest rating must
reach ``RATING_TREND_THRESHOLD`` in either direction to count as a real
trend -- a handful of games or a +2 blip is reported as ``STABLE`` (or
``INSUFFICIENT_DATA``), not ``IMPROVING``/``DECLINING``.
"""

from collections.abc import Sequence

from chess_insights.analytics.models import GameRecord, RatingDirection, RatingPoint, RatingTrend

MIN_RATING_POINTS_FOR_TREND = 5
RATING_TREND_THRESHOLD = 20


def analyze_rating(games: Sequence[GameRecord]) -> RatingTrend:
    """Chronological rating summary, ignoring games with no rating."""
    points = sorted(
        (
            RatingPoint(played_at=g.played_at, rating=g.player_rating)
            for g in games
            if g.player_rating is not None
        ),
        key=lambda p: p.played_at,
    )

    if not points:
        return RatingTrend(
            data_points=(),
            earliest_rating=None,
            latest_rating=None,
            highest_rating=None,
            lowest_rating=None,
            rating_change=None,
            direction=RatingDirection.INSUFFICIENT_DATA,
        )

    ratings = [p.rating for p in points]
    earliest_rating = ratings[0]
    latest_rating = ratings[-1]
    rating_change = latest_rating - earliest_rating

    if len(points) < MIN_RATING_POINTS_FOR_TREND:
        direction = RatingDirection.INSUFFICIENT_DATA
    elif rating_change >= RATING_TREND_THRESHOLD:
        direction = RatingDirection.IMPROVING
    elif rating_change <= -RATING_TREND_THRESHOLD:
        direction = RatingDirection.DECLINING
    else:
        direction = RatingDirection.STABLE

    return RatingTrend(
        data_points=tuple(points),
        earliest_rating=earliest_rating,
        latest_rating=latest_rating,
        highest_rating=max(ratings),
        lowest_rating=min(ratings),
        rating_change=rating_change,
        direction=direction,
    )
