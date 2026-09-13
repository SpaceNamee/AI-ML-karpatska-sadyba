"""The only module allowed to write SQL for the cottage catalog."""

from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.cottage import Cottage


class CottageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self) -> Select[tuple[Cottage]]:
        # Async SQLAlchemy never lazy-loads implicitly (it would need blocking
        # I/O mid-attribute-access, which it refuses to do). Every relationship
        # the response schema touches must be eager-loaded here, in the query,
        # not discovered by trial and error when a MissingGreenlet error appears.
        return select(Cottage).options(
            selectinload(Cottage.bedrooms),
            selectinload(Cottage.amenities),
        )

    async def list_all(self) -> Sequence[Cottage]:
        stmt = self._base_query().order_by(Cottage.id)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_by_slug(self, slug: str) -> Cottage | None:
        stmt = self._base_query().where(Cottage.slug == slug)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
