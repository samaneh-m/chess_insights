"""Common contract chess-platform client implementations conceptually satisfy.

A ``Protocol`` rather than an ABC: platform clients (``LichessClient``, and
later a Chess.com equivalent) implement this structurally, with no need to
inherit from a shared base class.
"""

from typing import Protocol

from chess_insights.schemas.game import NormalizedGame


class ChessPlatformClient(Protocol):
    """Fetches and normalizes a player's game history from one platform."""

    async def fetch_games(
        self, username: str, *, max_games: int | None = None
    ) -> list[NormalizedGame]:
        """Return normalized games for ``username``, most recent first.

        ``max_games`` limits how many games are requested; ``None`` means
        "as many as the platform will return in one call" -- concrete
        clients may still apply their own sane default.
        """
        ...
