FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1
# Use copy mode for cross-filesystem compatibility
ENV UV_LINK_MODE=copy

# Install dependencies first (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --group prod

# Copy application code
COPY . /app

# Final sync to install the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group prod

ENV WORKERS=2

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')"

CMD exec uv run gunicorn -w ${WORKERS} -b 0.0.0.0:5000 app:app
