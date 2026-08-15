"""Typed inputs and results for the analytics engine.

Percentage convention: every ``*_rate`` field is on a **0.0-100.0 scale**
(e.g. ``63.5`` means 63.5%), rounded to 2 decimal places, computed in
exactly one place (``_percentage`` below) so rounding never drifts between
modules.
"""

import enum
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime

from chess_insights.domain.enums import GameResult, GameSpeed, PlayerColor


@dataclass(frozen=True, slots=True)
class GameRecord:
    """Analytics-layer input: the fields analysis needs, decoupled from the
    ``Game`` ORM model so pure analytics functions are testable without a
    database. ``number_of_moves`` is a **ply count** (half-moves), per the
    convention established for normalized games in Phase 4-5.
    """

    played_at: datetime
    player_color: PlayerColor | None
    player_rating: int | None
    result: GameResult
    opening_name: str | None
    opening_eco: str | None
    number_of_moves: int | None
    duration_seconds: int | None
    game_speed: GameSpeed | None
    time_control: str | None


def _percentage(count: int, total: int) -> float:
    """``count`` as a percentage of ``total``, 0.0-100.0, rounded to 2 dp.

    Returns ``0.0`` (never ``NaN``) when ``total`` is 0.
    """
    if total == 0:
        return 0.0
    return round(count / total * 100, 2)


@dataclass(frozen=True, slots=True)
class PerformanceStats:
    """Win/loss/draw counts and rates for some set of games.

    Zero games is always valid: every count is 0 and every rate is 0.0.
    """

    games: int
    wins: int
    losses: int
    draws: int
    win_rate: float
    loss_rate: float
    draw_rate: float

    @classmethod
    def from_results(cls, results: Iterable[GameResult]) -> "PerformanceStats":
        """The one place win/loss/draw counting and rate calculation
        happens -- every analytics module builds its ``PerformanceStats``
        through this, so the math is never duplicated."""
        results = list(results)
        games = len(results)
        wins = sum(1 for r in results if r is GameResult.WIN)
        losses = sum(1 for r in results if r is GameResult.LOSS)
        draws = sum(1 for r in results if r is GameResult.DRAW)
        return cls(
            games=games,
            wins=wins,
            losses=losses,
            draws=draws,
            win_rate=_percentage(wins, games),
            loss_rate=_percentage(losses, games),
            draw_rate=_percentage(draws, games),
        )


@dataclass(frozen=True, slots=True)
class ColorPerformance:
    """Performance split by the tracked player's color.

    Games with ``player_color is None`` are excluded from both ``white``
    and ``black`` (they still count toward overall performance).
    """

    white: PerformanceStats
    black: PerformanceStats


@dataclass(frozen=True, slots=True)
class OpeningStats:
    """Performance for one opening (grouped by ``(opening_eco,
    opening_name)`` -- see ``analytics.openings``)."""

    opening_name: str
    opening_eco: str | None
    stats: PerformanceStats


@dataclass(frozen=True, slots=True)
class OpeningAnalysis:
    """All openings played, plus deterministically ranked best/worst.

    ``openings`` includes every opening with at least one game (sorted by
    name). ``top_openings``/``bottom_openings`` only include openings with
    ``games >= minimum_opening_games`` -- a single game is not a
    meaningful "best opening".
    """

    minimum_opening_games: int
    openings: tuple[OpeningStats, ...]
    top_openings: tuple[OpeningStats, ...]
    bottom_openings: tuple[OpeningStats, ...]


class RatingDirection(str, enum.Enum):
    """A conservative, deterministic classification of a rating trend.

    See ``analytics.rating`` for the exact rule.
    """

    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass(frozen=True, slots=True)
class RatingPoint:
    """One rating observation, for future time-series charting."""

    played_at: datetime
    rating: int


@dataclass(frozen=True, slots=True)
class RatingTrend:
    """Rating summary over time, built only from games with a known rating."""

    data_points: tuple[RatingPoint, ...]
    earliest_rating: int | None
    latest_rating: int | None
    highest_rating: int | None
    lowest_rating: int | None
    rating_change: int | None
    direction: RatingDirection


class TimeOfDayBucket(str, enum.Enum):
    """Local-hour buckets. See ``analytics.time_of_day`` for boundaries."""

    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    LATE_NIGHT = "late_night"


@dataclass(frozen=True, slots=True)
class TimeOfDayPerformance:
    timezone_name: str
    by_bucket: Mapping[TimeOfDayBucket, PerformanceStats]


class GameLengthBucket(str, enum.Enum):
    """Ply-count buckets. See ``analytics.game_length`` for thresholds."""

    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


@dataclass(frozen=True, slots=True)
class GameLengthPerformance:
    by_bucket: Mapping[GameLengthBucket, PerformanceStats]


@dataclass(frozen=True, slots=True)
class SpeedPerformance:
    """Performance by ``GameSpeed``. ``game_speed is None`` is grouped
    under ``GameSpeed.UNKNOWN`` (see ``analytics.time_control``)."""

    by_speed: Mapping[GameSpeed, PerformanceStats]


@dataclass(frozen=True, slots=True)
class AnalyticsReport:
    """The complete set of structured analytical facts for one player.

    Facts only -- no generated text, no charts. That's a later phase.
    """

    player_id: int
    overall: PerformanceStats
    by_color: ColorPerformance
    openings: OpeningAnalysis
    rating: RatingTrend
    by_time_of_day: TimeOfDayPerformance
    by_game_length: GameLengthPerformance
    by_speed: SpeedPerformance
