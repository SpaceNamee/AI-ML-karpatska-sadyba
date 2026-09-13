"""CatalogService tested against a fake repository — no database, no session,
runs in milliseconds. This is what CottageRepositoryLike (a Protocol) buys us.
"""

from collections.abc import Sequence

import pytest

from app.core.exceptions import CottageNotFoundError
from app.db.models.cottage import Cottage, CottageView
from app.services.catalog_service import CatalogService


class FakeCottageRepository:
    """Implements the same shape as CottageRepositoryLike, backed by a list."""

    def __init__(self, cottages: Sequence[Cottage]) -> None:
        self._cottages = cottages

    async def list_all(self) -> Sequence[Cottage]:
        return self._cottages

    async def get_by_slug(self, slug: str) -> Cottage | None:
        return next((c for c in self._cottages if c.slug == slug), None)


def _cottage(slug: str) -> Cottage:
    return Cottage(
        slug=slug,
        name=slug,
        area_sqm=100,
        max_guests=10,
        base_guests=5,
        bathrooms=1,
        view=CottageView.MOUNTAINS,
    )


async def test_list_cottages_returns_everything_the_repository_has() -> None:
    service = CatalogService(FakeCottageRepository([_cottage("a"), _cottage("b")]))

    result = await service.list_cottages()

    assert [c.slug for c in result] == ["a", "b"]


async def test_get_cottage_returns_the_matching_one() -> None:
    service = CatalogService(FakeCottageRepository([_cottage("a"), _cottage("b")]))

    result = await service.get_cottage("b")

    assert result.slug == "b"


async def test_get_cottage_raises_when_missing() -> None:
    service = CatalogService(FakeCottageRepository([_cottage("a")]))

    with pytest.raises(CottageNotFoundError):
        await service.get_cottage("does-not-exist")
