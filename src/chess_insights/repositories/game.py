"""Game persistence operations.

No commits happen here -- the caller (a service) owns the transaction.
"""

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chess_insights.db.models.game import Game
from chess_insights.domain.enums import ChessPlatform
from chess_insights.schemas.game import NormalizedGame


def normalized_game_to_game(normalized: NormalizedGame, *, player_id: int) -> Game:
    """The one place a ``NormalizedGame`` is mapped onto the ``Game`` ORM
    model, regardless of which platform it came from.

    ``player_id`` and the ``created_at``/``updated_at`` timestamps are
    persistence-only concerns supplied here / by the database -- everything
    else comes straight from the normalized game.
    """
    return Game(
        player_id=player_id,
        platform=normalized.platform,
        external_game_id=normalized.external_game_id,
        played_at=normalized.played_at,
        player_color=normalized.player_color,
        opponent_username=normalized.opponent_username,
        player_rating=normalized.player_rating,
        opponent_rating=normalized.opponent_rating,
        rating_change=normalized.rating_change,
        result=normalized.result,
        opening_name=normalized.opening_name,
        opening_eco=normalized.opening_eco,
        number_of_moves=normalized.number_of_moves,
        duration_seconds=normalized.duration_seconds,
        time_control=normalized.time_control,
        game_speed=normalized.game_speed,
        rated=normalized.rated,
        termination=normalized.termination,
        pgn=normalized.pgn,
    )


class GameRepository:
    """Persistence operations for ``Game``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def existing_external_ids(
        self,
        player_id: int,
        platform: ChessPlatform,
        external_game_ids: Iterable[str],
    ) -> set[str]:
        """Which of ``external_game_ids`` are already stored for this
        player/platform -- one batch query, not one per game."""
        ids = list(external_game_ids)
        if not ids:
            return set()
        result = await self._session.execute(
            select(Game.external_game_id).where(
                Game.player_id == player_id,
                Game.platform == platform,
                Game.external_game_id.in_(ids),
            )
        )
        return set(result.scalars().all())

    async def exists(self, player_id: int, platform: ChessPlatform, external_game_id: str) -> bool:
        """Single-game convenience wrapper around ``existing_external_ids``."""
        found = await self.existing_external_ids(player_id, platform, [external_game_id])
        return external_game_id in found

    async def add_many(self, normalized_games: Iterable[NormalizedGame], *, player_id: int) -> int:
        """Add ORM rows for the given normalized games. Not committed --
        the caller decides the transaction boundary. Returns how many rows
        were added."""
        games = [normalized_game_to_game(g, player_id=player_id) for g in normalized_games]
        self._session.add_all(games)
        return len(games)
