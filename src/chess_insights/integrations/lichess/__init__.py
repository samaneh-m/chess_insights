"""Lichess platform integration: HTTP client + response normalization."""

from chess_insights.integrations.lichess.client import LichessClient
from chess_insights.integrations.lichess.exceptions import (
    LichessAPIError,
    LichessConnectionError,
    LichessDataError,
    LichessError,
    LichessRateLimitError,
    LichessUserNotFoundError,
)

__all__ = [
    "LichessAPIError",
    "LichessClient",
    "LichessConnectionError",
    "LichessDataError",
    "LichessError",
    "LichessRateLimitError",
    "LichessUserNotFoundError",
]
