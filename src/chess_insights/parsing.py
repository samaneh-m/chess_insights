from io import StringIO
from itertools import islice
from typing import Any

import chess.pgn


def extract_color_and_opponent(
    game: dict[str, Any], username: str
) -> dict[str, str | None]:
    username = username.strip().casefold()
    if not username:
        raise ValueError("A Chess.com username is required.")

    players = {}
    for color in ("white", "black"):
        player = game.get(color)
        name = player.get("username") if isinstance(player, dict) else None
        players[color] = name.strip() or None if isinstance(name, str) else None

    matches = [
        color
        for color, name in players.items()
        if name is not None and name.casefold() == username
    ]
    if len(matches) != 1:
        raise ValueError("The user must match exactly one player in the game.")

    color = matches[0]
    opponent_color = "black" if color == "white" else "white"
    return {"color": color, "opponent": players[opponent_color]}


def extract_result(game: dict[str, Any], username: str) -> str | None:
    color = extract_color_and_opponent(game, username)["color"]
    result = game[color].get("result")
    if not isinstance(result, str):
        return None

    result = result.strip().casefold()
    if result == "win":
        return "win"
    if result in {
        "checkmated",
        "timeout",
        "resigned",
        "lose",
        "abandoned",
        "kingofthehill",
        "threecheck",
        "bughousepartnerlose",
    }:
        return "loss"
    if result in {
        "agreed",
        "repetition",
        "stalemate",
        "insufficient",
        "50move",
        "timevsinsufficient",
    }:
        return "draw"
    return None


def extract_rating(game: dict[str, Any], username: str) -> int | None:
    color = extract_color_and_opponent(game, username)["color"]
    rating = game[color].get("rating")
    if isinstance(rating, bool) or not isinstance(rating, int) or rating < 0:
        return None
    return rating


def extract_opening(game: dict[str, Any]) -> dict[str, str | list[str] | None]:
    opening: dict[str, str | list[str] | None] = {
        "opening_moves": None,
        "eco": None,
        "opening_name": None,
        "opening_url": None,
    }
    url = game.get("eco")
    if isinstance(url, str) and url.strip() not in {"", "?", "-"}:
        opening["opening_url"] = url.strip()

    pgn = game.get("pgn")
    if not isinstance(pgn, str) or not pgn.strip():
        return opening

    try:
        parsed_game = chess.pgn.read_game(StringIO(pgn))
    except (ValueError, IndexError):
        return opening
    if parsed_game is None:
        return opening

    for header, field in (
        ("ECO", "eco"),
        ("Opening", "opening_name"),
        ("ECOUrl", "opening_url"),
    ):
        value = parsed_game.headers.get(header)
        if isinstance(value, str) and value.strip() not in {"", "?", "-"}:
            opening[field] = value.strip()

    if parsed_game.errors:
        return opening

    board = parsed_game.board()
    moves = []
    for move in islice(parsed_game.mainline_moves(), 6):
        moves.append(board.san(move))
        board.push(move)
    opening["opening_moves"] = moves or None
    return opening
