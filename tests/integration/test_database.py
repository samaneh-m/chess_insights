"""Integration tests against a real PostgreSQL database.

Requires a reachable, migrated database (e.g. `docker compose up -d db` +
`uv run alembic upgrade head`) and is excluded from the default test run.
See tests/integration/README.md.

Uses random per-run identifiers rather than a cleanup fixture, so repeated
runs against a persistent dev database don't collide; the dev database is
disposable via `docker compose down -v`.
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from chess_insights.db.health import check_database_connection
from chess_insights.db.models import Game, Player
from chess_insights.db.session import get_engine
from chess_insights.domain.enums import ChessPlatform, GameResult, PlayerColor

pytestmark = pytest.mark.integration


@pytest.fixture
def session_factory():
    return async_sessionmaker(get_engine(), expire_on_commit=False)


def _unique_username() -> str:
    return f"itest-{uuid.uuid4().hex[:12]}"


async def test_database_health_check_succeeds_against_real_postgres() -> None:
    # Note: intentionally not exercised through the sync TestClient fixture
    # here -- it runs the ASGI app on its own event loop, which conflicts
    # with the session-scoped loop this module's cached engine expects.
    # /health's response shaping is covered by mocked tests in test_health.py.
    assert await check_database_connection(get_engine()) is True


async def test_player_can_be_inserted_and_game_can_reference_it(session_factory) -> None:
    username = _unique_username()

    async with session_factory() as session:
        player = Player(platform=ChessPlatform.LICHESS, username=username)
        session.add(player)
        await session.commit()
        player_id = player.id

    async with session_factory() as session:
        game = Game(
            player_id=player_id,
            platform=ChessPlatform.LICHESS,
            external_game_id=f"game-{uuid.uuid4().hex[:12]}",
            played_at=datetime.now(timezone.utc),
            result=GameResult.WIN,
            player_color=PlayerColor.WHITE,
        )
        session.add(game)
        await session.commit()

    async with session_factory() as session:
        result = await session.execute(select(Player).where(Player.id == player_id))
        loaded = result.scalar_one()
        await session.refresh(loaded, attribute_names=["games"])
        assert len(loaded.games) == 1
        assert loaded.games[0].player_id == player_id


async def test_duplicate_player_platform_username_is_rejected(session_factory) -> None:
    username = _unique_username()

    async with session_factory() as session:
        session.add(Player(platform=ChessPlatform.CHESS_COM, username=username))
        await session.commit()

    async with session_factory() as session:
        session.add(Player(platform=ChessPlatform.CHESS_COM, username=username))
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


async def test_duplicate_game_platform_external_id_player_is_rejected(session_factory) -> None:
    external_game_id = f"game-{uuid.uuid4().hex[:12]}"

    async with session_factory() as session:
        player = Player(platform=ChessPlatform.CHESS_COM, username=_unique_username())
        session.add(player)
        await session.commit()
        player_id = player.id

    async with session_factory() as session:
        session.add(
            Game(
                player_id=player_id,
                platform=ChessPlatform.CHESS_COM,
                external_game_id=external_game_id,
                played_at=datetime.now(timezone.utc),
                result=GameResult.DRAW,
            )
        )
        await session.commit()

    async with session_factory() as session:
        session.add(
            Game(
                player_id=player_id,
                platform=ChessPlatform.CHESS_COM,
                external_game_id=external_game_id,
                played_at=datetime.now(timezone.utc),
                result=GameResult.LOSS,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
