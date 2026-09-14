from fastapi import APIRouter

from app.api.deps import SearchServiceDep
from app.schemas.search import QueryRequest, QueryResponse, SearchResultRead

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query_knowledge_base(request: QueryRequest, search: SearchServiceDep) -> QueryResponse:
    """Public, unauthenticated — this is the guest-facing search a future RAG
    endpoint builds on top of. No LLM yet: this returns the raw ranked
    fragments, not a generated answer (see docs/sprint-praktyka-08-19-09.md's
    demo script, step 4 — the search is demoable entirely without one).
    """
    hits = await search.search(
        request.query,
        limit=request.limit,
        document_id=request.document_id,
        metadata_filter=request.metadata,
    )
    return QueryResponse(results=[SearchResultRead.from_hit(h) for h in hits])
