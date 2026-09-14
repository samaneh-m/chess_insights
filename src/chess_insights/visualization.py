from datetime import UTC, datetime, timedelta
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.dates import AutoDateLocator, ConciseDateFormatter
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator


def plot_overall_results(
    stats: dict[str, int | float | None], output_path: str | Path
) -> Path:
    path = Path(output_path)
    if path.suffix.lower() != ".png":
        raise ValueError("The output file must have a .png extension.")

    counts = [stats[field] for field in ("wins", "losses", "draws")]
    if any(
        isinstance(count, bool) or not isinstance(count, int) or count < 0
        for count in counts
    ):
        raise ValueError("Result counts must be non-negative integers.")

    figure = Figure(figsize=(8, 5), facecolor="white")
    FigureCanvasAgg(figure)
    axes = figure.subplots()
    bars = axes.bar(
        ["Wins", "Losses", "Draws"],
        counts,
        color=["#27836B", "#C95757", "#64829E"],
        width=0.55,
    )
    axes.bar_label(bars, padding=5, fontsize=12)
    axes.set_title("Game results", fontsize=18, pad=18)
    axes.set_ylabel("Number of games")
    axes.set_ylim(0, max(1, max(counts) * 1.2))
    axes.yaxis.set_major_locator(MaxNLocator(integer=True))
    axes.set_axisbelow(True)
    axes.grid(axis="y", alpha=0.2)
    axes.spines[["top", "right"]].set_visible(False)
    figure.text(
        0.5,
        0.03,
        f"Unknown results excluded: {stats.get('unknown_results', 0)}",
        ha="center",
        color="#555555",
    )
    figure.tight_layout(rect=(0, 0.07, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, format="png", dpi=150)
    return path


def plot_rating_trend(
    trends: dict[str, list[dict[str, datetime | int]]], output_path: str | Path
) -> Path:
    path = Path(output_path)
    if path.suffix.lower() != ".png":
        raise ValueError("The output file must have a .png extension.")

    series = {}
    for time_class, points in trends.items():
        values = []
        for point in points:
            date = point["date"]
            rating = point["rating"]
            if not isinstance(date, datetime) or date.utcoffset() is None:
                raise ValueError("Rating dates must include a timezone.")
            if isinstance(rating, bool) or not isinstance(rating, int) or rating < 0:
                raise ValueError("Ratings must be non-negative integers.")
            values.append((date.astimezone(UTC), rating))
        if values:
            series[time_class] = sorted(values, key=lambda value: value[0])

    figure = Figure(figsize=(9, max(4, 3.5 * len(series))), facecolor="white")
    FigureCanvasAgg(figure)
    if not series:
        axes = figure.subplots()
        axes.set_title("Rating over time", fontsize=18, pad=18)
        axes.text(0.5, 0.5, "No rating data", transform=axes.transAxes, ha="center")
        axes.set_axis_off()
    else:
        panels = figure.subplots(nrows=len(series), squeeze=False)
        colors = {"bullet": "#64829E", "blitz": "#C95757", "rapid": "#27836B"}
        for axes, (time_class, values) in zip(
            panels[:, 0], series.items(), strict=True
        ):
            dates, ratings = zip(*values, strict=True)
            axes.plot(
                dates,
                ratings,
                marker="o",
                markersize=3,
                linewidth=1.5,
                color=colors.get(time_class, "#876AA6"),
            )
            locator = AutoDateLocator(tz=UTC, minticks=3, maxticks=6)
            axes.xaxis.set_major_locator(locator)
            axes.xaxis.set_major_formatter(ConciseDateFormatter(locator, tz=UTC))
            if dates[0] == dates[-1]:
                axes.set_xlim(
                    dates[0] - timedelta(hours=12), dates[0] + timedelta(hours=12)
                )
            axes.set_title(f"{time_class.title()} rating", fontsize=15, pad=12)
            axes.set_xlabel("Date (UTC)")
            axes.set_ylabel("Rating")
            axes.yaxis.set_major_locator(MaxNLocator(integer=True))
            axes.grid(alpha=0.2)
            axes.spines[["top", "right"]].set_visible(False)

    figure.tight_layout(pad=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, format="png", dpi=150)
    return path


def plot_opening_results(
    stats: dict[str, dict[str, int | float | None]], output_path: str | Path
) -> Path:
    path = Path(output_path)
    if path.suffix.lower() != ".png":
        raise ValueError("The output file must have a .png extension.")

    openings = sorted(stats, key=lambda eco: (eco == "unknown", eco))
    for eco in openings:
        count = stats[eco]["total_games"]
        rate = stats[eco]["win_rate"]
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("Game counts must be non-negative integers.")
        if rate is not None and (
            isinstance(rate, bool)
            or not isinstance(rate, (int, float))
            or not 0 <= rate <= 100
        ):
            raise ValueError("Win rates must be between 0 and 100, or None.")

    figure = Figure(figsize=(9, max(4, len(openings) * 0.45 + 2)), facecolor="white")
    FigureCanvasAgg(figure)
    axes = figure.subplots()
    labels = []
    for position, eco in enumerate(openings):
        rate = stats[eco]["win_rate"]
        name = "Unknown" if eco == "unknown" else eco
        labels.append(f"{name} (n={stats[eco]['total_games']})")
        if rate is None:
            axes.text(2, position, "N/A", va="center", color="#555555")
        else:
            axes.barh(
                position,
                rate,
                height=0.6,
                color="#64829E" if eco == "unknown" else "#27836B",
            )
            axes.text(rate + 2, position, f"{rate:.1f}%", va="center")

    axes.set_yticks(range(len(openings)), labels)
    axes.invert_yaxis()
    axes.set_xlim(0, 115)
    axes.set_xticks(range(0, 101, 20))
    axes.set_xlabel("Win rate (%)")
    axes.set_title("Win rate by opening", fontsize=18, pad=18)
    axes.set_axisbelow(True)
    axes.grid(axis="x", alpha=0.2)
    axes.spines[["top", "right"]].set_visible(False)
    if not openings:
        axes.text(0.5, 0.5, "No opening data", transform=axes.transAxes, ha="center")
    figure.text(
        0.5,
        0.03,
        "n = all games; win rate uses known results only. N/A = no known results.",
        ha="center",
        fontsize=9,
        color="#555555",
    )
    figure.tight_layout(rect=(0, 0.08, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, format="png", dpi=150)
    return path


def plot_color_results(
    stats: dict[str, dict[str, int | float | None]], output_path: str | Path
) -> Path:
    path = Path(output_path)
    if path.suffix.lower() != ".png":
        raise ValueError("The output file must have a .png extension.")

    fields = ("wins", "losses", "draws")
    counts = {
        color: [stats[color][field] for field in fields] for color in ("white", "black")
    }
    if any(
        isinstance(count, bool) or not isinstance(count, int) or count < 0
        for values in counts.values()
        for count in values
    ):
        raise ValueError("Result counts must be non-negative integers.")

    figure = Figure(figsize=(8, 5), facecolor="white")
    FigureCanvasAgg(figure)
    axes = figure.subplots()
    for index, (label, bar_color) in enumerate(
        (("Wins", "#27836B"), ("Losses", "#C95757"), ("Draws", "#64829E"))
    ):
        positions = [position + (index - 1) * 0.24 for position in range(2)]
        bars = axes.bar(
            positions,
            [counts["white"][index], counts["black"][index]],
            width=0.22,
            color=bar_color,
            label=label,
        )
        axes.bar_label(bars, padding=5, fontsize=11)

    maximum = max(count for values in counts.values() for count in values)
    axes.set_ylim(0, max(1, maximum * 1.25))
    axes.set_xticks([0, 1], ["Playing White", "Playing Black"])
    axes.set_title("Game results by piece color", fontsize=18, pad=18)
    axes.set_ylabel("Number of games")
    axes.yaxis.set_major_locator(MaxNLocator(integer=True))
    axes.set_axisbelow(True)
    axes.grid(axis="y", alpha=0.2)
    axes.spines[["top", "right"]].set_visible(False)
    axes.legend(ncols=3, loc="upper center", frameon=False)
    figure.text(
        0.5,
        0.03,
        f"Unknown results excluded: White {stats['white'].get('unknown_results', 0)}"
        f" | Black {stats['black'].get('unknown_results', 0)}",
        ha="center",
        color="#555555",
    )
    figure.tight_layout(rect=(0, 0.07, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, format="png", dpi=150)
    return path
