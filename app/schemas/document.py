from pydantic import BaseModel

from app.db.models.kb import IngestionStatus


class DocumentAccepted(BaseModel):
    """The `202 Accepted` body: enough to poll `GET /documents/{id}` later
    (that endpoint is a future sprint day), never the processing result itself.
    """

    id: int
    status: IngestionStatus
