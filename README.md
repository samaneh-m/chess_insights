# Chess Insights

A Python-based chess performance analytics tool that analyzes online chess
game history and helps players identify patterns, strengths, weaknesses, and
rating trends.

Chess Insights will eventually download chess games from Lichess and
Chess.com, analyze a player's performance, generate insights and
visualizations, store data in PostgreSQL, and provide a FastAPI + HTML
dashboard.

## Current Phase

**Phase 1 — Project Foundation.** This phase establishes a clean, installable
Python application/package skeleton: project packaging, a CLI entry point, a
minimal FastAPI application with a health check, environment-based
configuration, tests, and linting.

No database, external chess-platform integrations, or analytics are
implemented yet. See [Planned Features](#planned-features) below.

## Requirements

- Python >= 3.10
- [uv](https://docs.astral.sh/uv/)

## Installation

```bash
uv venv
uv pip install -e .
```

To also install development dependencies (pytest, Ruff):

```bash
uv pip install -e ".[dev]"
```

## Run CLI

```bash
uv run -m chess_insights --help
```

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
- `GET /health` — application health check

## Test

```bash
uv run pytest
```

## Lint

```bash
uv run ruff check .
```

## Configuration

Configuration is read from environment variables (or a local `.env` file).
Copy `.env.example` to `.env` and adjust as needed:

```text
APP_NAME=Chess Insights
APP_ENV=development
HOST=127.0.0.1
PORT=8000
LOG_LEVEL=INFO
```

## Project Structure

```text
src/chess_insights/
├── __init__.py       # package version
├── __main__.py        # `python -m chess_insights` entry point
├── main.py            # CLI (argparse) and command dispatch
├── api/                # FastAPI interface layer (app factory, routes)
├── core/               # configuration and logging foundations
├── domain/             # (reserved) pure Python domain models
├── services/           # (reserved) application/service layer
├── integrations/       # (reserved) external API and persistence clients
└── analytics/          # (reserved) chess performance analytics
```

The `domain`, `services`, `integrations`, and `analytics` packages currently
only establish architectural boundaries for later phases — they contain no
implementation yet. The intended dependency direction is:

```text
CLI -> Application (API) -> Services / Domain -> Integrations / Persistence
```

Core chess analytics logic is intended to remain pure Python, independent of
FastAPI.

## Planned Features

Not yet implemented:

- Lichess game import
- Chess.com game import
- PostgreSQL persistence (SQLAlchemy, Alembic)
- Chess performance analytics
- Rating trend analysis
- Opening analysis
- Generated insights
- Visualizations
- HTML dashboard
