"""HTTP client for the Chess.com Published Data API.

Responsible only for external communication (archive discovery, monthly
archive retrieval, status handling, timeouts) -- record-level parsing lives
in ``normalizer.py``. Chess.com exposes a player's games as monthly
archives rather than one paginated endpoint; this client hides that behind
a single ``fetch_games`` call matching ``LichessClient``'s shape.
"""

import logging
from types import TracebackType
from typing import Any

import httpx

from chess_insights import __version__
from chess_insights.integrations.chess_com.exceptions import (
    ChessComAPIError,
    ChessComConnectionError,
    ChessComDataError,
    ChessComRateLimitError,
    ChessComUserNotFoundError,
)
from chess_insights.integrations.chess_com.normalizer import normalize_game
from chess_insights.schemas.game import NormalizedGame

logger = logging.getLogger(__name__)

CHESS_COM_BASE_URL = "https://api.chess.com"

# Bounded so a stray call during development can't accidentally trigger a
# multi-year archive download. Pass max_games=None explicitly to fetch a
# user's full history.
DEFAULT_MAX_GAMES = 100
DEFAULT_TIMEOUT_SECONDS = 30.0

# Chess.com's API documentation asks integrations to identify themselves.
USER_AGENT = f"ChessInsights/{__version__}"


class ChessComClient:
    """Fetches and normalizes a Chess.com player's game history."""

    def __init__(
        self,
        *,
        base_url: str = CHESS_COM_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            timeout=timeout,
            transport=transport,
        )

    async def __aenter__(self) -> "ChessComClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        await self._client.aclose()

    async def fetch_games(
        self, username: str, *, max_games: int | None = DEFAULT_MAX_GAMES
    ) -> list[NormalizedGame]:
        """Fetch and normalize ``username``'s recent games, most recent first.

        Chess.com's archive list is chronological (oldest first); this
        walks it newest-month-first and stops as soon as ``max_games``
        games have been collected, so limited requests don't download a
        user's entire history. ``max_games=None`` fetches every archive.

        Raises:
            ValueError: ``username`` is blank, or ``max_games`` is not > 0.
            ChessComUserNotFoundError: the username doesn't exist.
            ChessComRateLimitError: Chess.com returned 429.
            ChessComAPIError: Chess.com returned another error status.
            ChessComConnectionError: a request timed out or failed at the
                network level.
            ChessComDataError: the archive list itself could not be parsed
                (individual malformed games/archives are logged and
                skipped instead, so one bad month doesn't lose the rest).
        """
        username = _validate_username(username)
        if max_games is not None and max_games <= 0:
            raise ValueError("max_games must be > 0 when provided")

        archive_urls = await self._fetch_archive_urls(username)
        archive_urls.reverse()  # newest month first

        games: list[NormalizedGame] = []
        for archive_url in archive_urls:
            if max_games is not None and len(games) >= max_games:
                break
            games.extend(await self._fetch_archive_games(archive_url, tracked_username=username))

        return games[:max_games] if max_games is not None else games

    async def _get(self, url: str) -> httpx.Response:
        try:
            return await self._client.get(url)
        except httpx.TimeoutException as exc:
            raise ChessComConnectionError(f"Timed out fetching {url!r}") from exc
        except httpx.HTTPError as exc:
            raise ChessComConnectionError(f"Failed to reach Chess.com for {url!r}") from exc

    async def _fetch_archive_urls(self, username: str) -> list[str]:
        response = await self._get(f"/pub/player/{username}/games/archives")
        _raise_for_status(response, username)
        try:
            data: Any = response.json()
            archives = data["archives"]
            if not isinstance(archives, list):
                raise TypeError("'archives' is not a list")
        except (ValueError, KeyError, TypeError) as exc:
            raise ChessComDataError(f"Malformed archive list response for {username!r}") from exc
        return list(archives)

    async def _fetch_archive_games(
        self, archive_url: str, *, tracked_username: str
    ) -> list[NormalizedGame]:
        response = await self._get(archive_url)
        _raise_for_status(response, tracked_username)
        try:
            data: Any = response.json()
            records = data["games"]
            if not isinstance(records, list):
                raise TypeError("'games' is not a list")
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning("Skipping malformed Chess.com archive %s: %s", archive_url, exc)
            return []

        games: list[NormalizedGame] = []
        for record in reversed(records):  # newest game in the month first
            try:
                games.append(normalize_game(record, tracked_username=tracked_username))
            except ChessComDataError as exc:
                logger.warning(
                    "Skipping unparseable Chess.com game for %s: %s", tracked_username, exc
                )
        return games


def _validate_username(username: str) -> str:
    username = username.strip()
    if not username:
        raise ValueError("username must not be empty")
    return username


def _raise_for_status(response: httpx.Response, username: str) -> None:
    if response.status_code == 404:
        raise ChessComUserNotFoundError(f"Chess.com user {username!r} not found")
    if response.status_code == 429:
        retry_after_header = response.headers.get("Retry-After")
        retry_after = float(retry_after_header) if retry_after_header else None
        raise ChessComRateLimitError("Rate limited by Chess.com", retry_after=retry_after)
    if response.status_code >= 400:
        raise ChessComAPIError(
            f"Chess.com API returned {response.status_code} for {username!r}",
            status_code=response.status_code,
        )
