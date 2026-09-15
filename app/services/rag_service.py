"""RAG answer generation. No HTTP, no SQL directly — CLAUDE.md rule #2.

Facts come only from SearchService's ranked chunks (the same retrieval Day 8's
POST /query uses); the model is instructed to answer only from them and to
say so, with a phone number, when it can't. This is the architectural
guardrail from CLAUDE.md's "three levels of hallucination defense":
architectural (facts only via tools/retrieval) and pipeline (every claim
traces to a source_id) are both here; the third — a measured eval set — is a
later sprint day, not this one.
"""

import time
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.ai.llm import LlmClient
from app.repositories.chunk_repository import SearchHit

SYSTEM_PROMPT = (
    "Ти — асистент садиби «Карпатська садиба» в Карпатах. Відповідай ТІЛЬКИ на "
    "основі наданого нижче контексту. Якщо в контексті немає відповіді на "
    "питання, чесно скажи, що не знаєш, і запропонуй зателефонувати "
    "господарю. Відповідай українською мовою, коротко і по суті, без "
    "вигаданих фактів — фраз чи цифр, яких немає в контексті."
)

_NO_CONTEXT_ANSWER = (
    "Не знайшла інформації за вашим запитом у наявних матеріалах. "
    "Будь ласка, зателефонуйте господарю для уточнення."
)


class SearchServiceLike(Protocol):
    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
        document_id: int | None = None,
        metadata_filter: dict[str, str] | None = None,
    ) -> Sequence[SearchHit]: ...


class LlmCallRepositoryLike(Protocol):
    async def record(
        self,
        *,
        model: str,
        query_text: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        cost_usd: Decimal,
    ) -> None: ...


@dataclass(frozen=True)
class RagAnswer:
    answer: str
    sources: Sequence[SearchHit]


def _build_user_prompt(query: str, hits: Sequence[SearchHit]) -> str:
    context = "\n\n".join(f"[{i + 1}] {hit.content}" for i, hit in enumerate(hits))
    return f"Контекст:\n{context}\n\nПитання гостя: {query}"


class RagService:
    def __init__(
        self,
        search: SearchServiceLike,
        llm: LlmClient,
        llm_calls: LlmCallRepositoryLike,
        *,
        price_per_million_input: Decimal,
        price_per_million_output: Decimal,
    ) -> None:
        self._search = search
        self._llm = llm
        self._llm_calls = llm_calls
        self._price_in = price_per_million_input
        self._price_out = price_per_million_output

    async def answer(self, query: str, *, limit: int = 5) -> RagAnswer:
        hits = await self._search.search(query, limit=limit)
        if not hits:
            # No retrieved context -> no LLM call. Nothing to ground an answer
            # in, and no reason to spend tokens finding that out a second time.
            return RagAnswer(answer=_NO_CONTEXT_ANSWER, sources=[])

        start = time.perf_counter()
        response = await self._llm.complete(
            system=SYSTEM_PROMPT, user=_build_user_prompt(query, hits)
        )
        latency_ms = round((time.perf_counter() - start) * 1000)

        cost = (
            Decimal(response.input_tokens) / Decimal(1_000_000) * self._price_in
            + Decimal(response.output_tokens) / Decimal(1_000_000) * self._price_out
        )
        await self._llm_calls.record(
            model=response.model,
            query_text=query,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
        )

        return RagAnswer(answer=response.text, sources=hits)
