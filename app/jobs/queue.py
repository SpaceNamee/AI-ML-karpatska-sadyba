"""Enqueueing background jobs onto Redis via ARQ.

The Redis pool is a lazily-created, process-wide singleton — the same shape as
`app/db/session.py`'s engine, just async-created instead of eager, since ARQ's
`create_pool` has to await a connection. This deliberately avoids a FastAPI
`lifespan` hook: a hook only runs under a real ASGI server, not under the
`httpx.ASGITransport` this project's tests (and ad-hoc verification scripts)
use — a lesson learned the hard way earlier in this same sprint
(see the upload-directory fix in knowledge_base_service.py).
"""

import asyncio
from typing import Protocol

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings

from app.core.config import settings

_pool: ArqRedis | None = None
_pool_lock = asyncio.Lock()


async def _get_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:  # re-check: another task may have created it first
                _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _pool


class IngestQueueLike(Protocol):
    async def enqueue_ingest(self, document_id: int) -> None: ...


class ArqIngestQueue:
    async def enqueue_ingest(self, document_id: int) -> None:
        pool = await _get_pool()
        await pool.enqueue_job("ingest_document", document_id)
