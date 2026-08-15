"""Domain enums shared by ORM models and (eventually) services.

Pure Python -- no SQLAlchemy or FastAPI dependency, per the project's
layering: ``domain`` stays framework-agnostic.
"""

import enum


class ChessPlatform(str, enum.Enum):
    """Online chess platform a player/game record originates from."""

    LICHESS = "lichess"
    CHESS_COM = "chess_com"


class PlayerColor(str, enum.Enum):
    """The color a player had in a given game."""

    WHITE = "white"
    BLACK = "black"


class GameResult(str, enum.Enum):
    """Outcome of a game from the tracked player's perspective."""

    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"


class GameSpeed(str, enum.Enum):
    """Time-control category, matching common platform classifications."""

    BULLET = "bullet"
    BLITZ = "blitz"
    RAPID = "rapid"
    CLASSICAL = "classical"
    CORRESPONDENCE = "correspondence"
    UNKNOWN = "unknown"
