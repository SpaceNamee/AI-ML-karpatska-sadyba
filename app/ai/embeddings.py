"""Embedding model loading and batch encoding.

Load once per worker process (see `app/jobs/ingest_worker.py`'s on_startup),
never per job — constructing `SentenceTransformer` reloads weights from disk
(or downloads them, the first time) and takes on the order of a minute; doing
that per document would make ingestion unusably slow.
"""

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
