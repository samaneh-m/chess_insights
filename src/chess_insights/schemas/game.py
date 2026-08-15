"""Platform-agnostic representation of a single normalized game.

Mirrors ``chess_insights.db.models.game.Game`` minus persistence-only
concerns (``id``, ``player_id``, ``created_at``, ``updated_at``) -- this is
what a platform integration produces and what a future sync/repository
layer will consume to build a ``Game`` row. Not an ORM object itself, and
not persisted anywhere yet.
"""

from dataclasses import dataclass
from datetime import datetime

from chess_insights.domain.enums import ChessPlatform, GameResult, GameSpeed, PlayerColor


@dataclass(frozen=True, slots=True)
class NormalizedGame:
    """A single game, normalized from a specific platform's API response."""

    platform: ChessPlatform
    external_game_id: str
    played_at: datetime

    player_color: PlayerColor | None
    opponent_username: str | None

    player_rating: int | None
    opponent_rating: int | None
    rating_change: int | None

    result: GameResult

    opening_name: str | None
    opening_eco: str | None

    number_of_moves: int | None
    duration_seconds: int | None

    time_control: str | None
    game_speed: GameSpeed

    rated: bool | None
    termination: str | None

    pgn: str | None
