"""POST /documents -> ready, exercised through the real production pipeline:
the real KnowledgeBaseService (writes a real file), then the real ARQ task
function called directly rather than via Redis — CI has no separate worker
process to wait on, and the thing worth testing is the task's own logic
(parse -> chunk -> embed -> status transitions), not ARQ's transport.

Isolation note: this is the one test file that does NOT use the
db_session/api_client savepoint fixtures. `ingest_document` is production
code — it opens its own `SessionFactory()` connection, exactly like the real
worker process does, and a separate Postgres connection cannot see another
connection's uncommitted work. So this test commits for real and cleans up
explicitly afterward (a cascade delete of the KbDocument handles the job and
chunks too — see the ondelete="CASCADE" on both FKs).
"""

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.models.kb import IngestionStatus, KbChunk, KbDocument
from app.db.session import SessionFactory
from app.jobs.ingest_worker import ingest_document
from app.repositories.document_repository import DocumentRepository
from app.services.knowledge_base_service import KnowledgeBaseService


async def _get_document_with_job(session: AsyncSession, document_id: int) -> KbDocument | None:
    # session.get() doesn't take eager-load options the way a select()-based
    # query does; async SQLAlchemy never lazy-loads implicitly, so `.job`
    # needs to already be attached (same pattern as DocumentRepository).
    stmt = (
        select(KbDocument).options(selectinload(KbDocument.job)).where(KbDocument.id == document_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


class _NoopQueue:
    """The real KnowledgeBaseService enqueues after upload; this test calls
    the ingestion task itself directly right after, so the real enqueue
    would just be redundant work against Redis.
    """

    async def enqueue_ingest(self, document_id: int) -> None:
        return None


@pytest.fixture
def storage_dir(tmp_path: Path) -> Path:
    return tmp_path


async def test_upload_through_ingestion_reaches_ready_with_embedded_chunks(
    storage_dir: Path, worker_ctx: dict[str, object]
) -> None:
    document_id: int | None = None
    try:
        async with SessionFactory() as session:
            service = KnowledgeBaseService(
                DocumentRepository(session),
                storage_dir,
                settings.max_upload_size_bytes,
                _NoopQueue(),
            )
            document = await service.ingest_upload(
                filename="rules.txt",
                content="Заїзд з 15:00. Виїзд до 11:00. Тихі години з 00:00 до 05:00.".encode(),
                title="Integration test rules",
            )
            document_id = document.id

        # The real worker task — same function the ARQ process runs.
        await ingest_document(worker_ctx, document_id)

        async with SessionFactory() as session:
            refreshed = await _get_document_with_job(session, document_id)
            assert refreshed is not None
            assert refreshed.job is not None
            assert refreshed.job.status == IngestionStatus.READY
            assert refreshed.job.chunk_count == 1
            assert refreshed.job.error is None
            assert refreshed.job.started_at is not None
            assert refreshed.job.finished_at is not None

            chunks = (
                (await session.execute(select(KbChunk).where(KbChunk.document_id == document_id)))
                .scalars()
                .all()
            )
            assert len(chunks) == 1
            assert chunks[0].embedding is not None
            assert len(chunks[0].embedding) == settings.embedding_dimensions
    finally:
        if document_id is not None:
            async with SessionFactory() as session:
                doc = await session.get(KbDocument, document_id)
                if doc is not None:
                    await session.delete(doc)
                    await session.commit()


async def test_ingestion_of_an_unsupported_pdf_marks_the_job_failed(
    storage_dir: Path, worker_ctx: dict[str, object]
) -> None:
    document_id: int | None = None
    try:
        async with SessionFactory() as session:
            service = KnowledgeBaseService(
                DocumentRepository(session),
                storage_dir,
                settings.max_upload_size_bytes,
                _NoopQueue(),
            )
            document = await service.ingest_upload(
                filename="broken.pdf",
                content=b"this is not a real pdf file",
                title="Broken upload",
            )
            document_id = document.id

        await ingest_document(worker_ctx, document_id)

        async with SessionFactory() as session:
            refreshed = await _get_document_with_job(session, document_id)
            assert refreshed is not None
            assert refreshed.job is not None
            assert refreshed.job.status == IngestionStatus.FAILED
            assert refreshed.job.error  # the real pypdf error message, non-empty
    finally:
        if document_id is not None:
            async with SessionFactory() as session:
                doc = await session.get(KbDocument, document_id)
                if doc is not None:
                    await session.delete(doc)
                    await session.commit()
