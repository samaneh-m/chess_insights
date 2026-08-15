"""Tests for LichessClient: HTTP behavior only, via httpx.MockTransport.

No real network access -- every test constructs a client with a mock
transport that returns canned responses.
"""

import httpx
import pytest

from chess_insights.integrations.lichess import (
    LichessAPIError,
    LichessClient,
    LichessConnectionError,
    LichessRateLimitError,
    LichessUserNotFoundError,
)
from tests.conftest import load_fixture


def _client(handler) -> LichessClient:
    return LichessClient(transport=httpx.MockTransport(handler))


async def test_empty_username_rejected_without_a_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should not have made a request")

    async with _client(handler) as client:
        with pytest.raises(ValueError):
            await client.fetch_games("   ")


async def test_max_games_must_be_positive() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should not have made a request")

    async with _client(handler) as client:
        with pytest.raises(ValueError):
            await client.fetch_games("someone", max_games=0)


async def test_username_is_trimmed_and_used_in_request_path() -> None:
    seen_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_paths.append(request.url.path)
        return httpx.Response(200, text="")

    async with _client(handler) as client:
        await client.fetch_games("  someone  ")

    assert seen_paths == ["/api/games/user/someone"]


async def test_max_games_forwarded_as_query_param() -> None:
    seen_params = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_params.append(dict(request.url.params))
        return httpx.Response(200, text="")

    async with _client(handler) as client:
        await client.fetch_games("someone", max_games=5)

    assert seen_params[0]["max"] == "5"


async def test_max_games_none_omits_max_param() -> None:
    seen_params = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_params.append(dict(request.url.params))
        return httpx.Response(200, text="")

    async with _client(handler) as client:
        await client.fetch_games("someone", max_games=None)

    assert "max" not in seen_params[0]


async def test_successful_fetch_parses_and_skips_bad_lines() -> None:
    body = load_fixture("lichess", "games_response.ndjson")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=body)

    async with _client(handler) as client:
        games = await client.fetch_games("TrackedUser")

    # 4 lines: 1 valid, 1 broken JSON, 1 valid, 1 valid-JSON-but-missing-id.
    assert len(games) == 2
    assert {g.external_game_id for g in games} == {"aaaa1111", "cccc1111"}


async def test_404_raises_user_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    async with _client(handler) as client:
        with pytest.raises(LichessUserNotFoundError):
            await client.fetch_games("ghost")


async def test_429_raises_rate_limit_with_retry_after() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "12"}, text="Too Many Requests")

    async with _client(handler) as client:
        with pytest.raises(LichessRateLimitError) as exc_info:
            await client.fetch_games("someone")

    assert exc_info.value.retry_after == 12.0


async def test_429_without_retry_after_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="Too Many Requests")

    async with _client(handler) as client:
        with pytest.raises(LichessRateLimitError) as exc_info:
            await client.fetch_games("someone")

    assert exc_info.value.retry_after is None


async def test_500_raises_api_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    async with _client(handler) as client:
        with pytest.raises(LichessAPIError) as exc_info:
            await client.fetch_games("someone")

    assert exc_info.value.status_code == 500


async def test_timeout_raises_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    async with _client(handler) as client:
        with pytest.raises(LichessConnectionError):
            await client.fetch_games("someone")


async def test_network_failure_raises_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async with _client(handler) as client:
        with pytest.raises(LichessConnectionError):
            await client.fetch_games("someone")


async def test_context_manager_closes_underlying_client() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="")

    client = _client(handler)
    async with client:
        await client.fetch_games("someone")

    assert client._client.is_closed
