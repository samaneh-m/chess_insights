"""Integration tests for GameSyncService: mocked platform clients + a real
PostgreSQL database. See tests/integration/README.md.

Network is never touched -- LichessClient/ChessComClient are replaced with
a small test double via GameSyncService's client_factories injection point.
"""

import uuid

import pytest
from sqlalchemy import select

from chess_insights.domain.enums import ChessPlatform
from chess_insights.repositories.player import PlayerRepository
from chess_insights.services.sync import GameSyncService, SyncError
from tests.conftest import make_normalized_game

pytestmark = pytest.mark.integration


def _unique_username() -> str:
    return f"itest-{uuid.uuid4().hex[:12]}"


class _FakeClient:
    """Test double satisfying ChessPlatformClient with canned games."""

    def __init__(self, games=(), *, error: Exception | None = None) -> None:
        self._games = list(games)
        self._error = error
        self.received_max_games: object = "not-called"

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None

    async def fetch_games(self, username: str, *, max_games=None):
        self.received_max_games = max_games
        if self._error is not None:
            raise self._error
        return self._games


def _factory_for(client: _FakeClient):
    return lambda: client


async def test_first_sync_imports_all_fetched_games(session_factory) -> None:
    username = _unique_username()
    games = [make_normalized_game(external_game_id=f"g{i}") for i in range(5)]
    client = _FakeClient(games)

    async with session_factory() as session:
        service = GameSyncService(
            session, client_factories={ChessPlatform.LICHESS: _factory_for(client)}
        )
        result = await service.sync_player(platform=ChessPlatform.LICHESS, username=username)

    assert result.fetched_games == 5
    assert result.imported_games == 5
    assert result.skipped_games == 0


async def test_second_identical_sync_imports_zero(session_factory) -> None:
    username = _unique_username()
    games = [make_normalized_game(external_game_id=f"g{i}") for i in range(5)]

    async with session_factory() as session:
        service = GameSyncService(
            session, client_factories={ChessPlatform.LICHESS: _factory_for(_FakeClient(games))}
        )
        first = await service.sync_player(platform=ChessPlatform.LICHESS, username=username)

    async with session_factory() as session:
        service = GameSyncService(
            session, client_factories={ChessPlatform.LICHESS: _factory_for(_FakeClient(games))}
        )
        second = await service.sync_player(platform=ChessPlatform.LICHESS, username=username)

    assert first.imported_games == 5
    assert second.fetched_games == 5
    assert second.imported_games == 0
    assert second.skipped_games == 5
    assert second.player_id == first.player_id


async def test_partially_overlapping_sync_imports_only_new_games(session_factory) -> None:
    username = _unique_username()
    first_batch = [make_normalized_game(external_game_id=f"g{i}") for i in range(5)]
    second_batch = first_batch + [make_normalized_game(external_game_id=f"g{i}") for i in (5, 6)]

    async with session_factory() as session:
        service = GameSyncService(
            session,
            client_factories={ChessPlatform.LICHESS: _factory_for(_FakeClient(first_batch))},
        )
        await service.sync_player(platform=ChessPlatform.LICHESS, username=username)

    async with session_factory() as session:
        service = GameSyncService(
            session,
            client_factories={ChessPlatform.LICHESS: _factory_for(_FakeClient(second_batch))},
        )
        result = await service.sync_player(platform=ChessPlatform.LICHESS, username=username)

    assert result.fetched_games == 7
    assert result.imported_games == 2
    assert result.skipped_games == 5


async def test_lichess_client_is_selected_for_lichess_platform(session_factory) -> None:
    client = _FakeClient([make_normalized_game()])
    async with session_factory() as session:
        service = GameSyncService(
            session, client_factories={ChessPlatform.LICHESS: _factory_for(client)}
        )
        await service.sync_player(platform=ChessPlatform.LICHESS, username=_unique_username())
    assert client.received_max_games != "not-called"


async def test_chess_com_client_is_selected_for_chess_com_platform(session_factory) -> None:
    client = _FakeClient([make_normalized_game(platform=ChessPlatform.CHESS_COM)])
    async with session_factory() as session:
        service = GameSyncService(
            session, client_factories={ChessPlatform.CHESS_COM: _factory_for(client)}
        )
        await service.sync_player(platform=ChessPlatform.CHESS_COM, username=_unique_username())
    assert client.received_max_games != "not-called"


async def test_max_games_forwarded_to_client_unchanged(session_factory) -> None:
    client = _FakeClient([])
    async with session_factory() as session:
        service = GameSyncService(
            session, client_factories={ChessPlatform.LICHESS: _factory_for(client)}
        )
        await service.sync_player(
            platform=ChessPlatform.LICHESS, username=_unique_username(), max_games=37
        )
    assert client.received_max_games == 37


async def test_max_games_defaults_to_none_when_unspecified(session_factory) -> None:
    client = _FakeClient([])
    async with session_factory() as session:
        service = GameSyncService(
            session, client_factories={ChessPlatform.LICHESS: _factory_for(client)}
        )
        await service.sync_player(platform=ChessPlatform.LICHESS, username=_unique_username())
    assert client.received_max_games is None


async def test_player_is_created_on_successful_sync(session_factory) -> None:
    username = _unique_username()
    client = _FakeClient([make_normalized_game()])

    async with session_factory() as session:
        service = GameSyncService(
            session, client_factories={ChessPlatform.LICHESS: _factory_for(client)}
        )
        result = await service.sync_player(platform=ChessPlatform.LICHESS, username=username)

    async with session_factory() as session:
        repo = PlayerRepository(session)
        player = await repo.get_by_platform_username(ChessPlatform.LICHESS, username)
        assert player is not None
        assert player.id == result.player_id


async def test_player_is_reused_on_later_sync(session_factory) -> None:
    username = _unique_username()

    async with session_factory() as session:
        service = GameSyncService(
            session,
            client_factories={
                ChessPlatform.LICHESS: _factory_for(_FakeClient([make_normalized_game()]))
            },
        )
        first = await service.sync_player(platform=ChessPlatform.LICHESS, username=username)

    async with session_factory() as session:
        service = GameSyncService(
            session,
            client_factories={
                ChessPlatform.LICHESS: _factory_for(
                    _FakeClient([make_normalized_game(external_game_id="g2")])
                )
            },
        )
        second = await service.sync_player(platform=ChessPlatform.LICHESS, username=username)

    assert first.player_id == second.player_id


async def test_last_sync_at_is_updated(session_factory) -> None:
    username = _unique_username()
    client = _FakeClient([make_normalized_game()])

    async with session_factory() as session:
        service = GameSyncService(
            session, client_factories={ChessPlatform.LICHESS: _factory_for(client)}
        )
        result = await service.sync_player(platform=ChessPlatform.LICHESS, username=username)

    async with session_factory() as session:
        repo = PlayerRepository(session)
        player = await repo.get_by_platform_username(ChessPlatform.LICHESS, username)
        assert player.last_sync_at == result.last_sync_at


async def test_api_failure_does_not_create_a_player(session_factory) -> None:
    username = _unique_username()
    client = _FakeClient([], error=RuntimeError("simulated platform failure"))

    async with session_factory() as session:
        service = GameSyncService(
            session, client_factories={ChessPlatform.LICHESS: _factory_for(client)}
        )
        with pytest.raises(SyncError):
            await service.sync_player(platform=ChessPlatform.LICHESS, username=username)

    async with session_factory() as session:
        repo = PlayerRepository(session)
        assert await repo.get_by_platform_username(ChessPlatform.LICHESS, username) is None


async def test_database_failure_rolls_back_and_creates_no_player(session_factory) -> None:
    username = _unique_username()
    # Violates ck_games_number_of_moves_nonneg -> IntegrityError on commit.
    bad_game = make_normalized_game(number_of_moves=-1)
    client = _FakeClient([bad_game])

    async with session_factory() as session:
        service = GameSyncService(
            session, client_factories={ChessPlatform.LICHESS: _factory_for(client)}
        )
        with pytest.raises(SyncError):
            await service.sync_player(platform=ChessPlatform.LICHESS, username=username)

    async with session_factory() as session:
        repo = PlayerRepository(session)
        # The whole transaction (including get_or_create's flush) rolled back.
        assert await repo.get_by_platform_username(ChessPlatform.LICHESS, username) is None


async def test_zero_game_account_sync_succeeds(session_factory) -> None:
    username = _unique_username()
    client = _FakeClient([])

    async with session_factory() as session:
        service = GameSyncService(
            session, client_factories={ChessPlatform.LICHESS: _factory_for(client)}
        )
        result = await service.sync_player(platform=ChessPlatform.LICHESS, username=username)

    assert result.fetched_games == 0
    assert result.imported_games == 0
    assert result.skipped_games == 0
    assert result.last_sync_at is not None

    async with session_factory() as session:
        repo = PlayerRepository(session)
        player = await repo.get_by_platform_username(ChessPlatform.LICHESS, username)
        assert player is not None
        assert player.last_sync_at is not None


async def test_same_external_id_for_different_players_both_persist(session_factory) -> None:
    username_a = _unique_username()
    username_b = _unique_username()
    shared_id = f"shared-{uuid.uuid4().hex[:12]}"

    async with session_factory() as session:
        service = GameSyncService(
            session,
            client_factories={
                ChessPlatform.LICHESS: _factory_for(
                    _FakeClient([make_normalized_game(external_game_id=shared_id)])
                )
            },
        )
        result_a = await service.sync_player(platform=ChessPlatform.LICHESS, username=username_a)

    async with session_factory() as session:
        service = GameSyncService(
            session,
            client_factories={
                ChessPlatform.LICHESS: _factory_for(
                    _FakeClient([make_normalized_game(external_game_id=shared_id)])
                )
            },
        )
        result_b = await service.sync_player(platform=ChessPlatform.LICHESS, username=username_b)

    # Uniqueness is (platform, external_game_id, player_id) -- different
    # players may have a game recorded under the same external id (e.g.
    # two tracked accounts that played each other), so both import cleanly.
    assert result_a.imported_games == 1
    assert result_b.imported_games == 1
    assert result_a.player_id != result_b.player_id


async def test_unsupported_platform_raises_sync_error(session_factory) -> None:
    async with session_factory() as session:
        service = GameSyncService(session, client_factories={})
        with pytest.raises(SyncError):
            await service.sync_player(platform=ChessPlatform.LICHESS, username=_unique_username())


async def test_blank_username_raises_sync_error(session_factory) -> None:
    async with session_factory() as session:
        service = GameSyncService(
            session, client_factories={ChessPlatform.LICHESS: _factory_for(_FakeClient([]))}
        )
        with pytest.raises(SyncError):
            await service.sync_player(platform=ChessPlatform.LICHESS, username="   ")


async def test_games_table_reflects_imported_rows(session_factory) -> None:
    from chess_insights.db.models.game import Game

    username = _unique_username()
    games = [make_normalized_game(external_game_id=f"gg{i}") for i in range(3)]

    async with session_factory() as session:
        service = GameSyncService(
            session, client_factories={ChessPlatform.LICHESS: _factory_for(_FakeClient(games))}
        )
        result = await service.sync_player(platform=ChessPlatform.LICHESS, username=username)

    async with session_factory() as session:
        rows = (
            (await session.execute(select(Game).where(Game.player_id == result.player_id)))
            .scalars()
            .all()
        )
        assert len(rows) == 3
