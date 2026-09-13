from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AvailabilityServiceDep, CatalogServiceDep
from app.db.models.cottage import Cottage
from app.schemas.availability import AvailabilityRead, OccupiedRange
from app.schemas.cottage import CottageRead

router = APIRouter(prefix="/cottages", tags=["cottages"])


@router.get("", response_model=list[CottageRead])
async def list_cottages(catalog: CatalogServiceDep) -> Sequence[Cottage]:
    """All cottages. `response_model` serializes the ORM rows via `CottageRead`
    (`from_attributes=True`); the function itself returns the ORM objects — the
    two type annotations describe different things on purpose.
    """
    return await catalog.list_cottages()


@router.get("/{slug}", response_model=CottageRead)
async def get_cottage(slug: str, catalog: CatalogServiceDep) -> Cottage:
    """A single cottage. `CottageNotFoundError` becomes a 404 via the handler
    registered in `app/main.py` — this function never touches HTTP status codes.
    """
    return await catalog.get_cottage(slug)


@router.get("/{slug}/availability", response_model=AvailabilityRead)
async def get_availability(
    slug: str,
    availability: AvailabilityServiceDep,
    months: Annotated[int, Query(ge=1, le=12, description="How many months ahead to check")] = 3,
) -> AvailabilityRead:
    """Occupied date ranges for the next `months` months. A 404 for an unknown
    slug comes from the same CottageNotFoundError path as `get_cottage` — the
    service resolves the slug before querying blocks.
    """
    window = await availability.get_occupied_ranges(slug, months)
    return AvailabilityRead(
        cottage_slug=slug,
        window_start=window.window_start,
        window_end=window.window_end,
        occupied=[OccupiedRange.from_block(b) for b in window.blocks],
    )
