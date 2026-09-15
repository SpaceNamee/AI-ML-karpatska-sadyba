"""The only module allowed to write SQL for the knowledge base."""

from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.kb import IngestionJob, IngestionStatus, KbDocument


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self) -> Select[tuple[KbDocument]]:
        return select(KbDocument).options(selectinload(KbDocument.job))

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

    async def get_by_id(self, document_id: int) -> KbDocument | None:
        stmt = self._base_query().where(KbDocument.id == document_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self) -> Sequence[KbDocument]:
        stmt = self._base_query().order_by(KbDocument.id.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()
