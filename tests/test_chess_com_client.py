"""Tests for ChessComClient: HTTP behavior only, via httpx.MockTransport.

No real network access -- every test constructs a client with a mock
transport that returns canned responses.
"""

import json

import httpx
import pytest

from chess_insights.integrations.chess_com import (
    ChessComAPIError,
    ChessComClient,
    ChessComConnectionError,
    ChessComDataError,
    ChessComRateLimitError,
    ChessComUserNotFoundError,
)
from tests.conftest import load_fixture, load_json_fixture

ARCHIVES = load_json_fixture("chess_com", "archives.json")["archives"]
MONTHLY_ARCHIVE_BODY = load_fixture("chess_com", "monthly_archive.json")


def _client(handler) -> ChessComClient:
    return ChessComClient(transport=httpx.MockTransport(handler))


def _archives_response(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"archives": ARCHIVES})


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


async def test_archive_list_is_requested_first() -> None:
    requested_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        if request.url.path.endswith("/archives"):
            return _archives_response(request)
        return httpx.Response(200, text=MONTHLY_ARCHIVE_BODY)

    async with _client(handler) as client:
        await client.fetch_games("trackeduser", max_games=1)

    assert requested_paths[0] == "/pub/player/trackeduser/games/archives"


async def test_newest_archive_fetched_first() -> None:
    fetched_archive_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/archives"):
            return _archives_response(request)
        fetched_archive_paths.append(request.url.path)
        return httpx.Response(200, text=MONTHLY_ARCHIVE_BODY)

    async with _client(handler) as client:
        await client.fetch_games("trackeduser", max_games=1)

    # ARCHIVES is oldest-first (2023/11, 2023/12, 2024/01); newest (01) first.
    assert fetched_archive_paths[0].endswith("/2024/01")


async def test_stops_fetching_archives_once_max_games_reached() -> None:
    fetched_archive_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/archives"):
            return _archives_response(request)
        fetched_archive_paths.append(request.url.path)
        return httpx.Response(200, text=MONTHLY_ARCHIVE_BODY)

    # MONTHLY_ARCHIVE_BODY yields 2 valid games per archive (one is malformed
    # and skipped) -- max_games=1 should be satisfied after a single archive.
    async with _client(handler) as client:
        games = await client.fetch_games("trackeduser", max_games=1)

    assert len(games) == 1
    assert len(fetched_archive_paths) == 1


async def test_max_games_none_fetches_every_archive() -> None:
    fetched_archive_paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/archives"):
            return _archives_response(request)
        fetched_archive_paths.append(request.url.path)
        return httpx.Response(200, text=MONTHLY_ARCHIVE_BODY)

    async with _client(handler) as client:
        games = await client.fetch_games("trackeduser", max_games=None)

    assert len(fetched_archive_paths) == len(ARCHIVES)
    assert len(games) == 2 * len(ARCHIVES)  # 2 valid games per archive


async def test_malformed_individual_game_is_skipped() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/archives"):
            return _archives_response(request)
        return httpx.Response(200, text=MONTHLY_ARCHIVE_BODY)

    async with _client(handler) as client:
        games = await client.fetch_games("trackeduser", max_games=None)

    # Each archive has 3 records, 1 malformed (missing end_time) -> skipped.
    assert len(games) == 2 * len(ARCHIVES)


async def test_malformed_archive_response_is_skipped_not_fatal() -> None:
    call_count = {"archives": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/archives"):
            return _archives_response(request)
        call_count["archives"] += 1
        if call_count["archives"] == 1:
            return httpx.Response(200, text="not valid json{{{")
        return httpx.Response(200, text=MONTHLY_ARCHIVE_BODY)

    async with _client(handler) as client:
        games = await client.fetch_games("trackeduser", max_games=None)

    # 3 archives total: 1 malformed (0 games) + 2 good (2 games each) = 4.
    assert len(games) == 4


async def test_empty_game_history() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"archives": []})

    async with _client(handler) as client:
        games = await client.fetch_games("trackeduser")

    assert games == []


async def test_malformed_archive_list_raises_data_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": "shape"})

    async with _client(handler) as client:
        with pytest.raises(ChessComDataError):
            await client.fetch_games("trackeduser")


async def test_404_raises_user_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    async with _client(handler) as client:
        with pytest.raises(ChessComUserNotFoundError):
            await client.fetch_games("ghost")


async def test_429_raises_rate_limit_with_retry_after() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "7"}, text="Too Many Requests")

    async with _client(handler) as client:
        with pytest.raises(ChessComRateLimitError) as exc_info:
            await client.fetch_games("someone")

    assert exc_info.value.retry_after == 7.0


async def test_500_raises_api_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    async with _client(handler) as client:
        with pytest.raises(ChessComAPIError) as exc_info:
            await client.fetch_games("someone")

    assert exc_info.value.status_code == 500


async def test_timeout_raises_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    async with _client(handler) as client:
        with pytest.raises(ChessComConnectionError):
            await client.fetch_games("someone")


async def test_network_failure_raises_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async with _client(handler) as client:
        with pytest.raises(ChessComConnectionError):
            await client.fetch_games("someone")


async def test_user_agent_header_sent() -> None:
    seen_user_agents = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_user_agents.append(request.headers.get("User-Agent"))
        return httpx.Response(200, json={"archives": []})

    async with _client(handler) as client:
        await client.fetch_games("someone")

    assert seen_user_agents[0] is not None
    assert seen_user_agents[0].startswith("ChessInsights/")


async def test_context_manager_closes_underlying_client() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"archives": []})

    client = _client(handler)
    async with client:
        await client.fetch_games("someone")

    assert client._client.is_closed


async def test_single_archive_games_returned_newest_first() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/archives"):
            return httpx.Response(200, json={"archives": [ARCHIVES[-1]]})
        return httpx.Response(200, text=MONTHLY_ARCHIVE_BODY)

    async with _client(handler) as client:
        games = await client.fetch_games("trackeduser", max_games=None)

    ids = [g.external_game_id for g in games]
    # monthly_archive.json lists bbbb-0001 then bbbb-0002 (bbbb-0003 is
    # malformed/skipped); within-archive order should be newest-first.
    assert ids == ["bbbb-0002", "bbbb-0001"]


def test_archives_fixture_is_well_formed() -> None:
    assert isinstance(ARCHIVES, list) and len(ARCHIVES) == 3
    assert json.loads(MONTHLY_ARCHIVE_BODY)["games"]
