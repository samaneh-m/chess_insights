"""Pure Python chess performance analytics.

Computes structured facts (win rates, opening/rating/time breakdowns) from
``GameRecord`` sequences -- no FastAPI, no SQLAlchemy, no generated text,
no charts. ``chess_insights.services.analytics.PlayerAnalyticsService``
loads persisted games and calls into this package; nothing here talks to
the database itself.
"""

from chess_insights.analytics.color import analyze_by_color
from chess_insights.analytics.game_length import analyze_game_length
from chess_insights.analytics.models import (
    AnalyticsReport,
    ColorPerformance,
    GameLengthBucket,
    GameLengthPerformance,
    GameRecord,
    OpeningAnalysis,
    OpeningStats,
    PerformanceStats,
    RatingDirection,
    RatingPoint,
    RatingTrend,
    SpeedPerformance,
    TimeOfDayBucket,
    TimeOfDayPerformance,
)
from chess_insights.analytics.openings import analyze_openings
from chess_insights.analytics.overall import analyze_overall
from chess_insights.analytics.rating import analyze_rating
from chess_insights.analytics.time_control import analyze_speed
from chess_insights.analytics.time_of_day import analyze_time_of_day

__all__ = [
    "AnalyticsReport",
    "ColorPerformance",
    "GameLengthBucket",
    "GameLengthPerformance",
    "GameRecord",
    "OpeningAnalysis",
    "OpeningStats",
    "PerformanceStats",
    "RatingDirection",
    "RatingPoint",
    "RatingTrend",
    "SpeedPerformance",
    "TimeOfDayBucket",
    "TimeOfDayPerformance",
    "analyze_by_color",
    "analyze_game_length",
    "analyze_openings",
    "analyze_overall",
    "analyze_rating",
    "analyze_speed",
    "analyze_time_of_day",
]
