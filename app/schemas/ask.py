from pydantic import BaseModel, Field

from app.schemas.search import SearchResultRead
from app.services.rag_service import RagAnswer


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=5, ge=1, le=20)


class AskResponse(BaseModel):
    answer: str
    sources: list[SearchResultRead]

    @classmethod
    def from_rag_answer(cls, result: RagAnswer) -> "AskResponse":
        return cls(
            answer=result.answer,
            sources=[SearchResultRead.from_hit(h) for h in result.sources],
        )
