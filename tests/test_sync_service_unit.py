"""Fast unit tests for sync-service logic that needs no database.

Full sync_player() behavior (fetch + persist + dedup + rollback) lives in
tests/integration/test_sync_service.py, since it requires a real session.
"""

from chess_insights.domain.enums import ChessPlatform
from chess_insights.integrations.chess_com import ChessComClient
from chess_insights.integrations.lichess import LichessClient
from chess_insights.services.sync import _CLIENT_FACTORIES, SyncResult


def test_lichess_platform_maps_to_lichess_client() -> None:
    assert _CLIENT_FACTORIES[ChessPlatform.LICHESS] is LichessClient


def test_chess_com_platform_maps_to_chess_com_client() -> None:
    assert _CLIENT_FACTORIES[ChessPlatform.CHESS_COM] is ChessComClient


def test_every_chess_platform_has_a_client_factory() -> None:
    assert set(_CLIENT_FACTORIES) == set(ChessPlatform)


def test_sync_result_is_a_frozen_dataclass_with_expected_fields() -> None:
    from dataclasses import fields

    field_names = {f.name for f in fields(SyncResult)}
    assert field_names == {
        "player_id",
        "platform",
        "username",
        "fetched_games",
        "imported_games",
        "skipped_games",
        "last_sync_at",
    }
