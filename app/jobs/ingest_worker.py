"""ARQ worker: async knowledge-base ingestion (parse -> chunk -> KbChunk rows).

Run with:  uv run arq app.jobs.ingest_worker.WorkerSettings

No embeddings yet (a later sprint day) — a chunk's `embedding` column stays
NULL, and IngestionStatus.READY here means "chunked", not "search-ready".
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import anyio
import structlog
from arq.connections import RedisSettings
from sqlalchemy.orm import selectinload

from app.ai.rag.chunking import chunk_text
from app.ai.rag.parsing import parse_document
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.models.kb import IngestionStatus, KbChunk, KbDocument
from app.db.session import SessionFactory

logger = structlog.get_logger("app.jobs.ingest")


async def ingest_document(ctx: dict[str, Any], document_id: int) -> None:
    async with SessionFactory() as session:
        document = await session.get(
            KbDocument, document_id, options=[selectinload(KbDocument.job)]
        )
        if document is None or document.job is None:
            # Not retried (see WorkerSettings): a missing row means the
            # document was deleted after being queued, not a transient fault.
            logger.error("ingest_document_missing", document_id=document_id)
            return

        job = document.job
        job.status = IngestionStatus.PROCESSING
        job.started_at = datetime.now(UTC)
        await session.commit()

        try:
            text = await anyio.to_thread.run_sync(
                parse_document, Path(document.stored_path), document.content_type
            )
            chunks = chunk_text(text)
            for position, content in enumerate(chunks):
                session.add(KbChunk(document_id=document.id, position=position, content=content))

            job.status = IngestionStatus.READY
            job.chunk_count = len(chunks)
            job.error = None
            logger.info("ingest_document_ready", document_id=document_id, chunk_count=len(chunks))
        except Exception as exc:
            # Deliberately no automatic ARQ retry (see WorkerSettings): a parse
            # failure on a specific file is deterministic, not transient, and
            # would just fail identically on every retry.
            logger.exception("ingest_document_failed", document_id=document_id)
            job.status = IngestionStatus.FAILED
            job.error = str(exc)
        finally:
            job.finished_at = datetime.now(UTC)
            await session.commit()


async def _on_startup(ctx: dict[str, Any]) -> None:
    # The worker is its own process — app/main.py's configure_logging() call
    # never runs for it.
    configure_logging(debug=settings.debug)
    logger.info("worker_startup")


async def _on_shutdown(ctx: dict[str, Any]) -> None:
    logger.info("worker_shutdown")


class WorkerSettings:
    functions = (ingest_document,)
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = _on_startup
    on_shutdown = _on_shutdown
    max_tries = 1  # see the comment in ingest_document's except block
