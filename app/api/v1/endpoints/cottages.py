from collections.abc import Sequence

from fastapi import APIRouter

from app.api.deps import CatalogServiceDep
from app.db.models.cottage import Cottage
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
