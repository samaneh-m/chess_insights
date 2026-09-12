from typing import Any

from .chesscom import get_player_games
from .parsing import parse_game


def get_processed_games(username: str) -> list[dict[str, Any]]:
    games = get_player_games(username)
    return [parse_game(game, username) for game in games]
