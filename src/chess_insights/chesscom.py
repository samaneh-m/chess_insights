import re
import time
from typing import Any
from urllib.parse import quote

import httpx

BASE_URL = "https://api.chess.com/pub/player"
MAX_ATTEMPTS = 3


class ChessComError(Exception):
    pass


def _get_json(client: httpx.Client, url: str) -> dict[str, Any]:
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = client.get(url)
        except httpx.RequestError as exc:
            if attempt == MAX_ATTEMPTS - 1:
                raise ChessComError("Could not connect to Chess.com.") from exc
        else:
            if response.status_code == 404:
                raise ChessComError("Chess.com user or game archive was not found.")
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == MAX_ATTEMPTS - 1:
                    raise ChessComError(
                        f"Chess.com is temporarily unavailable (HTTP "
                        f"{response.status_code}). Try again later."
                    )
            else:
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise ChessComError(
                        f"Chess.com returned HTTP {response.status_code}."
                    ) from exc
                try:
                    data = response.json()
                except ValueError as exc:
                    raise ChessComError("Chess.com returned invalid JSON.") from exc
                if not isinstance(data, dict):
                    raise ChessComError("Chess.com returned an unexpected response.")
                return data
        time.sleep(2**attempt)
    raise ChessComError("Could not retrieve Chess.com data.")


def get_player_games(username: str) -> list[dict[str, Any]]:
    username = username.strip().lower()
    if not username:
        raise ValueError("A Chess.com username is required.")

    player_url = f"{BASE_URL}/{quote(username, safe='')}"
    archive_pattern = re.compile(
        rf"{re.escape(BASE_URL)}/[^/]+/games/[0-9]{{4}}/(0[1-9]|1[0-2])"
    )
    games: list[dict[str, Any]] = []
    with httpx.Client(
        timeout=30.0,
        headers={"User-Agent": "chess_insights", "Accept": "application/json"},
    ) as client:
        data = _get_json(client, f"{player_url}/games/archives")
        archives = data.get("archives")
        if not isinstance(archives, list):
            raise ChessComError("Chess.com returned an invalid archive list.")
        for archive_url in archives:
            if not isinstance(archive_url, str) or not archive_pattern.fullmatch(
                archive_url
            ):
                raise ChessComError("Chess.com returned an invalid archive URL.")

        for archive_url in dict.fromkeys(archives):
            monthly_data = _get_json(client, archive_url)
            monthly_games = monthly_data.get("games")
            if not isinstance(monthly_games, list) or any(
                not isinstance(game, dict) for game in monthly_games
            ):
                raise ChessComError("Chess.com returned an invalid games list.")
            games.extend(monthly_games)
    return games
