"""Minimal logging setup for the application."""

import logging

from chess_insights.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure the root logger based on application settings."""
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
