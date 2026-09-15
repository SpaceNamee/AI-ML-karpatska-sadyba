from collections.abc import Sequence
from decimal import Decimal

from app.ai.llm import LlmResponse
from app.repositories.chunk_repository import SearchHit
from app.services.rag_service import RagService


class FakeSearchService:
    def __init__(self, hits: Sequence[SearchHit]) -> None:
        self._hits = hits

    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
        document_id: int | None = None,
        metadata_filter: dict[str, str] | None = None,
    ) -> Sequence[SearchHit]:
        return self._hits


class FakeLlmClient:
    def __init__(self, text: str = "fake answer") -> None:
        self.calls: list[tuple[str, str]] = []
        self._text = text

    async def complete(self, *, system: str, user: str) -> LlmResponse:
        self.calls.append((system, user))
        return LlmResponse(text=self._text, model="fake-model", input_tokens=100, output_tokens=20)


class FakeLlmCallRepository:
    def __init__(self) -> None:
        self.recorded: list[dict[str, object]] = []

    async def record(
        self,
        *,
        model: str,
        query_text: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        cost_usd: Decimal,
    ) -> None:
        self.recorded.append(
            {
                "model": model,
                "query_text": query_text,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency_ms,
                "cost_usd": cost_usd,
            }
        )


def _hit(content: str = "chunk text") -> SearchHit:
    return SearchHit(document_id=1, document_title="Doc", position=0, content=content, score=0.9)


async def test_answer_calls_llm_and_records_the_call_when_hits_exist() -> None:
    llm = FakeLlmClient(text="Заїзд з 15:00.")
    llm_calls = FakeLlmCallRepository()
    service = RagService(
        FakeSearchService([_hit()]),
        llm,
        llm_calls,
        price_per_million_input=Decimal("1"),
        price_per_million_output=Decimal("5"),
    )

    result = await service.answer("коли заїзд?")

    assert result.answer == "Заїзд з 15:00."
    assert len(result.sources) == 1
    assert len(llm.calls) == 1
    system, user = llm.calls[0]
    assert "ТІЛЬКИ" in system  # "answer ONLY from context" is the core guardrail
    assert "коли заїзд?" in user
    assert "chunk text" in user  # the retrieved hit's content reached the prompt

    assert len(llm_calls.recorded) == 1
    recorded = llm_calls.recorded[0]
    # 100 input tokens @ $1/M + 20 output tokens @ $5/M = 0.0001 + 0.0001
    assert recorded["cost_usd"] == Decimal("100") / Decimal("1_000_000") * Decimal("1") + Decimal(
        "20"
    ) / Decimal("1_000_000") * Decimal("5")


async def test_answer_skips_the_llm_when_there_are_no_hits() -> None:
    llm = FakeLlmClient()
    llm_calls = FakeLlmCallRepository()
    service = RagService(
        FakeSearchService([]),
        llm,
        llm_calls,
        price_per_million_input=Decimal("1"),
        price_per_million_output=Decimal("5"),
    )

    result = await service.answer("щось невідоме")

    assert result.sources == []
    assert llm.calls == []  # no context -> no LLM call, no cost
    assert llm_calls.recorded == []
