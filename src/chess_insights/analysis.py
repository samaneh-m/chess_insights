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
