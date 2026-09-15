"""Integration test infrastructure: a real Postgres database (never SQLite —
see CLAUDE.md: no EXCLUDE constraints, no pgvector), migrated once per test
session, with per-test transactional isolation for tests that stay on one
connection throughout.

Isolation strategy — two different patterns, used deliberately:

- `db_session` / `api_client`: everything happens on ONE held connection
  wrapped in an outer transaction. `join_transaction_mode="create_savepoint"`
  means a repository's own `session.commit()` calls (every repository in
  this codebase makes them) turn into SAVEPOINT release, not a real commit —
  so the outer transaction rolls back at teardown and nothing needs manual
  cleanup. Use this whenever the test and the code under test share one
  session/connection.
- Real commit + explicit cascade-delete cleanup: required whenever the code
  under test opens its *own* separate connection — the ARQ worker's
  `ingest_document` task does exactly this (SessionFactory() is production
  code, not a test artifact). A separate Postgres connection cannot see
  another connection's uncommitted work, so the savepoint trick doesn't
  apply; see test_ingest_cycle.py.
"""

import subprocess
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import anyio
import asyncpg
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.embeddings import load_model
from app.core.config import settings
from app.db.session import engine, get_session
from app.main import app

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _admin_dsn() -> str:
    """`settings.database_url`, minus the SQLAlchemy driver suffix asyncpg's
    own `connect()` doesn't take, pointed at the always-present `postgres`
    maintenance DB — CREATE DATABASE can't run against the DB being created.
    """
    parts = urlsplit(settings.database_url.replace("+asyncpg", ""))
    return urlunsplit(parts._replace(path="/postgres"))


def _test_db_name() -> str:
    return settings.database_url.rsplit("/", 1)[-1]


async def _ensure_test_database_exists() -> None:
    conn = await asyncpg.connect(_admin_dsn())
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", _test_db_name()
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{_test_db_name()}"')
    finally:
        await conn.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _migrated_test_database() -> None:
    await _ensure_test_database_exists()
    # A subprocess, not `alembic.command.upgrade()` in-process: it's the exact
    # command a developer runs by hand, so there's only one migration code
    # path to trust, not two that could quietly drift apart. Off-loaded to a
    # thread — this fixture is async, and subprocess.run() blocks.
    await anyio.to_thread.run_sync(
        lambda: subprocess.run(["alembic", "upgrade", "head"], check=True, cwd=_REPO_ROOT)
    )


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with engine.connect() as connection:
        trans = await connection.begin()
        session_factory = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        async with session_factory() as session:
            yield session
        await trans.rollback()


@pytest_asyncio.fixture
async def api_client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """An HTTP client whose `get_session` dependency is overridden to the
    *same* transactional `db_session` — so what the test asserts via direct
    queries matches what the endpoint wrote, and both roll back together.
    """

    async def _override() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = _override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture
def anonymous_client() -> AsyncClient:
    """A client with no session override, for tests that only need to check
    an unauthenticated status code and never touch the database.
    """
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest_asyncio.fixture(scope="session")
async def worker_ctx() -> dict[str, object]:
    """`ingest_document(ctx, document_id)`'s `ctx["embedding_model"]`, loaded
    the same way the real worker's `on_startup` loads it — tests that call
    the task function directly (bypassing ARQ) need to provide it themselves.
    """
    return {"embedding_model": load_model()}
