"""Integration tests for PlayerRepository and GameRepository against a real
PostgreSQL database. See tests/integration/README.md.

Uses random per-run identifiers rather than a cleanup fixture, so repeated
runs against a persistent dev database don't collide.
"""

import uuid
from datetime import datetime, timezone

import pytest

from chess_insights.domain.enums import ChessPlatform
from chess_insights.repositories.game import GameRepository
from chess_insights.repositories.player import PlayerRepository
from tests.conftest import make_normalized_game

pytestmark = pytest.mark.integration


def _unique_username() -> str:
    return f"itest-{uuid.uuid4().hex[:12]}"


# --- PlayerRepository -------------------------------------------------


async def test_get_by_platform_username_returns_none_for_unknown_player(session_factory) -> None:
    async with session_factory() as session:
        repo = PlayerRepository(session)
        found = await repo.get_by_platform_username(ChessPlatform.LICHESS, _unique_username())
        assert found is None


async def test_get_or_create_creates_a_player(session_factory) -> None:
    username = _unique_username()
    async with session_factory() as session:
        repo = PlayerRepository(session)
        player, created = await repo.get_or_create(ChessPlatform.LICHESS, username)
        await session.commit()

        assert created is True
        assert player.id is not None
        assert player.platform is ChessPlatform.LICHESS
        assert player.username == username.lower()


async def test_repeated_get_or_create_returns_the_same_player(session_factory) -> None:
    username = _unique_username()
    async with session_factory() as session:
        repo = PlayerRepository(session)
        first, first_created = await repo.get_or_create(ChessPlatform.LICHESS, username)
        await session.commit()
        first_id = first.id

    async with session_factory() as session:
        repo = PlayerRepository(session)
        second, second_created = await repo.get_or_create(ChessPlatform.LICHESS, username)
        await session.commit()

        assert first_created is True
        assert second_created is False
        assert second.id == first_id


async def test_username_case_is_normalized(session_factory) -> None:
    base_username = _unique_username()
    async with session_factory() as session:
        repo = PlayerRepository(session)
        created_player, _ = await repo.get_or_create(ChessPlatform.LICHESS, base_username.upper())
        await session.commit()
        created_id = created_player.id

    async with session_factory() as session:
        repo = PlayerRepository(session)
        # Different capitalization, same logical player.
        found = await repo.get_by_platform_username(ChessPlatform.LICHESS, base_username.lower())
        assert found is not None
        assert found.id == created_id

        reused, created = await repo.get_or_create(ChessPlatform.LICHESS, f" {base_username} ")
        assert created is False
        assert reused.id == created_id


async def test_same_username_on_different_platforms_are_distinct_players(
    session_factory,
) -> None:
    username = _unique_username()
    async with session_factory() as session:
        repo = PlayerRepository(session)
        lichess_player, _ = await repo.get_or_create(ChessPlatform.LICHESS, username)
        chess_com_player, _ = await repo.get_or_create(ChessPlatform.CHESS_COM, username)
        await session.commit()

        assert lichess_player.id != chess_com_player.id
        assert lichess_player.username == chess_com_player.username


async def test_mark_synced_updates_last_sync_at(session_factory) -> None:
    username = _unique_username()
    async with session_factory() as session:
        repo = PlayerRepository(session)
        player, _ = await repo.get_or_create(ChessPlatform.LICHESS, username)
        assert player.last_sync_at is None

        synced_at = datetime.now(timezone.utc)
        await repo.mark_synced(player, synced_at=synced_at)
        await session.commit()

    async with session_factory() as session:
        repo = PlayerRepository(session)
        reloaded = await repo.get_by_platform_username(ChessPlatform.LICHESS, username)
        assert reloaded.last_sync_at is not None
        assert reloaded.last_sync_at == synced_at


# --- GameRepository -----------------------------------------------------


async def _make_player(session_factory, *, platform: ChessPlatform = ChessPlatform.LICHESS) -> int:
    async with session_factory() as session:
        repo = PlayerRepository(session)
        player, _ = await repo.get_or_create(platform, _unique_username())
        await session.commit()
        return player.id


async def test_add_many_persists_games_with_correct_fields(session_factory) -> None:
    player_id = await _make_player(session_factory)
    game_id = f"game-{uuid.uuid4().hex[:12]}"
    normalized = make_normalized_game(external_game_id=game_id, opponent_username="rival")

    async with session_factory() as session:
        repo = GameRepository(session)
        imported = await repo.add_many([normalized], player_id=player_id)
        await session.commit()
        assert imported == 1

    async with session_factory() as session:
        repo = GameRepository(session)
        found = await repo.existing_external_ids(player_id, ChessPlatform.LICHESS, [game_id])
        assert found == {game_id}


async def test_exists_reflects_persisted_games(session_factory) -> None:
    player_id = await _make_player(session_factory)
    game_id = f"game-{uuid.uuid4().hex[:12]}"

    async with session_factory() as session:
        repo = GameRepository(session)
        assert await repo.exists(player_id, ChessPlatform.LICHESS, game_id) is False

        await repo.add_many([make_normalized_game(external_game_id=game_id)], player_id=player_id)
        await session.commit()

    async with session_factory() as session:
        repo = GameRepository(session)
        assert await repo.exists(player_id, ChessPlatform.LICHESS, game_id) is True


async def test_existing_external_ids_is_a_single_batch_query(session_factory) -> None:
    player_id = await _make_player(session_factory)
    ids = [f"game-{uuid.uuid4().hex[:12]}" for _ in range(3)]

    async with session_factory() as session:
        repo = GameRepository(session)
        await repo.add_many(
            [make_normalized_game(external_game_id=i) for i in ids[:2]], player_id=player_id
        )
        await session.commit()

    async with session_factory() as session:
        repo = GameRepository(session)
        found = await repo.existing_external_ids(player_id, ChessPlatform.LICHESS, ids)
        assert found == set(ids[:2])  # the 3rd id was never persisted


async def test_games_for_another_player_do_not_interfere(session_factory) -> None:
    player_a = await _make_player(session_factory)
    player_b = await _make_player(session_factory)
    shared_external_id = f"game-{uuid.uuid4().hex[:12]}"

    async with session_factory() as session:
        repo = GameRepository(session)
        await repo.add_many(
            [make_normalized_game(external_game_id=shared_external_id)], player_id=player_a
        )
        await session.commit()

    async with session_factory() as session:
        repo = GameRepository(session)
        assert await repo.exists(player_a, ChessPlatform.LICHESS, shared_external_id) is True
        assert await repo.exists(player_b, ChessPlatform.LICHESS, shared_external_id) is False


async def test_games_for_another_platform_do_not_interfere(session_factory) -> None:
    player_id = await _make_player(session_factory)
    shared_external_id = f"game-{uuid.uuid4().hex[:12]}"

    async with session_factory() as session:
        repo = GameRepository(session)
        await repo.add_many(
            [
                make_normalized_game(
                    platform=ChessPlatform.LICHESS, external_game_id=shared_external_id
                )
            ],
            player_id=player_id,
        )
        await session.commit()

    async with session_factory() as session:
        repo = GameRepository(session)
        assert await repo.exists(player_id, ChessPlatform.LICHESS, shared_external_id) is True
        assert await repo.exists(player_id, ChessPlatform.CHESS_COM, shared_external_id) is False
