"""External chess-platform integrations (Lichess, Chess.com, ...).

Each platform package exposes a client conceptually satisfying
``ChessPlatformClient`` (see ``chess_insights.integrations.base``) and
normalizes that platform's API responses into
``chess_insights.schemas.NormalizedGame``. Persistence (repositories, sync
services) is a later phase -- this layer only fetches and normalizes.
"""
