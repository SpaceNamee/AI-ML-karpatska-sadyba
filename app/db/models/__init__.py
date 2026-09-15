"""Import every model here so `Base.metadata` is complete for Alembic autogenerate.

A model that no import path reaches is invisible to `alembic revision --autogenerate`.
Add each new model module to this list as you create it.
"""

from app.db.models.availability import AvailabilityBlock, AvailabilitySource
from app.db.models.bedroom import Bedroom
from app.db.models.cottage import Amenity, Cottage, cottage_amenities
from app.db.models.kb import IngestionJob, IngestionStatus, KbChunk, KbDocument
from app.db.models.llm_call import LlmCall
from app.db.models.user import User

__all__ = [
    "Amenity",
    "AvailabilityBlock",
    "AvailabilitySource",
    "Bedroom",
    "Cottage",
    "IngestionJob",
    "IngestionStatus",
    "KbChunk",
    "KbDocument",
    "LlmCall",
    "User",
    "cottage_amenities",
]
