"""Command-line interface for Chess Insights."""

import argparse
import logging

import uvicorn

from chess_insights import __version__
from chess_insights.core.config import get_settings
from chess_insights.core.logging import configure_logging

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level CLI argument parser."""
    settings = get_settings()

    parser = argparse.ArgumentParser(
        prog="chess_insights",
        description="Chess Insights: chess performance analytics tool.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Run the FastAPI web application")
    serve_parser.add_argument("--host", default=settings.host, help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=settings.port, help="Port to bind to")

    return parser


def run_serve(host: str, port: int) -> None:
    """Start the FastAPI application with Uvicorn."""
    settings = get_settings()
    configure_logging(settings)
    logger.info("Starting %s on %s:%s", settings.app_name, host, port)
    uvicorn.run("chess_insights.api.app:app", host=host, port=port)


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``chess_insights`` command-line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "serve":
        run_serve(host=args.host, port=args.port)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
