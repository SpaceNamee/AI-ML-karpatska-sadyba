"""A log line per LLM call: tokens, latency, cost (CLAUDE.md rule #7).

Immutable once written — like KbChunk, no TimestampMixin; just `created_at`.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TZDateTime


class LlmCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(primary_key=True)
    model: Mapped[str] = mapped_column(String(100))
    query_text: Mapped[str] = mapped_column(Text)
    input_tokens: Mapped[int]
    output_tokens: Mapped[int]
    latency_ms: Mapped[int]
    # numeric(12, 6): six decimal places because a single call often costs a
    # fraction of a cent — Decimal, per CLAUDE.md rule #4, never float.
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    created_at: Mapped[datetime] = mapped_column(TZDateTime, server_default=func.now())
