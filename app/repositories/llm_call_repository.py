"""The only module allowed to write SQL for the llm_calls log."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.llm_call import LlmCall


class LlmCallRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
        self._session.add(
            LlmCall(
                model=model,
                query_text=query_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
            )
        )
        await self._session.commit()
