"""ORM model registry.

Importing this module registers all models on ``Base.metadata``. This is
the one place Alembic (and anything else that needs the full schema)
should import from, rather than relying on incidental import side effects.
"""

from chess_insights.db.models.game import Game
from chess_insights.db.models.player import Player

__all__ = ["Game", "Player"]
