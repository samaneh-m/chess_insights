"""Command-line interface for Chess Insights."""

import argparse
import asyncio
import logging

import uvicorn

from chess_insights import __version__
from chess_insights.core.config import get_settings
from chess_insights.core.logging import configure_logging
from chess_insights.db.session import dispose_engine, get_sessionmaker
from chess_insights.domain.enums import ChessPlatform
from chess_insights.services.sync import GameSyncService, SyncError

logger = logging.getLogger(__name__)

# CLI-friendly platform spellings -> ChessPlatform. Derived from the enum
# itself (plus one friendly alias) rather than duplicating its values.
_PLATFORM_CHOICES = [platform.value for platform in ChessPlatform] + ["chess.com"]


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

    sync_parser = subparsers.add_parser(
        "sync", help="Fetch and store a player's games from a platform"
    )
    sync_parser.add_argument("platform", choices=_PLATFORM_CHOICES, help="Platform to sync from")
    sync_parser.add_argument("username", help="Platform username to sync")
    sync_parser.add_argument(
        "--max-games",
        type=int,
        default=100,
        help="Maximum number of games to fetch (default: 100)",
    )

    return parser


def run_serve(host: str, port: int) -> None:
    """Start the FastAPI application with Uvicorn."""
    settings = get_settings()
    configure_logging(settings)
    logger.info("Starting %s on %s:%s", settings.app_name, host, port)
    uvicorn.run("chess_insights.api.app:app", host=host, port=port)


def _parse_platform(value: str) -> ChessPlatform:
    """CLI platform spelling -> ``ChessPlatform`` (accepts "chess.com" too)."""
    return ChessPlatform(value.strip().lower().replace(".", "_"))


async def run_sync(platform_arg: str, username: str, max_games: int) -> int:
    """Run one synchronization and print a summary. Returns a process exit code."""
    settings = get_settings()
    configure_logging(settings)
    platform = _parse_platform(platform_arg)

    try:
        session_factory = get_sessionmaker()
        async with session_factory() as session:
            service = GameSyncService(session)
            try:
                result = await service.sync_player(
                    platform=platform, username=username, max_games=max_games
                )
            except SyncError as exc:
                logger.error("Sync failed: %s", exc)
                return 1
    finally:
        await dispose_engine()

    print(f"Platform: {result.platform.value}")
    print(f"Player: {result.username}")
    print(f"Fetched games: {result.fetched_games}")
    print(f"Imported games: {result.imported_games}")
    print(f"Skipped existing games: {result.skipped_games}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``chess_insights`` command-line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "serve":
        run_serve(host=args.host, port=args.port)
        return 0

    if args.command == "sync":
        return asyncio.run(run_sync(args.platform, args.username, args.max_games))

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
