"""Import every model here so `Base.metadata` is complete for Alembic autogenerate.

A model that no import path reaches is invisible to `alembic revision --autogenerate`.
Add each new model module to this list as you create it.
"""

from app.db.models.bedroom import Bedroom
from app.db.models.cottage import Amenity, Cottage, cottage_amenities
from app.db.models.kb import IngestionJob, IngestionStatus, KbChunk, KbDocument

__all__ = [
    "Amenity",
    "Bedroom",
    "Cottage",
    "IngestionJob",
    "IngestionStatus",
    "KbChunk",
    "KbDocument",
    "cottage_amenities",
]
