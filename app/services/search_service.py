"""Semantic search over the knowledge base. No HTTP, no SQL — CLAUDE.md rule #2."""

from collections.abc import Sequence
from typing import Protocol

import anyio

from app.ai.embeddings import embed_texts, get_shared_model
from app.repositories.chunk_repository import SearchHit


class ChunkRepositoryLike(Protocol):
    async def search(
        self,
        query_vector: list[float],
        limit: int,
        *,
        document_id: int | None = None,
        metadata_filter: dict[str, str] | None = None,
    ) -> Sequence[SearchHit]: ...


class SearchService:
    def __init__(self, repository: ChunkRepositoryLike) -> None:
        self._repository = repository

    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
        document_id: int | None = None,
        metadata_filter: dict[str, str] | None = None,
    ) -> Sequence[SearchHit]:
        model = await get_shared_model()
        # embed_texts is CPU-bound and synchronous; keep it off the event loop
        # the same way the worker does, per app/ai/embeddings.py's docstring.
        vectors = await anyio.to_thread.run_sync(embed_texts, model, [query])
        return await self._repository.search(
            vectors[0], limit, document_id=document_id, metadata_filter=metadata_filter
        )
