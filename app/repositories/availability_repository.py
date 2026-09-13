"""The only module allowed to write SQL for availability blocks."""

from collections.abc import Sequence
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.availability import AvailabilityBlock


class AvailabilityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_blocks(
        self, cottage_id: int, window_start: date, window_end: date
    ) -> Sequence[AvailabilityBlock]:
        """Blocks for `cottage_id` that overlap `[window_start, window_end)`."""
        window = Range(window_start, window_end)
        stmt = (
            select(AvailabilityBlock)
            .where(AvailabilityBlock.cottage_id == cottage_id)
            .where(AvailabilityBlock.stay.overlaps(window))
            .order_by(func.lower(AvailabilityBlock.stay))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
