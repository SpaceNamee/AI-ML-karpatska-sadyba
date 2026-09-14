from datetime import datetime
from typing import Self

from pydantic import BaseModel

from app.db.models.kb import IngestionStatus, KbDocument


class DocumentAccepted(BaseModel):
    """The `202 Accepted` body: enough to poll `GET /documents/{id}` afterward,
    never the processing result itself.
    """

    id: int
    status: IngestionStatus


class DocumentStatusRead(BaseModel):
    id: int
    title: str
    original_filename: str
    content_type: str
    status: IngestionStatus
    chunk_count: int
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    processing_seconds: float | None

    @classmethod
    def from_document(cls, document: KbDocument) -> Self:
        # `job` is `IngestionJob | None` in the type (a row could technically
        # lack one); every document created through this service always has
        # one (see DocumentRepository.create_pending), so this is a real
        # invariant, not user input.
        job = document.job
        assert job is not None

        processing_seconds = None
        if job.started_at is not None and job.finished_at is not None:
            processing_seconds = (job.finished_at - job.started_at).total_seconds()

        return cls(
            id=document.id,
            title=document.title,
            original_filename=document.original_filename,
            content_type=document.content_type,
            status=job.status,
            chunk_count=job.chunk_count,
            error=job.error,
            started_at=job.started_at,
            finished_at=job.finished_at,
            processing_seconds=processing_seconds,
        )
