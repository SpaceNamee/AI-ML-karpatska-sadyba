import os

# `app.core.config` builds its `Settings` at import time, so every required variable
# must exist in the environment *before* anything imports the app. `setdefault` means
# a real value from the shell (or CI) still wins.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://sadyba:sadyba@localhost:5432/sadyba_test",
)
os.environ.setdefault("ENVIRONMENT", "ci")

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """An HTTP client that talks to the app in-process, without a running server."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
