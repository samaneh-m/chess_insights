from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
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
