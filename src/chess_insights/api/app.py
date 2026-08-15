"""Minimal FastAPI application for Chess Insights (Phase 1).

This module only defines the HTTP interface layer. Future phases will wire
in services, persistence, and analytics; this layer should never contain
that logic itself.
"""

import logging

from fastapi import FastAPI

from chess_insights.core.config import get_settings
from chess_insights.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(title=settings.app_name)

    @app.get("/")
    def read_root() -> dict[str, str]:
        return {"name": settings.app_name, "status": "running"}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    logger.info("%s application created (env=%s)", settings.app_name, settings.app_env)
    return app


app = create_app()
