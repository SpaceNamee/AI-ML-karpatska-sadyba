"""Embedding model loading and batch encoding.

Load once per process, never per call — constructing `SentenceTransformer`
reloads weights from disk (or downloads them, the first time) and takes on
the order of a minute; doing that per document or per query would make
everything unusably slow. `app/jobs/ingest_worker.py` (the worker) loads it
in `on_startup` and threads it through ARQ's `ctx`; `get_shared_model()`
below is the equivalent for the API process, which has no comparable
per-process startup hook it can rely on (see `app/jobs/queue.py`'s docstring
for why — the same ASGITransport-vs-lifespan lesson applies here).
"""

import asyncio

import anyio
from sentence_transformers import SentenceTransformer

from app.core.config import settings


def load_model() -> SentenceTransformer:
    model = SentenceTransformer(settings.embedding_model_name)
    actual_dim = model.get_embedding_dimension()
    if actual_dim != settings.embedding_dimensions:
        # Fail loudly at worker startup, not with a cryptic Postgres "expected
        # N dimensions, got M" error on the first chunk INSERT.
        raise RuntimeError(
            f"{settings.embedding_model_name} produces {actual_dim}-dimensional "
            f"vectors, but settings.embedding_dimensions={settings.embedding_dimensions} "
            f"(and the kb_chunks.embedding column is vector({settings.embedding_dimensions}))"
        )
    return model


def embed_texts(model: SentenceTransformer, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = model.encode(texts, batch_size=32, show_progress_bar=False)
    return [vector.tolist() for vector in vectors]


_model: SentenceTransformer | None = None
_model_lock = asyncio.Lock()


async def get_shared_model() -> SentenceTransformer:
    """Lazily-created, process-wide singleton — the async-safe equivalent of
    the worker's eager on_startup load, for a process (the API) with no
    reliable startup hook to put it in instead.
    """
    global _model
    if _model is None:
        async with _model_lock:
            if _model is None:  # re-check: another request may have won the race
                _model = await anyio.to_thread.run_sync(load_model)
    return _model
