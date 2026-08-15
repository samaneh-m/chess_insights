"""Tests for analytics.game_length.analyze_game_length.

Buckets are ply counts: Short 0-39, Medium 40-79, Long 80+.
"""

import pytest

from chess_insights.analytics.game_length import analyze_game_length
from chess_insights.analytics.models import GameLengthBucket
from chess_insights.domain.enums import GameResult
from tests.conftest import make_game_record


@pytest.mark.parametrize(
    ("plies", "expected_bucket"),
    [
        (0, GameLengthBucket.SHORT),
        (39, GameLengthBucket.SHORT),
        (40, GameLengthBucket.MEDIUM),
        (79, GameLengthBucket.MEDIUM),
        (80, GameLengthBucket.LONG),
        (200, GameLengthBucket.LONG),
    ],
)
def test_bucket_boundaries(plies, expected_bucket) -> None:
    perf = analyze_game_length([make_game_record(number_of_moves=plies)])
    assert perf.by_bucket[expected_bucket].games == 1
    for bucket in GameLengthBucket:
        if bucket is not expected_bucket:
            assert perf.by_bucket[bucket].games == 0


def test_missing_ply_count_is_excluded_not_short() -> None:
    perf = analyze_game_length([make_game_record(number_of_moves=None)])
    for bucket in GameLengthBucket:
        assert perf.by_bucket[bucket].games == 0


def test_win_loss_draw_stats_by_length_bucket() -> None:
    games = [
        make_game_record(number_of_moves=10, result=GameResult.WIN),
        make_game_record(number_of_moves=20, result=GameResult.LOSS),
        make_game_record(number_of_moves=100, result=GameResult.DRAW),
    ]
    perf = analyze_game_length(games)
    assert perf.by_bucket[GameLengthBucket.SHORT].games == 2
    assert perf.by_bucket[GameLengthBucket.SHORT].wins == 1
    assert perf.by_bucket[GameLengthBucket.SHORT].losses == 1
    assert perf.by_bucket[GameLengthBucket.LONG].games == 1
    assert perf.by_bucket[GameLengthBucket.LONG].draws == 1
