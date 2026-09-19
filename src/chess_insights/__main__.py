import argparse
import sys
from pathlib import Path

from .analysis import (
    calculate_color_stats,
    calculate_duration_stats,
    calculate_hourly_stats,
    calculate_opening_stats,
    calculate_overall_stats,
    calculate_rating_trend,
)
from .chesscom import ChessComError
from .processing import get_processed_games
from .reporting import generate_performance_report
from .visualization import (
    plot_color_results,
    plot_duration_results,
    plot_hourly_results,
    plot_opening_results,
    plot_overall_results,
    plot_rating_trend,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Analyze Chess.com games and save charts and a report in outputs/."
    )
    parser.add_argument("username", help="Chess.com username")
    args = parser.parse_args(argv)
    username = args.username.strip()
    if not username:
        parser.error("A Chess.com username is required.")

    print(f"Fetching games for {username}...", flush=True)
    try:
        games = get_processed_games(username)
        print(f"Total games: {len(games)}", flush=True)
        print("Generating charts and report...", flush=True)
        output_dir = Path("outputs")
        charts = (
            (calculate_overall_stats, plot_overall_results, "overall_results.png"),
            (calculate_color_stats, plot_color_results, "color_results.png"),
            (calculate_opening_stats, plot_opening_results, "opening_results.png"),
            (calculate_rating_trend, plot_rating_trend, "rating_trend.png"),
            (calculate_hourly_stats, plot_hourly_results, "hourly_results.png"),
            (calculate_duration_stats, plot_duration_results, "duration_results.png"),
        )
        for analyze, plot, filename in charts:
            plot(analyze(games), output_dir / filename)
        report = f"Chess.com player: {username}\n\n{generate_performance_report(games)}"
        (output_dir / "report.txt").write_text(report, encoding="utf-8")
    except (ChessComError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Operation cancelled.", file=sys.stderr)
        return 130

    print(f"Saved six PNG charts and report.txt to {output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
