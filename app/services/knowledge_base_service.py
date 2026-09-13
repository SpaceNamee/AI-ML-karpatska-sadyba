"""Knowledge-base ingestion entry point. No HTTP, no SQL — see CLAUDE.md rule
#2. The actual parsing/chunking/embedding pipeline is a later sprint day; this
service's whole job today is: validate, store the file, and record a PENDING
job for a worker to pick up.
"""

import uuid
from pathlib import Path
from typing import Protocol

import anyio

from app.core.exceptions import UnsupportedDocumentTypeError, UploadTooLargeError
from app.db.models.kb import KbDocument

_ALLOWED_EXTENSIONS = {".txt": "text/plain", ".pdf": "application/pdf"}


def _write_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


class DocumentRepositoryLike(Protocol):
    async def create_pending(
        self, *, title: str, original_filename: str, stored_path: str, content_type: str
    ) -> KbDocument: ...


class KnowledgeBaseService:
    def __init__(
        self, repository: DocumentRepositoryLike, storage_dir: Path, max_upload_size_bytes: int
    ) -> None:
        self._repository = repository
        self._storage_dir = storage_dir
        self._max_upload_size_bytes = max_upload_size_bytes

    async def ingest_upload(
        self, *, filename: str, content: bytes, title: str | None = None
    ) -> KbDocument:
        if len(content) > self._max_upload_size_bytes:
            raise UploadTooLargeError(self._max_upload_size_bytes)

        suffix = Path(filename).suffix.lower()
        content_type = _ALLOWED_EXTENSIONS.get(suffix)
        if content_type is None:
            raise UnsupportedDocumentTypeError(filename)

        # A random stored name, never the client-supplied filename: it sidesteps
        # collisions, path traversal ("../../etc/passwd"), and awkward
        # characters, all in one move. The original name is kept as metadata.
        stored_name = f"{uuid.uuid4()}{suffix}"
        stored_path = self._storage_dir / stored_name
        # The service owns making sure its own storage directory exists rather
        # than trusting a startup hook to have run first — an app `lifespan`
        # only fires under a real ASGI server, not under the ASGITransport that
        # both this test suite and an ad-hoc script use.
        await anyio.to_thread.run_sync(_write_file, stored_path, content)

        return await self._repository.create_pending(
            title=title or Path(filename).stem,
            original_filename=filename,
            stored_path=str(stored_path),
            content_type=content_type,
        )
