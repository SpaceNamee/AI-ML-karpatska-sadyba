from pydantic import BaseModel, Field

from app.repositories.chunk_repository import SearchHit


class QueryRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)
    document_id: int | None = None
    # Equality filters on kb_chunks.metadata (e.g. {"section": "rules"}). No
    # chunk carries real metadata yet — see ChunkRepository.search — but the
    # request shape is here for when ingestion starts attaching some.
    metadata: dict[str, str] | None = None


class SearchResultRead(BaseModel):
    score: float
    document_id: int
    document_title: str
    position: int
    snippet: str

    @classmethod
    def from_hit(cls, hit: SearchHit) -> "SearchResultRead":
        return cls(
            score=hit.score,
            document_id=hit.document_id,
            document_title=hit.document_title,
            position=hit.position,
            snippet=hit.content,
        )


class QueryResponse(BaseModel):
    results: list[SearchResultRead]
