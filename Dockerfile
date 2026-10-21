# GigaLegs web app (docs/HOSTING.md). Data, athlete files, and the program are
# mounted at runtime from the host; nothing private is baked into the image.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /bin/uv

ENV PYTHONUNBUFFERED=1 UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 GIGALEGS_ROOT=/app
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
RUN uv sync --frozen --no-dev \
    && useradd --system --uid 1000 app && mkdir -p data && chown app data
USER app

EXPOSE 8000
HEALTHCHECK --interval=60s --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=4)"
CMD ["/app/.venv/bin/gigalegs", "serve", "--public", "--port", "8000"]
