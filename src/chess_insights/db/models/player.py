"""Player ORM model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from chess_insights.db.base import Base, enum_column, timestamp_column
from chess_insights.domain.enums import ChessPlatform

if TYPE_CHECKING:
    from chess_insights.db.models.game import Game


class Player(Base):
    """A tracked player on a chess platform (Lichess or Chess.com)."""

    __tablename__ = "players"
    __table_args__ = (
        UniqueConstraint("platform", "username", name="uq_players_platform_username"),
        Index("ix_players_platform_username", "platform", "username"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[ChessPlatform] = enum_column(ChessPlatform, name="chess_platform")
    username: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = timestamp_column()
    updated_at: Mapped[datetime] = timestamp_column(onupdate=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    games: Mapped[list["Game"]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"Player(id={self.id!r}, platform={self.platform!r}, username={self.username!r})"
