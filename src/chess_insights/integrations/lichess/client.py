"""HTTP client for the Lichess API.

Responsible only for external communication (requests, status handling,
timeouts) -- record-level parsing lives in ``normalizer.py``. Uses the
official "export games of a user" endpoint with the NDJSON response format,
so each game is one self-contained JSON object per line.
"""

import json
import logging
from types import TracebackType

import httpx

from chess_insights.integrations.lichess.exceptions import (
    LichessAPIError,
    LichessConnectionError,
    LichessDataError,
    LichessRateLimitError,
    LichessUserNotFoundError,
)
from chess_insights.integrations.lichess.normalizer import normalize_game
from chess_insights.schemas.game import NormalizedGame

logger = logging.getLogger(__name__)

LICHESS_BASE_URL = "https://lichess.org"

# Bounded so a stray call during development can't accidentally trigger a
# multi-thousand-game download. Pass max_games=None explicitly to fetch a
# user's full history.
DEFAULT_MAX_GAMES = 100
DEFAULT_TIMEOUT_SECONDS = 30.0


class LichessClient:
    """Fetches and normalizes a Lichess player's game history."""

    def __init__(
        self,
        *,
        base_url: str = LICHESS_BASE_URL,
        api_token: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Create a client.

        ``api_token`` is optional -- public game history works without one;
        a token only raises Lichess's rate limits. It is sent solely as an
        Authorization header and never logged. ``transport`` exists for
        tests (an ``httpx.MockTransport``); production code should leave it
        unset.
        """
        headers = {"Accept": "application/x-ndjson"}
        if api_token:
            headers["Authorization"] = f"Bearer {api_token}"
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    async def __aenter__(self) -> "LichessClient":
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

        Raises:
            ValueError: ``username`` is blank, or ``max_games`` is not > 0.
            LichessUserNotFoundError: the username doesn't exist.
            LichessRateLimitError: Lichess returned 429.
            LichessAPIError: Lichess returned another error status.
            LichessConnectionError: the request timed out or failed at the
                network level.

        Records that fail to parse are logged and skipped rather than
        aborting the whole fetch; a single malformed game shouldn't lose
        the rest of a user's history.
        """
        username = _validate_username(username)
        if max_games is not None and max_games <= 0:
            raise ValueError("max_games must be > 0 when provided")

        params: dict[str, str] = {
            "moves": "true",
            "opening": "true",
            "pgnInJson": "true",
            "clocks": "false",
            "evals": "false",
        }
        if max_games is not None:
            params["max"] = str(max_games)

        try:
            response = await self._client.get(f"/api/games/user/{username}", params=params)
        except httpx.TimeoutException as exc:
            raise LichessConnectionError(f"Timed out fetching games for {username!r}") from exc
        except httpx.HTTPError as exc:
            raise LichessConnectionError(f"Failed to reach Lichess for {username!r}") from exc

        _raise_for_status(response, username)
        return _parse_games(response.text, tracked_username=username)


def _validate_username(username: str) -> str:
    username = username.strip()
    if not username:
        raise ValueError("username must not be empty")
    return username


def _raise_for_status(response: httpx.Response, username: str) -> None:
    if response.status_code == 404:
        raise LichessUserNotFoundError(f"Lichess user {username!r} not found")
    if response.status_code == 429:
        retry_after_header = response.headers.get("Retry-After")
        retry_after = float(retry_after_header) if retry_after_header else None
        raise LichessRateLimitError("Rate limited by Lichess", retry_after=retry_after)
    if response.status_code >= 400:
        raise LichessAPIError(
            f"Lichess API returned {response.status_code} for {username!r}",
            status_code=response.status_code,
        )


def _parse_games(body: str, *, tracked_username: str) -> list[NormalizedGame]:
    games: list[NormalizedGame] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.warning(
                "Skipping malformed Lichess response line for %s: %s", tracked_username, exc
            )
            continue
        try:
            game = normalize_game(record, tracked_username=tracked_username)
        except LichessDataError as exc:
            logger.warning("Skipping unparseable Lichess game for %s: %s", tracked_username, exc)
            continue
        if game is not None:
            games.append(game)
    return games
