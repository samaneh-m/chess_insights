"""Player persistence operations.

No commits happen here -- the caller (a service) owns the transaction. The
one exception is ``get_or_create``'s internal ``flush()``, which assigns
the new row's ``id`` without ending the transaction, so callers can use it
immediately (e.g. as a foreign key) before deciding whether to commit.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from chess_insights.db.models.player import Player
from chess_insights.domain.enums import ChessPlatform


def canonicalize_username(username: str) -> str:
    """Normalize a platform username for storage and lookup.

    Strips whitespace and lowercases, so "Hikaru", "hikaru", and "HIKARU"
    all resolve to the same stored row. Because every write and read goes
    through this function, the existing ``UNIQUE(platform, username)``
    constraint enforces case-insensitive uniqueness with no schema change.
    """
    return username.strip().lower()


class PlayerRepository:
    """Persistence operations for ``Player``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_platform_username(
        self, platform: ChessPlatform, username: str
    ) -> Player | None:
        canonical = canonicalize_username(username)
        result = await self._session.execute(
            select(Player).where(Player.platform == platform, Player.username == canonical)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, platform: ChessPlatform, username: str) -> tuple[Player, bool]:
        """Return the existing player, or add and flush a new one.

        Returns ``(player, created)``. Not committed -- the caller decides
        the transaction boundary.
        """
        existing = await self.get_by_platform_username(platform, username)
        if existing is not None:
            return existing, False

        player = Player(platform=platform, username=canonicalize_username(username))
        self._session.add(player)
        await self._session.flush()
        return player, True

    async def mark_synced(self, player: Player, *, synced_at: datetime) -> None:
        """Set ``last_sync_at``. Not committed -- the caller decides the
        transaction boundary."""
        player.last_sync_at = synced_at
