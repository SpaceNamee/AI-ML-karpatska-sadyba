"""The only module allowed to write SQL for chunk search."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.kb import KbChunk, KbDocument


@dataclass(frozen=True)
class SearchHit:
    document_id: int
    document_title: str
    position: int
    content: str
    score: float  # 1 - cosine distance: 1.0 is identical, higher is more similar


class ChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self,
        query_vector: list[float],
        limit: int,
        *,
        document_id: int | None = None,
        metadata_filter: dict[str, str] | None = None,
    ) -> Sequence[SearchHit]:
        distance = KbChunk.embedding.cosine_distance(query_vector)
        stmt = (
            select(
                KbChunk.document_id,
                KbDocument.title.label("document_title"),
                KbChunk.position,
                KbChunk.content,
                (1 - distance).label("score"),
            )
            .join(KbDocument, KbChunk.document_id == KbDocument.id)
            # A chunk with no embedding yet (still PROCESSING) has nothing to
            # rank by and would otherwise sort arbitrarily under `<=>`.
            .where(KbChunk.embedding.is_not(None))
            .order_by(distance)
            .limit(limit)
        )
        if document_id is not None:
            stmt = stmt.where(KbChunk.document_id == document_id)
        if metadata_filter:
            for key, value in metadata_filter.items():
                # ->> extracts the JSONB value as text; equality-only, no
                # metadata is populated yet (see KbChunk.meta), but the shape
                # is here for when chunking starts attaching real metadata.
                stmt = stmt.where(KbChunk.meta[key].astext == value)

        result = await self._session.execute(stmt)
        return [SearchHit(**row._mapping) for row in result]
