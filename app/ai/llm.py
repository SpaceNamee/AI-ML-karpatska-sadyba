"""LLM client abstraction (CLAUDE.md rule #8: no vendor SDK outside this file).

`OpenAiCompatClient` talks to any OpenAI-compatible `/chat/completions`
endpoint — Gemini, DeepSeek, and OpenAI itself all qualify, so switching
providers is three Settings values, not a code change. Anthropic's native API
uses a different request/response shape; it would need its own class behind
the same `LlmClient` Protocol, not a config change.

Tests use a hand-rolled fake (see tests/unit/test_rag_service.py) rather than
anything from this module, per CLAUDE.md rule #8 ("fake model in tests").
"""

from dataclasses import dataclass
from typing import Protocol

import openai

from app.core.config import settings
from app.core.exceptions import LlmNotConfiguredError


@dataclass(frozen=True)
class LlmResponse:
    text: str
    model: str
    input_tokens: int
    output_tokens: int


class LlmClient(Protocol):
    async def complete(self, *, system: str, user: str) -> LlmResponse: ...


class OpenAiCompatClient:
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self._client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    async def complete(self, *, system: str, user: str) -> LlmResponse:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        choice = response.choices[0]
        usage = response.usage
        return LlmResponse(
            text=choice.message.content or "",
            model=response.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
        )


def get_llm_client() -> LlmClient:
    """Raises LlmNotConfiguredError (-> 503) rather than letting the app fail
    to start: catalog/availability/upload/search all work with no LLM key.
    """
    if not settings.llm_api_key:
        raise LlmNotConfiguredError()
    return OpenAiCompatClient(settings.llm_api_key, settings.llm_base_url, settings.llm_model)
