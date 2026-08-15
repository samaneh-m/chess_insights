# Chess Insights

A Python-based chess performance analytics tool that analyzes online chess
game history and helps players identify patterns, strengths, weaknesses, and
rating trends.

Chess Insights will eventually download chess games from Lichess and
Chess.com, analyze a player's performance, generate insights and
visualizations, store data in PostgreSQL, and provide a FastAPI + HTML
dashboard.

## Current Phase

**Phase 4 — Lichess Integration.** This phase adds a Lichess API client and
normalization layer: given a username, it fetches recent games from the
official Lichess API and turns them into platform-agnostic
`NormalizedGame` objects. Phases 1-3's package/CLI/FastAPI/Docker/
PostgreSQL/schema foundation is unchanged.

Fetched games are **not persisted** yet (no repositories/sync service), and
Chess.com is not implemented. See [Current Status](#current-status) below.

- Lichess integration: **implemented**
- Chess.com integration: not yet implemented
- Database persistence of imported games: not yet implemented
- Analytics: not yet implemented

## Requirements

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/)
- [Docker](https://docs.docker.com/get-docker/) + Docker Compose (optional,
  only needed to run PostgreSQL via containers)

## Local Python Development

```bash
uv venv
uv pip install -e ".[dev]"
```

This installs the package plus development dependencies (pytest,
pytest-asyncio, Ruff).

## Run CLI

```bash
uv run -m chess_insights --help
```

CLI help and package import never require a running database.

## Run web application

```bash
uv run -m chess_insights serve
```

Options:

```bash
uv run -m chess_insights serve --host 127.0.0.1 --port 8000
```

Once running, visit:

- `GET /` — basic application info
- `GET /health` — application + database health (see below)

## PostgreSQL / Docker Setup

The application also runs fully containerized, alongside a PostgreSQL
container:

```bash
docker compose up --build
```

This starts two services:

- `db` — PostgreSQL 16, with a named volume (`postgres_data`) so data
  survives container restarts, and a `pg_isready`-based healthcheck.
- `app` — the FastAPI application, built from the local `Dockerfile`. It
  waits for `db` to report healthy before starting, and connects to it via
  the Docker Compose network (`DATABASE_URL` is overridden to point at the
  `db` service instead of `localhost`).

Stop the containers:

```bash
docker compose down
```

Stop the containers **and delete the PostgreSQL data volume**:

```bash
docker compose down -v
```

Docker is an *additional* way to run Chess Insights — the project remains a
normal installable Python package (`uv pip install -e .` /
`uv run -m chess_insights ...`) independent of Docker.

## Environment Variables

Configuration is read from environment variables (or a local `.env` file).
Copy `.env.example` to `.env` and adjust as needed:

```text
APP_NAME=Chess Insights
APP_ENV=development
HOST=127.0.0.1
PORT=8000
LOG_LEVEL=INFO

POSTGRES_DB=chess_insights
POSTGRES_USER=chess
POSTGRES_PASSWORD=chess
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://chess:chess@localhost:5432/chess_insights

# Optional: only needed for higher Lichess API rate limits.
LICHESS_API_TOKEN=
```

`DATABASE_URL`, when set, takes precedence over the individual `POSTGRES_*`
fields. Docker Compose sets it automatically for the `app` service so it
reaches PostgreSQL at the `db` hostname. `.env` is git-ignored; only
`.env.example` is committed, and it contains development-only defaults, not
real secrets.

## Health Endpoint

`GET /health` performs a live `SELECT 1` against PostgreSQL through the
application's async SQLAlchemy engine:

- Database reachable → `200 {"status": "ok", "database": "ok"}`
- Database unreachable → `503 {"status": "degraded", "database": "unavailable"}`

The response never includes the connection string, credentials, or a raw
traceback; the underlying error is logged server-side instead.

## Database Schema

Two ORM models exist so far (`src/chess_insights/db/models/`):

- **`Player`** (`players`) — a tracked player on a platform. `platform` +
  `username` is unique (the same username may exist on both platforms).
- **`Game`** (`games`) — a single game played by a tracked player, with a
  `player_id` foreign key (`ON DELETE CASCADE`). External metadata that a
  platform may not provide (ratings, opening, duration, PGN, ...) is
  nullable; core identity fields (`player_id`, `platform`,
  `external_game_id`, `played_at`, `result`) are required. Duplicate-import
  protection is a unique constraint on `(platform, external_game_id,
  player_id)`. Indexes exist on `(player_id, played_at)`, `opening_name`,
  and `game_speed`.

Domain enums (`src/chess_insights/domain/enums.py`): `ChessPlatform`,
`PlayerColor`, `GameResult`, `GameSpeed`. Stored as `VARCHAR` + `CHECK`
(not native PostgreSQL `ENUM`) to keep future value changes a plain
migration instead of `ALTER TYPE`.

## Alembic

The project uses Alembic, configured to read its database URL from the
application's own settings (`chess_insights.core.config`) rather than
duplicating it in `alembic.ini`. `migrations/env.py` imports
`chess_insights.db.models` so `players`/`games` are registered on
`Base.metadata` for autogenerate.

```bash
uv run alembic current
uv run alembic upgrade head
```

The first migration (`create player and game tables`) creates both tables,
their constraints, and indexes, with a matching `downgrade()`. Inside
Docker, once a container is running:

```bash
docker compose exec app uv run alembic upgrade head
```

## Lichess Integration

`chess_insights.integrations.lichess.LichessClient` fetches and normalizes
a Lichess player's game history using the official
[export-games API](https://lichess.org/api#tag/Games/operation/apiGamesUser)
(NDJSON format) via `httpx.AsyncClient`. It does not persist anything —
persistence is a later phase.

```python
import asyncio

from chess_insights.integrations.lichess import LichessClient


async def main() -> None:
    async with LichessClient() as client:
        games = await client.fetch_games("username", max_games=10)

    for game in games:
        print(game.external_game_id, game.result.value, game.game_speed.value)


asyncio.run(main())
```

`fetch_games` returns `list[NormalizedGame]`
(`chess_insights.schemas.NormalizedGame`) — a platform-agnostic dataclass
mirroring the `Game` ORM model's fields. `max_games` defaults to 100 (to
avoid accidentally downloading a huge history); pass `max_games=None` to
fetch a user's entire history. Results/colors are normalized relative to
the requested username (`GameResult.WIN` always means *that user* won, not
White). Games that never really started (`aborted`/`noStart`) are skipped;
individual malformed records are logged and skipped rather than failing
the whole fetch.

Errors are raised as `LichessError` subclasses (`LichessUserNotFoundError`,
`LichessRateLimitError`, `LichessAPIError`, `LichessConnectionError`,
`LichessDataError`) — raw `httpx` exceptions never escape the client.

An optional `LICHESS_API_TOKEN` env var raises Lichess's rate limits;
public game history works fine without one.

## Test

```bash
uv run pytest
```

Runs fast unit tests only (database calls are mocked, Lichess HTTP calls
use `httpx.MockTransport` with fixtures under `tests/fixtures/lichess/` —
no real network access). Tests that require a real PostgreSQL connection
live in `tests/integration/` and are marked `integration`; they're
excluded by default. To run them:

```bash
docker compose up -d db
uv run pytest -m integration
```

## Lint

```bash
uv run ruff check .
uv run ruff format --check .
```

## Project Structure

```text
src/chess_insights/
├── __init__.py       # package version
├── __main__.py        # `python -m chess_insights` entry point
├── main.py            # CLI (argparse) and command dispatch
├── api/                # FastAPI interface layer (app factory, routes, lifespan)
├── core/               # configuration and logging foundations
├── db/                 # SQLAlchemy engine/session, declarative base, health check
├── domain/             # enums shared across the app (ChessPlatform, GameResult, ...)
├── services/           # (reserved) application/service layer
├── integrations/       # platform clients (Lichess) + common client contract
│   └── lichess/         # HTTP client, normalizer, exceptions
├── schemas/             # NormalizedGame -- platform-agnostic game representation
└── analytics/          # (reserved) chess performance analytics

migrations/             # Alembic environment (async) + revisions
alembic.ini
Dockerfile
docker-compose.yml

tests/fixtures/lichess/  # NDJSON/JSON fixtures used by mocked Lichess tests
```

`db/models/` (`player.py`, `game.py`, `__init__.py`) holds the ORM models.
Importing `chess_insights.db.models` registers them on `Base.metadata` —
this is the one place that import should happen from (e.g. Alembic's
`env.py`), rather than relying on incidental import side effects.

The `domain`, `services`, `integrations`, and `analytics` packages still only
establish architectural boundaries for later phases. `db/` is infrastructure
only — it contains no chess-specific tables. The intended dependency
direction is:

```text
CLI -> Application (API) -> Services / Domain -> Integrations / Persistence
```

Core chess analytics logic is intended to remain pure Python, independent of
FastAPI and SQLAlchemy.

## Current Status

Implemented:

- Installable Python package (`src` layout, CLI, FastAPI app)
- Docker + Docker Compose (`app` + `db` services)
- PostgreSQL with a persistent volume and healthcheck
- Async SQLAlchemy 2.x engine/session infrastructure and declarative `Base`
- Database-aware `/health` endpoint
- `Player` and `Game` ORM models: relationship, uniqueness/duplicate-import
  constraints, check constraints, indexes
- First real Alembic schema migration (`create player and game tables`)
- Lichess API client + normalization (`chess_insights.integrations.lichess`)

Not implemented yet:

- Chess.com API integration
- Persisting fetched games to the database (repositories / sync service)
- Chess performance analytics and insights
- Visualizations / HTML dashboard
