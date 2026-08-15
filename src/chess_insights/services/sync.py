"""Synchronizes a player's game history from a platform into PostgreSQL.

Full flow: platform + username -> platform client -> list[NormalizedGame]
-> repositories -> PostgreSQL. This is the one place that connects the
integrations layer to persistence; nothing here talks HTTP directly, and
nothing in ``repositories`` knows a platform client exists.
"""

import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from chess_insights.domain.enums import ChessPlatform
from chess_insights.integrations.base import ChessPlatformClient
from chess_insights.integrations.chess_com import ChessComClient
from chess_insights.integrations.lichess import LichessClient
from chess_insights.repositories.game import GameRepository
from chess_insights.repositories.player import PlayerRepository

logger = logging.getLogger(__name__)


class SyncError(Exception):
    """A synchronization run failed (platform API error or database error).

    The original exception (a ``LichessError``/``ChessComError`` subtype,
    or a SQLAlchemy error) is preserved via exception chaining.
    """


@dataclass(frozen=True, slots=True)
class SyncResult:
    """Outcome of one ``GameSyncService.sync_player`` call."""

    player_id: int
    platform: ChessPlatform
    username: str
    fetched_games: int
    imported_games: int
    skipped_games: int
    last_sync_at: datetime


# Centralizes platform -> client selection so nothing else in the codebase
# needs `if platform == ChessPlatform.LICHESS: ...` branching. Each factory
# takes no arguments; both clients are usable with just their defaults.
_CLIENT_FACTORIES: dict[ChessPlatform, Callable[[], ChessPlatformClient]] = {
    ChessPlatform.LICHESS: LichessClient,
    ChessPlatform.CHESS_COM: ChessComClient,
}


class GameSyncService:
    """Fetches a player's games from a platform and persists the new ones.

    Owns the transaction for one ``sync_player`` call: the platform fetch
    happens *before* any database write, so a failed fetch (user not
    found, rate limited, network error) never creates a Player row implying
    a successful sync. If persistence then fails for any reason, the
    session is rolled back and ``last_sync_at`` is left untouched.
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        client_factories: Mapping[ChessPlatform, Callable[[], ChessPlatformClient]] | None = None,
    ) -> None:
        self._session = session
        self._players = PlayerRepository(session)
        self._games = GameRepository(session)
        self._client_factories = client_factories or _CLIENT_FACTORIES

    async def sync_player(
        self,
        *,
        platform: ChessPlatform,
        username: str,
        max_games: int | None = None,
    ) -> SyncResult:
        """Fetch and persist ``username``'s games from ``platform``.

        ``max_games`` is forwarded to the platform client as-is (``None``
        means "use the client's own default" via that client's normal
        semantics) -- no second limit is applied here.

        Raises:
            SyncError: fetching from the platform failed, or the database
                transaction failed. The original exception is chained.
        """
        username = username.strip()
        if not username:
            raise SyncError("username must not be empty")

        client_factory = self._client_factories.get(platform)
        if client_factory is None:
            raise SyncError(f"Unsupported platform: {platform!r}")

        try:
            async with client_factory() as client:
                normalized_games = await client.fetch_games(username, max_games=max_games)
        except Exception as exc:
            raise SyncError(
                f"Failed to fetch games for {username!r} from {platform.value}"
            ) from exc

        try:
            player, _created = await self._players.get_or_create(platform, username)

            external_ids = [game.external_game_id for game in normalized_games]
            existing_ids = await self._games.existing_external_ids(
                player.id, platform, external_ids
            )
            new_games = [g for g in normalized_games if g.external_game_id not in existing_ids]
            imported = await self._games.add_many(new_games, player_id=player.id)

            synced_at = datetime.now(timezone.utc)
            await self._players.mark_synced(player, synced_at=synced_at)

            await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            raise SyncError(
                f"Failed to persist games for {username!r} on {platform.value}"
            ) from exc

        logger.info(
            "Synced %s/%s: fetched=%d imported=%d skipped=%d",
            platform.value,
            username,
            len(normalized_games),
            imported,
            len(normalized_games) - imported,
        )
        return SyncResult(
            player_id=player.id,
            platform=platform,
            username=player.username,
            fetched_games=len(normalized_games),
            imported_games=imported,
            skipped_games=len(normalized_games) - imported,
            last_sync_at=synced_at,
        )
