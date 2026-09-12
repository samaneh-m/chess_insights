from typing import Any


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
