# Integration tests

Tests in this directory are marked `@pytest.mark.integration` and require a
reachable PostgreSQL database. They are excluded from the default
`uv run pytest` run (see `addopts` in `pyproject.toml`).

To run them:

```bash
docker compose up -d db
uv run pytest -m integration
```

They read the same `DATABASE_URL` / `POSTGRES_*` settings as the
application (see `.env.example`).
