"""Tests for analytics.time_control.analyze_speed."""

import pytest

from chess_insights.analytics.time_control import analyze_speed
from chess_insights.domain.enums import GameResult, GameSpeed
from tests.conftest import make_game_record


@pytest.mark.parametrize(
    "speed",
    [
        GameSpeed.BULLET,
        GameSpeed.BLITZ,
        GameSpeed.RAPID,
        GameSpeed.CLASSICAL,
        GameSpeed.CORRESPONDENCE,
        GameSpeed.UNKNOWN,
    ],
)
def test_each_known_speed_value_is_grouped_correctly(speed) -> None:
    perf = analyze_speed([make_game_record(game_speed=speed)])
    assert perf.by_speed[speed].games == 1
    for other in GameSpeed:
        if other is not speed:
            assert perf.by_speed[other].games == 0


def test_none_speed_is_grouped_under_unknown() -> None:
    perf = analyze_speed([make_game_record(game_speed=None)])
    assert perf.by_speed[GameSpeed.UNKNOWN].games == 1


def test_statistics_are_computed_per_speed() -> None:
    games = [
        make_game_record(game_speed=GameSpeed.BLITZ, result=GameResult.WIN),
        make_game_record(game_speed=GameSpeed.BLITZ, result=GameResult.LOSS),
        make_game_record(game_speed=GameSpeed.BULLET, result=GameResult.WIN),
    ]
    perf = analyze_speed(games)
    assert perf.by_speed[GameSpeed.BLITZ].games == 2
    assert perf.by_speed[GameSpeed.BLITZ].wins == 1
    assert perf.by_speed[GameSpeed.BULLET].games == 1
    assert perf.by_speed[GameSpeed.BULLET].wins == 1


def test_all_speed_values_present_in_output_even_with_zero_games() -> None:
    perf = analyze_speed([])
    assert set(perf.by_speed) == set(GameSpeed)
    for stats in perf.by_speed.values():
        assert stats.games == 0
