"""Turns a raw Chess.com game record into a ``NormalizedGame``.

Pure functions, no network I/O -- fully testable with plain fixture
dictionaries. Consumes records shaped like one entry of a Chess.com
"monthly archive" games list (see ``client.py`` for the exact requests).

Chess.com's Published Data API differs from Lichess's export endpoint in
ways that shape several fields here:

- There is no single `id`; the documented stable identifier is `uuid`
  (falling back to the trailing segment of `url` if `uuid` is ever
  absent). See ``_external_game_id``.
- Each side has its own `result` string (`"win"`, `"checkmated"`,
  `"resigned"`, `"repetition"`, ...) instead of a shared `winner` field.
  See ``_classify_result``.
- Only `end_time` (epoch seconds) is available, not a start timestamp, so
  `played_at` is the game's *end* time and `duration_seconds` is always
  `None` (can't be derived without a start time -- not approximated from
  the time control, per design).
- There's no per-game rating-change field, so `rating_change` is always
  `None` rather than estimated.
- Opening name/ECO and ply count come from parsing the `pgn` field's
  headers and movetext (see ``_parse_pgn_metadata``), since Chess.com
  doesn't expose them as separate structured fields the way Lichess does.
"""

import io
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import unquote

import chess.pgn

from chess_insights.domain.enums import ChessPlatform, GameResult, GameSpeed, PlayerColor
from chess_insights.integrations.chess_com.exceptions import ChessComDataError
from chess_insights.schemas.game import NormalizedGame

logger = logging.getLogger(__name__)

# Per-player Chess.com "result" codes that mean *that side* drew. Anything
# else is either "win" or a loss reason (e.g. "checkmated", "resigned",
# "timeout", "abandoned") -- there's no need to enumerate every loss code:
# whatever isn't "win" and isn't a draw code is a loss for that side.
_DRAW_RESULTS = frozenset(
    {"agreed", "repetition", "stalemate", "insufficient", "50move", "timevsinsufficient"}
)

_SPEED_MAP = {
    "bullet": GameSpeed.BULLET,
    "blitz": GameSpeed.BLITZ,
    "rapid": GameSpeed.RAPID,
    "daily": GameSpeed.CORRESPONDENCE,
}


def normalize_game(record: dict[str, Any], *, tracked_username: str) -> NormalizedGame:
    """Normalize one Chess.com game record.

    Raises:
        ChessComDataError: the record has no usable id, is missing
            `end_time`/a tracked-side result, or the tracked username
            isn't one of the two players.
    """
    white = record.get("white") or {}
    black = record.get("black") or {}

    tracked_color = _find_tracked_color(white, black, tracked_username)
    if tracked_color is None:
        raise ChessComDataError(f"Game does not include tracked player {tracked_username!r}")
    tracked_side, opponent_side = (
        (white, black) if tracked_color is PlayerColor.WHITE else (black, white)
    )

    external_game_id = _external_game_id(record)
    if not external_game_id:
        raise ChessComDataError("Chess.com record has neither 'uuid' nor 'url'")

    end_time = record.get("end_time")
    if not isinstance(end_time, int | float):
        raise ChessComDataError(f"Game {external_game_id!r} is missing 'end_time'")
    played_at = datetime.fromtimestamp(end_time, tz=timezone.utc)

    tracked_result = tracked_side.get("result")
    if not tracked_result:
        raise ChessComDataError(f"Game {external_game_id!r} is missing tracked player's result")
    opponent_result = opponent_side.get("result")

    opening_eco, opening_name, number_of_moves = _parse_pgn_metadata(record.get("pgn"))

    return NormalizedGame(
        platform=ChessPlatform.CHESS_COM,
        external_game_id=external_game_id,
        played_at=played_at,
        player_color=tracked_color,
        opponent_username=opponent_side.get("username"),
        player_rating=tracked_side.get("rating"),
        opponent_rating=opponent_side.get("rating"),
        rating_change=None,
        result=_classify_result(tracked_result),
        opening_name=opening_name,
        opening_eco=opening_eco,
        number_of_moves=number_of_moves,
        duration_seconds=None,
        time_control=record.get("time_control"),
        game_speed=_SPEED_MAP.get(record.get("time_class", ""), GameSpeed.UNKNOWN),
        rated=record.get("rated"),
        termination=_termination(tracked_result, opponent_result),
        pgn=record.get("pgn"),
    )


def _find_tracked_color(
    white: dict[str, Any], black: dict[str, Any], tracked_username: str
) -> PlayerColor | None:
    target = tracked_username.casefold()
    white_username = (white.get("username") or "").casefold()
    black_username = (black.get("username") or "").casefold()
    if white_username == target:
        return PlayerColor.WHITE
    if black_username == target:
        return PlayerColor.BLACK
    return None


def _external_game_id(record: dict[str, Any]) -> str | None:
    """The documented stable identifier is `uuid`; `url`'s trailing segment
    is a fallback for the rare record that lacks it."""
    uuid = record.get("uuid")
    if uuid:
        return uuid
    url = record.get("url")
    if url:
        tail = url.rstrip("/").rsplit("/", 1)[-1]
        return tail or None
    return None


def _classify_result(result: str) -> GameResult:
    if result == "win":
        return GameResult.WIN
    if result in _DRAW_RESULTS:
        return GameResult.DRAW
    return GameResult.LOSS


def _termination(tracked_result: str, opponent_result: str | None) -> str:
    """The more descriptive of the two sides' result codes.

    Whichever side didn't "win" carries the informative reason (e.g.
    "checkmated", "resigned", "repetition"); "win" alone says nothing
    about *how* the game ended.
    """
    if tracked_result != "win":
        return tracked_result
    return opponent_result or tracked_result


def _parse_pgn_metadata(pgn: str | None) -> tuple[str | None, str | None, int | None]:
    """Best-effort (opening_eco, opening_name, number_of_moves) from PGN.

    number_of_moves is a ply count (half-moves), matching the Lichess
    normalizer's convention. Uses python-chess rather than hand-rolled
    token splitting: Chess.com's PGN includes `{[%clk ...]}` comments and
    "N... move" black-move numbering that make naive whitespace splitting
    unreliable.
    """
    if not pgn:
        return None, None, None
    try:
        game = chess.pgn.read_game(io.StringIO(pgn))
    except Exception:
        logger.warning("Failed to parse Chess.com PGN for opening/move-count", exc_info=True)
        return None, None, None
    if game is None:
        return None, None, None

    eco = game.headers.get("ECO") or None
    opening_name = _opening_name_from_eco_url(game.headers.get("ECOUrl"))
    number_of_moves = sum(1 for _ in game.mainline_moves())
    return eco, opening_name, number_of_moves


def _opening_name_from_eco_url(eco_url: str | None) -> str | None:
    if not eco_url:
        return None
    slug = eco_url.rstrip("/").rsplit("/", 1)[-1]
    if not slug:
        return None
    return unquote(slug).replace("-", " ")
