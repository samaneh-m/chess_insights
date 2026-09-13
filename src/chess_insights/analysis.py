import re
from datetime import UTC, datetime
from typing import Any


def calculate_overall_stats(
    games: list[dict[str, Any]],
) -> dict[str, int | float | None]:
    wins = 0
    losses = 0
    draws = 0
    unknown = 0

    for game in games:
        result = game.get("result")
        if result == "win":
            wins += 1
        elif result == "loss":
            losses += 1
        elif result == "draw":
            draws += 1
        else:
            unknown += 1

    known_results = wins + losses + draws
    win_rate = wins / known_results * 100 if known_results else None
    return {
        "total_games": len(games),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "unknown_results": unknown,
        "win_rate": win_rate,
    }


def calculate_color_stats(
    games: list[dict[str, Any]],
) -> dict[str, dict[str, int | float | None]]:
    return {
        color: calculate_overall_stats(
            [game for game in games if game.get("color") == color]
        )
        for color in ("white", "black")
    }


def calculate_opening_stats(
    games: list[dict[str, Any]],
) -> dict[str, dict[str, int | float | None]]:
    openings: dict[str, list[dict[str, Any]]] = {}
    for game in games:
        eco = game.get("eco")
        eco = eco.strip().upper() if isinstance(eco, str) else ""
        if not re.fullmatch(r"[A-E][0-9]{2}", eco):
            eco = "unknown"
        openings.setdefault(eco, []).append(game)

    return {
        eco: calculate_overall_stats(opening_games)
        for eco, opening_games in openings.items()
    }


def calculate_rating_trend(
    games: list[dict[str, Any]],
) -> dict[str, list[dict[str, datetime | int]]]:
    trends: dict[str, list[dict[str, datetime | int]]] = {}
    for game in games:
        if game.get("rated") is not True:
            continue
        time_class = game.get("time_class")
        if time_class not in ("bullet", "blitz", "rapid", "daily"):
            continue
        rating = game.get("rating")
        if isinstance(rating, bool) or not isinstance(rating, int) or rating < 0:
            continue
        date = game.get("end_time")
        if not isinstance(date, datetime) or date.utcoffset() is None:
            continue
        trends.setdefault(time_class, []).append(
            {"date": date.astimezone(UTC), "rating": rating}
        )

    for points in trends.values():
        points.sort(key=lambda point: point["date"])
    return trends


def calculate_hourly_stats(
    games: list[dict[str, Any]],
) -> dict[int, dict[str, int | float | None]]:
    hourly_games: dict[int, list[dict[str, Any]]] = {hour: [] for hour in range(24)}
    for game in games:
        start = game.get("start_time")
        if not isinstance(start, datetime) or start.utcoffset() is None:
            continue
        hour = start.astimezone(UTC).hour
        hourly_games[hour].append(game)

    return {
        hour: calculate_overall_stats(group) for hour, group in hourly_games.items()
    }
