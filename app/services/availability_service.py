"""Availability business logic. No HTTP, no SQL — see CLAUDE.md rule #2."""

import calendar
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from app.db.models.availability import AvailabilityBlock
from app.services.catalog_service import CatalogService


class AvailabilityRepositoryLike(Protocol):
    async def list_blocks(
        self, cottage_id: int, window_start: date, window_end: date
    ) -> Sequence[AvailabilityBlock]: ...


@dataclass(frozen=True)
class AvailabilityWindow:
    window_start: date
    window_end: date
    blocks: Sequence[AvailabilityBlock]


def _add_months(start: date, months: int) -> date:
    """Calendar-correct "N months from now", clamped to the target month's
    actual length (Jan 31 + 1 month -> Feb 28/29, not an overflow into March).
    """
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


class AvailabilityService:
    def __init__(self, catalog: CatalogService, repository: AvailabilityRepositoryLike) -> None:
        self._catalog = catalog
        self._repository = repository

    async def get_occupied_ranges(
        self, slug: str, months: int, today: date | None = None
    ) -> AvailabilityWindow:
        # Raises CottageNotFoundError -> 404 if the slug doesn't exist; the
        # caller never has to check for that separately.
        cottage = await self._catalog.get_cottage(slug)
        window_start = today or date.today()
        window_end = _add_months(window_start, months)
        blocks = await self._repository.list_blocks(cottage.id, window_start, window_end)
        return AvailabilityWindow(window_start, window_end, blocks)
