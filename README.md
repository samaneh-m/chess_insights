# Chess Insights

A Python-based chess performance analytics tool that analyzes online chess
game history and helps players identify patterns, strengths, weaknesses, and
rating trends.

Chess Insights will eventually download chess games from Lichess and
Chess.com, analyze a player's performance, generate insights and
visualizations, store data in PostgreSQL, and provide a FastAPI + HTML
dashboard.

## Current Phase

**Phase 2 — Persistence & Container Foundation.** This phase adds PostgreSQL,
async SQLAlchemy 2.x, and Alembic infrastructure, plus Docker/Docker Compose
as an additional way to run the application. Phase 1's package/CLI/FastAPI
foundation is unchanged.

No chess domain models (`Player`, `Game`, ...), platform integrations, or
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

## Alembic

The project uses Alembic, configured to read its database URL from the
application's own settings (`chess_insights.core.config`) rather than
duplicating it in `alembic.ini`.

```bash
uv run alembic current
uv run alembic upgrade head
```

No domain models exist yet, so there are currently no migration revisions —
`migrations/versions/` is intentionally empty. Once Phase 3 introduces
`Player` and `Game` ORM models, the first real migration will be generated
with `uv run alembic revision --autogenerate`.

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

migrations/             # Alembic environment (async), no revisions yet
alembic.ini
Dockerfile
docker-compose.yml
```

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
- Alembic environment wired to application configuration
- Database-aware `/health` endpoint

Not implemented yet:

- Chess domain models (`Player`, `Game`, ...) and database schema
- Lichess / Chess.com API integrations
- Game import / synchronization
- Chess performance analytics and insights
- Visualizations / HTML dashboard
