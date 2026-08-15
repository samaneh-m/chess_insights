# Runtime image for the Chess Insights FastAPI application.
#
# This is an additional way to run the app; the project remains a normal
# installable Python package (see README.md for `uv pip install -e .`).
FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md LICENSE alembic.ini ./
COPY src ./src
COPY migrations ./migrations

RUN uv sync --frozen

EXPOSE 8000

CMD ["uv", "run", "-m", "chess_insights", "serve", "--host", "0.0.0.0", "--port", "8000"]
