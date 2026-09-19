from typing import Any

from .analysis import (
    calculate_color_stats,
    calculate_duration_stats,
    calculate_hourly_stats,
    calculate_opening_stats,
    calculate_overall_stats,
    calculate_rating_trend,
)


def _format_stats(stats: dict[str, int | float | None]) -> str:
    rate = stats["win_rate"]
    rate_text = "N/A" if rate is None else f"{rate:.1f}%"
    return (
        f"games: {stats['total_games']}; wins: {stats['wins']}; "
        f"losses: {stats['losses']}; draws: {stats['draws']}; "
        f"unknown results: {stats['unknown_results']}; win rate: {rate_text}."
    )


def generate_performance_report(games: list[dict[str, Any]]) -> str:
    overall = calculate_overall_stats(games)
    lines = ["Performance summary", "", f"Overall: {_format_stats(overall)}"]
    if not games:
        lines.append("No games are available for analysis.")
        return "\n".join(lines) + "\n"

    lines.extend(["", "Piece color"])
    colors = calculate_color_stats(games)
    for color, stats in colors.items():
        lines.append(f"{color.title()}: {_format_stats(stats)}")

    lines.extend(["", "Openings (up to five most played ECO groups)"])
    openings = calculate_opening_stats(games)
    known_openings = sorted(
        (eco for eco in openings if eco != "unknown"),
        key=lambda eco: (-openings[eco]["total_games"], eco),
    )
    for eco in known_openings[:5]:
        lines.append(f"{eco}: {_format_stats(openings[eco])}")
    if not known_openings:
        lines.append("No known opening codes are available.")
    if len(known_openings) > 5:
        lines.append(f"Other opening groups not listed: {len(known_openings) - 5}.")
    if "unknown" in openings:
        lines.append(f"Unknown opening: {_format_stats(openings['unknown'])}")

    lines.extend(["", "Rating over time (rated games only, UTC)"])
    trends = calculate_rating_trend(games)
    for time_class, points in sorted(trends.items()):
        first = points[0]
        last = points[-1]
        if len(points) == 1:
            lines.append(
                f"{time_class.title()}: one rating record, {first['rating']} "
                f"on {first['date']:%Y-%m-%d}; not enough records for a trend."
            )
        else:
            change = last["rating"] - first["rating"]
            lines.append(
                f"{time_class.title()}: {first['rating']} on "
                f"{first['date']:%Y-%m-%d} to {last['rating']} on "
                f"{last['date']:%Y-%m-%d}; net change {change:+d} "
                f"across {len(points)} rating records."
            )
    if not trends:
        lines.append("No valid rated-game records are available.")

    lines.extend(["", "Performance by start hour (UTC)"])
    hourly = calculate_hourly_stats(games)
    for hour, stats in hourly.items():
        if stats["total_games"]:
            lines.append(f"{hour:02d}:00-{hour:02d}:59 UTC: {_format_stats(stats)}")
    timed_games = sum(stats["total_games"] for stats in hourly.values())
    if not timed_games:
        lines.append("No valid start times are available.")
    lines.append(f"Games without a valid start time: {len(games) - timed_games}.")

    lines.extend(["", "Performance by elapsed duration"])
    labels = {
        "short": "Short live games (under 5 minutes)",
        "medium": "Medium live games (5 to under 15 minutes)",
        "long": "Long live games (15 minutes or more)",
        "daily": "Daily games (separate from live games)",
        "unknown": "Unknown duration or game type",
    }
    for group, stats in calculate_duration_stats(games).items():
        lines.append(f"{labels[group]}: {_format_stats(stats)}")

    lines.extend(
        [
            "",
            (
                "Win rates include draws in the denominator and exclude unknown results. "
                "N/A means no known results."
            ),
            (
                "Compare percentages alongside game counts; small groups are less reliable. "
                "These statistics describe results, not the causes of wins or losses."
            ),
        ]
    )
    return "\n".join(lines) + "\n"
