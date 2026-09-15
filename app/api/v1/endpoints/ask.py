from fastapi import APIRouter

from app.api.deps import RagServiceDep
from app.schemas.ask import AskRequest, AskResponse

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
async def ask_knowledge_base(request: AskRequest, rag: RagServiceDep) -> AskResponse:
    """Public, unauthenticated, same as POST /query. Answers only from
    retrieved context (app/services/rag_service.py's system prompt enforces
    this) and cites the chunks it used. 503s with a clear message if no LLM
    provider is configured — see Settings.llm_api_key.
    """
    result = await rag.answer(request.query, limit=request.limit)
    return AskResponse.from_rag_answer(result)
