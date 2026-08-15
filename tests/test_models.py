"""Schema/metadata tests for the Player and Game ORM models.

These inspect ``Base.metadata`` directly and never touch a database, so
they run without PostgreSQL.
"""

from chess_insights.db import models  # noqa: F401  (registers models on Base.metadata)
from chess_insights.db.base import Base
from chess_insights.db.models.game import Game
from chess_insights.db.models.player import Player
from chess_insights.domain.enums import ChessPlatform, GameResult, GameSpeed, PlayerColor


def test_base_metadata_contains_players_and_games() -> None:
    assert set(Base.metadata.tables) == {"players", "games"}


def test_players_table_name() -> None:
    assert Player.__tablename__ == "players"


def test_games_table_name() -> None:
    assert Game.__tablename__ == "games"


def test_player_platform_and_username_are_not_nullable() -> None:
    table = Player.__table__
    assert table.c.platform.nullable is False
    assert table.c.username.nullable is False


def test_player_last_sync_at_is_nullable() -> None:
    assert Player.__table__.c.last_sync_at.nullable is True


def test_player_has_unique_platform_username_constraint() -> None:
    unique_constraints = {
        tuple(col.name for col in c.columns)
        for c in Player.__table__.constraints
        if c.__class__.__name__ == "UniqueConstraint"
    }
    assert ("platform", "username") in unique_constraints


def test_game_has_duplicate_protection_constraint() -> None:
    unique_constraints = {
        tuple(col.name for col in c.columns)
        for c in Game.__table__.constraints
        if c.__class__.__name__ == "UniqueConstraint"
    }
    assert ("platform", "external_game_id", "player_id") in unique_constraints


def test_game_required_identity_fields_are_not_nullable() -> None:
    table = Game.__table__
    for column_name in ("player_id", "platform", "external_game_id", "played_at", "result"):
        assert table.c[column_name].nullable is False, column_name


def test_game_optional_external_metadata_is_nullable() -> None:
    table = Game.__table__
    optional_columns = (
        "player_color",
        "opponent_username",
        "player_rating",
        "opponent_rating",
        "rating_change",
        "opening_name",
        "opening_eco",
        "number_of_moves",
        "duration_seconds",
        "time_control",
        "game_speed",
        "rated",
        "termination",
        "pgn",
    )
    for column_name in optional_columns:
        assert table.c[column_name].nullable is True, column_name


def test_game_has_foreign_key_to_players() -> None:
    fk_targets = {fk.target_fullname for fk in Game.__table__.foreign_keys}
    assert "players.id" in fk_targets


def test_expected_indexes_exist() -> None:
    game_index_columns = {ix.name: [c.name for c in ix.columns] for ix in Game.__table__.indexes}
    assert game_index_columns["ix_games_player_id_played_at"] == ["player_id", "played_at"]
    assert "opening_name" in game_index_columns["ix_games_opening_name"]
    assert "game_speed" in game_index_columns["ix_games_game_speed"]

    player_index_columns = {
        ix.name: [c.name for c in ix.columns] for ix in Player.__table__.indexes
    }
    assert player_index_columns["ix_players_platform_username"] == ["platform", "username"]


def test_check_constraints_guard_nonnegative_counters() -> None:
    check_constraints = {
        c.name for c in Game.__table__.constraints if c.__class__.__name__ == "CheckConstraint"
    }
    assert "ck_games_number_of_moves_nonneg" in check_constraints
    assert "ck_games_duration_seconds_nonneg" in check_constraints


def test_player_games_relationship_configured() -> None:
    assert "games" in Player.__mapper__.relationships
    relationship = Player.__mapper__.relationships["games"]
    assert relationship.mapper.class_ is Game


def test_game_player_relationship_configured() -> None:
    assert "player" in Game.__mapper__.relationships
    relationship = Game.__mapper__.relationships["player"]
    assert relationship.mapper.class_ is Player


def test_chess_platform_enum_values() -> None:
    assert {member.value for member in ChessPlatform} == {"lichess", "chess_com"}


def test_player_color_enum_values() -> None:
    assert {member.value for member in PlayerColor} == {"white", "black"}


def test_game_result_enum_values() -> None:
    assert {member.value for member in GameResult} == {"win", "loss", "draw"}


def test_game_speed_enum_values() -> None:
    assert {member.value for member in GameSpeed} == {
        "bullet",
        "blitz",
        "rapid",
        "classical",
        "correspondence",
        "unknown",
    }
