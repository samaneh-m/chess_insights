"""Tests for analytics.openings.analyze_openings."""

from chess_insights.analytics.openings import analyze_openings
from chess_insights.domain.enums import GameResult
from tests.conftest import make_game_record


def test_grouping_by_opening() -> None:
    games = [
        make_game_record(opening_name="Italian Game", opening_eco="C50"),
        make_game_record(opening_name="Italian Game", opening_eco="C50"),
        make_game_record(opening_name="Sicilian Defense", opening_eco="B20"),
    ]
    analysis = analyze_openings(games, minimum_opening_games=1)
    by_name = {o.opening_name: o for o in analysis.openings}
    assert by_name["Italian Game"].stats.games == 2
    assert by_name["Sicilian Defense"].stats.games == 1


def test_win_rate_per_opening() -> None:
    games = [
        make_game_record(opening_name="Italian Game", result=GameResult.WIN),
        make_game_record(opening_name="Italian Game", result=GameResult.WIN),
        make_game_record(opening_name="Italian Game", result=GameResult.LOSS),
    ]
    analysis = analyze_openings(games, minimum_opening_games=1)
    italian = analysis.openings[0]
    assert italian.stats.games == 3
    assert italian.stats.win_rate == 66.67


def test_minimum_sample_threshold_excludes_low_sample_openings_from_ranking() -> None:
    games = [
        make_game_record(opening_name="Played Once", result=GameResult.WIN),
        *[make_game_record(opening_name="Played Thrice", result=GameResult.WIN) for _ in range(3)],
    ]
    analysis = analyze_openings(games, minimum_opening_games=3)
    # Both appear in the full list...
    assert {o.opening_name for o in analysis.openings} == {"Played Once", "Played Thrice"}
    # ...but only the one meeting the threshold is ranked.
    assert {o.opening_name for o in analysis.top_openings} == {"Played Thrice"}
    assert {o.opening_name for o in analysis.bottom_openings} == {"Played Thrice"}


def test_best_ranking_orders_by_win_rate_descending() -> None:
    games = [
        *[make_game_record(opening_name="Bad", result=GameResult.LOSS) for _ in range(3)],
        *[make_game_record(opening_name="Good", result=GameResult.WIN) for _ in range(3)],
    ]
    analysis = analyze_openings(games, minimum_opening_games=3)
    assert analysis.top_openings[0].opening_name == "Good"
    assert analysis.top_openings[-1].opening_name == "Bad"


def test_worst_ranking_orders_by_win_rate_ascending() -> None:
    games = [
        *[make_game_record(opening_name="Bad", result=GameResult.LOSS) for _ in range(3)],
        *[make_game_record(opening_name="Good", result=GameResult.WIN) for _ in range(3)],
    ]
    analysis = analyze_openings(games, minimum_opening_games=3)
    assert analysis.bottom_openings[0].opening_name == "Bad"
    assert analysis.bottom_openings[-1].opening_name == "Good"


def test_ties_break_by_sample_size_then_alphabetical_name() -> None:
    # Same win rate (100%) for all three; "Big" has more games so ranks
    # first among ties, then alphabetical among remaining equal-sized ties.
    games = [
        *[make_game_record(opening_name="Charlie", result=GameResult.WIN) for _ in range(3)],
        *[make_game_record(opening_name="Alpha", result=GameResult.WIN) for _ in range(3)],
        *[make_game_record(opening_name="Big", result=GameResult.WIN) for _ in range(5)],
    ]
    analysis = analyze_openings(games, minimum_opening_games=3)
    names_in_order = [o.opening_name for o in analysis.top_openings]
    assert names_in_order == ["Big", "Alpha", "Charlie"]


def test_ranking_is_deterministic_across_repeated_calls() -> None:
    games = [
        *[make_game_record(opening_name="Charlie", result=GameResult.WIN) for _ in range(3)],
        *[make_game_record(opening_name="Alpha", result=GameResult.WIN) for _ in range(3)],
    ]
    first = analyze_openings(games, minimum_opening_games=3)
    second = analyze_openings(games, minimum_opening_games=3)
    assert first.top_openings == second.top_openings
    assert first.bottom_openings == second.bottom_openings


def test_games_with_missing_opening_are_excluded_and_do_not_crash() -> None:
    games = [
        make_game_record(opening_name=None, opening_eco=None),
        make_game_record(opening_name="Italian Game", opening_eco="C50"),
    ]
    analysis = analyze_openings(games, minimum_opening_games=1)
    assert len(analysis.openings) == 1
    assert analysis.openings[0].opening_name == "Italian Game"


def test_eco_is_preserved_per_opening_group() -> None:
    games = [make_game_record(opening_name="Italian Game", opening_eco="C50")]
    analysis = analyze_openings(games, minimum_opening_games=1)
    assert analysis.openings[0].opening_eco == "C50"


def test_same_name_different_eco_are_not_merged() -> None:
    games = [
        make_game_record(opening_name="Sicilian Defense", opening_eco="B20"),
        make_game_record(opening_name="Sicilian Defense", opening_eco="B90"),
    ]
    analysis = analyze_openings(games, minimum_opening_games=1)
    assert len(analysis.openings) == 2
    ecos = {o.opening_eco for o in analysis.openings}
    assert ecos == {"B20", "B90"}


def test_top_and_bottom_limit_is_configurable() -> None:
    games = [
        make_game_record(opening_name=f"Opening {i}", result=GameResult.WIN) for i in range(10)
    ]
    analysis = analyze_openings(games, minimum_opening_games=1, limit=2)
    assert len(analysis.top_openings) == 2
    assert len(analysis.bottom_openings) == 2


def test_minimum_opening_games_defaults_to_three() -> None:
    games = [make_game_record(opening_name="Once")]
    analysis = analyze_openings(games)
    assert analysis.minimum_opening_games == 3
    assert analysis.top_openings == ()
