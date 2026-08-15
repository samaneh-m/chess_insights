"""Game ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chess_insights.db.base import Base, enum_column, timestamp_column
from chess_insights.domain.enums import ChessPlatform, GameResult, GameSpeed, PlayerColor

if TYPE_CHECKING:
    from chess_insights.db.models.player import Player


class Game(Base):
    """A single game played by a tracked player.

    ``platform`` + ``external_game_id`` + ``player_id`` together guard
    against inserting the same synchronized game twice (see the unique
    constraint below).
    """

    __tablename__ = "games"
    __table_args__ = (
        UniqueConstraint(
            "platform",
            "external_game_id",
            "player_id",
            name="uq_games_platform_external_game_id_player",
        ),
        CheckConstraint(
            "number_of_moves IS NULL OR number_of_moves >= 0",
            name="ck_games_number_of_moves_nonneg",
        ),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_games_duration_seconds_nonneg",
        ),
        Index("ix_games_player_id_played_at", "player_id", "played_at"),
        Index("ix_games_opening_name", "opening_name"),
        Index("ix_games_game_speed", "game_speed"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )

    platform: Mapped[ChessPlatform] = enum_column(ChessPlatform, name="chess_platform")
    external_game_id: Mapped[str] = mapped_column(String(255), nullable=False)

    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    player_color: Mapped[PlayerColor | None] = enum_column(
        PlayerColor, name="player_color", nullable=True
    )
    opponent_username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    player_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opponent_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_change: Mapped[int | None] = mapped_column(Integer, nullable=True)

    result: Mapped[GameResult] = enum_column(GameResult, name="game_result")

    opening_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    opening_eco: Mapped[str | None] = mapped_column(String(10), nullable=True)

    number_of_moves: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    time_control: Mapped[str | None] = mapped_column(String(50), nullable=True)
    game_speed: Mapped[GameSpeed | None] = enum_column(GameSpeed, name="game_speed", nullable=True)

    rated: Mapped[bool | None] = mapped_column(nullable=True)
    termination: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pgn: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = timestamp_column(onupdate=True)

    player: Mapped["Player"] = relationship(back_populates="games")

    def __repr__(self) -> str:
        return (
            f"Game(id={self.id!r}, player_id={self.player_id!r}, "
            f"platform={self.platform!r}, external_game_id={self.external_game_id!r})"
        )
