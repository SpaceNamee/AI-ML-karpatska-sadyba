from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile, status

from app.api.deps import CurrentUserDep, KnowledgeBaseServiceDep
from app.core.exceptions import UnsupportedDocumentTypeError
from app.schemas.document import DocumentAccepted

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", status_code=status.HTTP_202_ACCEPTED, response_model=DocumentAccepted)
async def upload_document(
    current_user: CurrentUserDep,
    kb: KnowledgeBaseServiceDep,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
) -> DocumentAccepted:
    """Admin-only (`CurrentUserDep` enforces that — an unauthenticated or
    invalid-token request never reaches this body). Adds a document to the
    knowledge base and returns immediately with its job PENDING; parsing,
    chunking, and embedding are a later sprint day's async worker, not this
    request.
    """
    if file.filename is None:
        raise UnsupportedDocumentTypeError("<no filename>")
    content = await file.read()
    document = await kb.ingest_upload(filename=file.filename, content=content, title=title)
    # `job` is `IngestionJob | None` in the type (a Postgres row could lack
    # one); `create_pending` always attaches one, so this is a real invariant,
    # not user input, and the assert documents that for mypy and the reader.
    assert document.job is not None
    return DocumentAccepted(id=document.id, status=document.job.status)
