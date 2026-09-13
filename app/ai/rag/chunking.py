"""Fixed-size chunking with overlap.

A deliberately naive baseline (see docs/roadmap-v2-ai-engineer.md Research #1)
— the point of this sprint is to have *something* measurable, not the best
chunker. "Size 400, overlap 50" is by word count, not a model's real subword
tokenizer: no embedding model is wired in yet, and picking a specific
tokenizer now would tie chunking to whichever model happens to be measured
first. Revisit once Research #1 actually compares embedding models.
"""

import re


def normalize_whitespace(text: str) -> str:
    """Collapses runs of whitespace (including newlines) to single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def chunk_text(text: str, *, size: int = 400, overlap: int = 50) -> list[str]:
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")

    words = normalize_whitespace(text).split(" ")
    words = [w for w in words if w]
    if not words:
        return []

    step = size - overlap
    chunks: list[str] = []
    start = 0
    while True:
        chunk_words = words[start : start + size]
        chunks.append(" ".join(chunk_words))
        if start + size >= len(words):
            break
        start += step
    return chunks
