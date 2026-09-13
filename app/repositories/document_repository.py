"""The only module allowed to write SQL for the knowledge base."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.kb import IngestionJob, IngestionStatus, KbDocument


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_pending(
        self, *, title: str, original_filename: str, stored_path: str, content_type: str
    ) -> KbDocument:
        """Create the document row and its ingestion job in one transaction —
        a document without a job (or vice versa) should never be observable.
        """
        document = KbDocument(
            title=title,
            original_filename=original_filename,
            stored_path=stored_path,
            content_type=content_type,
            job=IngestionJob(status=IngestionStatus.PENDING),
        )
        self._session.add(document)
        await self._session.commit()
        return document
