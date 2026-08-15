"""Application-owned, platform-agnostic schemas.

These are the objects platform integrations normalize external API
responses into -- external formats (Lichess, Chess.com, ...) never leak
past the integration layer.
"""

from chess_insights.schemas.game import NormalizedGame

__all__ = ["NormalizedGame"]
