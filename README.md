# Chess Insights

A Python-based chess performance analytics tool that analyzes online chess
game history and helps players identify patterns, strengths, weaknesses, and
rating trends.

Chess Insights will eventually download chess games from Lichess and
Chess.com, analyze a player's performance, generate insights and
visualizations, store data in PostgreSQL, and provide a FastAPI + HTML
dashboard.

## Current Phase

**Phase 3 — Domain Models & Database Schema.** This phase adds the `Player`
and `Game` SQLAlchemy ORM models, their relationship, constraints and
indexes, and the first real Alembic migration. Phases 1-2's package/CLI/
FastAPI/Docker/PostgreSQL foundation is unchanged.

No platform integrations (Lichess/Chess.com clients), game import, or
analytics are implemented yet. See [Current Status](#current-status) below.

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
pytest-asyncio, httpx, Ruff).

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

## Test

```bash
uv run pytest
```

Runs fast unit tests only (database calls are mocked). Tests that require a
real PostgreSQL connection live in `tests/integration/` and are marked
`integration`; they're excluded by default. To run them:

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
├── domain/             # (reserved) pure Python domain models
├── services/           # (reserved) application/service layer
├── integrations/       # (reserved) external API clients
└── analytics/          # (reserved) chess performance analytics

migrations/             # Alembic environment (async) + revisions
alembic.ini
Dockerfile
docker-compose.yml
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

Not implemented yet:

- Lichess / Chess.com API integrations
- Game import / synchronization
- Chess performance analytics and insights
- Visualizations / HTML dashboard
