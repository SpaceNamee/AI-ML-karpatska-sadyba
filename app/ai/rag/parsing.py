"""Text extraction for uploaded knowledge-base documents.

Deliberately minimal: whichever text a naive per-format extractor gets is the
text we index — no OCR, no layout awareness, no scanned-PDF handling. That's
the honest starting point Research #1/#2 measures against, not a limitation
to quietly work around.
"""

from pathlib import Path

from pypdf import PdfReader


def parse_document(path: Path, content_type: str) -> str:
    if content_type == "application/pdf":
        return _parse_pdf(path)
    return _parse_text(path)


def _parse_pdf(path: Path) -> str:
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _parse_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")
