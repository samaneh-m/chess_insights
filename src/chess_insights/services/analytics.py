"""Builds an ``AnalyticsReport`` for one player from persisted games.

The only place ORM ``Game`` rows are turned into analytics-layer
``GameRecord`` objects. No statistical/mathematical logic lives here --
that's entirely in ``chess_insights.analytics``; this module only queries
and translates.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chess_insights.analytics.color import analyze_by_color
from chess_insights.analytics.game_length import analyze_game_length
from chess_insights.analytics.models import AnalyticsReport, GameRecord
from chess_insights.analytics.openings import (
    DEFAULT_MINIMUM_OPENING_GAMES,
    DEFAULT_TOP_OPENINGS_LIMIT,
    analyze_openings,
)
from chess_insights.analytics.overall import analyze_overall
from chess_insights.analytics.rating import analyze_rating
from chess_insights.analytics.time_control import analyze_speed
from chess_insights.analytics.time_of_day import analyze_time_of_day
from chess_insights.db.models.game import Game
from chess_insights.db.models.player import Player


class PlayerNotFoundError(Exception):
    """Raised when an analytics request targets a nonexistent Player."""


def _to_game_record(game: Game) -> GameRecord:
    """The one place a persisted ``Game`` row is mapped to the analytics
    layer's input type."""
    return GameRecord(
        played_at=game.played_at,
        player_color=game.player_color,
        player_rating=game.player_rating,
        result=game.result,
        opening_name=game.opening_name,
        opening_eco=game.opening_eco,
        number_of_moves=game.number_of_moves,
        duration_seconds=game.duration_seconds,
        game_speed=game.game_speed,
        time_control=game.time_control,
    )


class PlayerAnalyticsService:
    """Loads a player's persisted games and builds their ``AnalyticsReport``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def build_report(
        self,
        player_id: int,
        *,
        timezone_name: str = "UTC",
        minimum_opening_games: int = DEFAULT_MINIMUM_OPENING_GAMES,
        top_openings_limit: int = DEFAULT_TOP_OPENINGS_LIMIT,
    ) -> AnalyticsReport:
        """Build the full analytics report for ``player_id``.

        Raises:
            PlayerNotFoundError: no ``Player`` with this id exists. A valid
                player with zero games is not an error -- it produces a
                report where every statistic is zero/empty.
            zoneinfo.ZoneInfoNotFoundError: ``timezone_name`` is unknown.
        """
        player = await self._session.get(Player, player_id)
        if player is None:
            raise PlayerNotFoundError(f"Player {player_id} not found")

        result = await self._session.execute(
            select(Game).where(Game.player_id == player_id).order_by(Game.played_at)
        )
        games = [_to_game_record(row) for row in result.scalars().all()]

        return AnalyticsReport(
            player_id=player_id,
            overall=analyze_overall(games),
            by_color=analyze_by_color(games),
            openings=analyze_openings(
                games, minimum_opening_games=minimum_opening_games, limit=top_openings_limit
            ),
            rating=analyze_rating(games),
            by_time_of_day=analyze_time_of_day(games, timezone_name=timezone_name),
            by_game_length=analyze_game_length(games),
            by_speed=analyze_speed(games),
        )
