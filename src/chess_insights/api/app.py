"""Minimal FastAPI application for Chess Insights (Phase 1-2).

This module only defines the HTTP interface layer. Future phases will wire
in services and analytics; this layer should never contain that logic
itself. Building the app (``create_app``) never touches the database or
network — connections are only attempted when a request actually needs one.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from chess_insights.core.config import get_settings
from chess_insights.core.logging import configure_logging
from chess_insights.db.health import check_database_connection
from chess_insights.db.session import dispose_engine, get_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage database resources across the application's lifetime."""
    settings = get_settings()
    logger.info("%s starting up (env=%s)", settings.app_name, settings.app_env)
    yield
    await dispose_engine()
    logger.info("%s shutdown complete", settings.app_name)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    @app.get("/")
    def read_root() -> dict[str, str]:
        return {"name": settings.app_name, "status": "running"}

    @app.get("/health")
    async def health() -> JSONResponse:
        database_ok = await check_database_connection(get_engine())
        if database_ok:
            return JSONResponse({"status": "ok", "database": "ok"})
        return JSONResponse(
            {"status": "degraded", "database": "unavailable"},
            status_code=503,
        )

    logger.info("%s application created (env=%s)", settings.app_name, settings.app_env)
    return app


app = create_app()
