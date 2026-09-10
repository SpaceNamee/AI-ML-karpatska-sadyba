# Single stage is fine for now: no compiled assets, and dev runs with a bind mount.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# UV_COMPILE_BYTECODE: precompile .pyc on install for faster container startup.
# UV_LINK_MODE=copy: silence the "can't hardlink across filesystems" warning in Docker.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependency layer: only busts when the lockfile changes, not on every code edit.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

EXPOSE 8000

# Compose overrides this with --reload for local dev.
CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
