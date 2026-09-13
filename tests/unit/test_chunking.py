import pytest

from app.ai.rag.chunking import chunk_text, normalize_whitespace


def test_normalize_whitespace_collapses_runs() -> None:
    assert normalize_whitespace("a   b\n\nc\t d") == "a b c d"


def test_chunk_text_on_empty_input_returns_nothing() -> None:
    assert chunk_text("   ") == []


def test_chunk_text_shorter_than_size_is_one_chunk() -> None:
    assert chunk_text("hello world", size=400, overlap=50) == ["hello world"]


def test_chunk_text_overlaps_consecutive_windows() -> None:
    words = " ".join(f"w{i}" for i in range(10))

    chunks = chunk_text(words, size=4, overlap=1)

    assert chunks == ["w0 w1 w2 w3", "w3 w4 w5 w6", "w6 w7 w8 w9"]


def test_chunk_text_rejects_overlap_not_smaller_than_size() -> None:
    with pytest.raises(ValueError, match="overlap must be smaller than size"):
        chunk_text("some text", size=5, overlap=5)
