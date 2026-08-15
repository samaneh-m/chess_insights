"""Turns a raw Lichess API game record into a ``NormalizedGame``.

Pure functions, no network I/O -- fully testable with plain fixture
dictionaries. Consumes records shaped like the Lichess "export games" NDJSON
format (see ``client.py`` for the exact request).
"""

from datetime import datetime, timezone
from typing import Any

from chess_insights.domain.enums import ChessPlatform, GameResult, GameSpeed, PlayerColor
from chess_insights.integrations.lichess.exceptions import LichessDataError
from chess_insights.schemas.game import NormalizedGame

# Games with no meaningful outcome: nothing was actually played. Skipped
# rather than mis-classified as a draw.
_SKIPPED_STATUSES = frozenset({"aborted", "noStart"})

# Lichess has no separate "ultra bullet" category in our GameSpeed enum;
# the closest fit is BULLET. Anything else unrecognized falls back to
# GameSpeed.UNKNOWN rather than raising.
_SPEED_MAP = {
    "ultraBullet": GameSpeed.BULLET,
    "bullet": GameSpeed.BULLET,
    "blitz": GameSpeed.BLITZ,
    "rapid": GameSpeed.RAPID,
    "classical": GameSpeed.CLASSICAL,
    "correspondence": GameSpeed.CORRESPONDENCE,
}


def normalize_game(record: dict[str, Any], *, tracked_username: str) -> NormalizedGame | None:
    """Normalize one Lichess game record.

    Returns ``None`` for games with no meaningful result (aborted / never
    started) -- these are intentionally skipped, not raised as errors.

    Raises:
        LichessDataError: the record is missing its id, or the tracked
            username isn't one of the two players.
    """
    game_id = record.get("id")
    if not game_id:
        raise LichessDataError("Lichess record is missing 'id'")

    if record.get("status") in _SKIPPED_STATUSES:
        return None

    players = record.get("players") or {}
    white = players.get("white") or {}
    black = players.get("black") or {}

    tracked_color = _find_tracked_color(white, black, tracked_username)
    if tracked_color is None:
        raise LichessDataError(
            f"Game {game_id!r} does not include tracked player {tracked_username!r}"
        )
    tracked_side, opponent_side = (
        (white, black) if tracked_color is PlayerColor.WHITE else (black, white)
    )

    created_at = record.get("createdAt")
    if not isinstance(created_at, int | float):
        raise LichessDataError(f"Game {game_id!r} is missing 'createdAt'")
    played_at = datetime.fromtimestamp(created_at / 1000, tz=timezone.utc)

    last_move_at = record.get("lastMoveAt")
    duration_seconds = None
    if isinstance(last_move_at, int | float):
        duration_seconds = max(0, round((last_move_at - created_at) / 1000))

    opening = record.get("opening") or {}
    moves = record.get("moves") or ""

    return NormalizedGame(
        platform=ChessPlatform.LICHESS,
        external_game_id=game_id,
        played_at=played_at,
        player_color=tracked_color,
        opponent_username=(opponent_side.get("user") or {}).get("name"),
        player_rating=tracked_side.get("rating"),
        opponent_rating=opponent_side.get("rating"),
        rating_change=tracked_side.get("ratingDiff"),
        result=_normalize_result(record.get("winner"), tracked_color),
        opening_name=opening.get("name"),
        opening_eco=opening.get("eco"),
        number_of_moves=len(moves.split()) if moves else None,
        duration_seconds=duration_seconds,
        time_control=_format_time_control(record.get("clock"), record.get("daysPerTurn")),
        game_speed=_SPEED_MAP.get(record.get("speed", ""), GameSpeed.UNKNOWN),
        rated=record.get("rated"),
        termination=record.get("status"),
        pgn=record.get("pgn"),
    )


def _find_tracked_color(
    white: dict[str, Any], black: dict[str, Any], tracked_username: str
) -> PlayerColor | None:
    target = tracked_username.casefold()
    white_name = (white.get("user") or {}).get("name", "")
    black_name = (black.get("user") or {}).get("name", "")
    if white_name.casefold() == target:
        return PlayerColor.WHITE
    if black_name.casefold() == target:
        return PlayerColor.BLACK
    return None


def _normalize_result(winner: str | None, tracked_color: PlayerColor) -> GameResult:
    """Result relative to the tracked player: win/loss/draw, never White's."""
    if winner is None:
        return GameResult.DRAW
    return GameResult.WIN if winner == tracked_color.value else GameResult.LOSS


def _format_time_control(clock: dict[str, Any] | None, days_per_turn: int | None) -> str | None:
    if clock:
        initial = clock.get("initial")
        increment = clock.get("increment")
        if initial is not None and increment is not None:
            return f"{initial}+{increment}"
    if days_per_turn:
        return f"{days_per_turn}d/move"
    return None
