"""Persistence operations for ORM models.

Repositories only talk to the database, through the ``AsyncSession`` they
are given -- no HTTP calls, no FastAPI, no analytics. They never commit or
roll back; the caller (a service) owns the transaction.
"""

from chess_insights.repositories.game import GameRepository
from chess_insights.repositories.player import PlayerRepository

__all__ = ["GameRepository", "PlayerRepository"]
