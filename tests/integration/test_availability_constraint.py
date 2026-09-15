"""The mandatory test from CLAUDE.md rule #3: a test asserting an overlapping
availability_blocks insert raises IntegrityError is "never cut". This is the
one guarantee the whole booking architecture rests on — the DB, not Python,
must refuse a double-booking, even under concurrent requests a Python check
would race.
"""

from datetime import date

import pytest
from sqlalchemy.dialects.postgresql import Range
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.availability import AvailabilityBlock, AvailabilitySource
from app.db.models.cottage import Cottage, CottageView


async def _make_cottage(session: AsyncSession, slug: str) -> Cottage:
    cottage = Cottage(
        slug=slug,
        name="Test cottage",
        area_sqm=100,
        max_guests=10,
        base_guests=5,
        bathrooms=1,
        view=CottageView.MOUNTAINS,
    )
    session.add(cottage)
    await session.flush()
    return cottage


async def test_overlapping_stay_on_the_same_cottage_raises_integrity_error(
    db_session: AsyncSession,
) -> None:
    cottage = await _make_cottage(db_session, "constraint-test-1")
    db_session.add(
        AvailabilityBlock(
            cottage_id=cottage.id,
            stay=Range(date(2027, 6, 10), date(2027, 6, 15)),
            source=AvailabilitySource.MANUAL,
        )
    )
    await db_session.commit()

    db_session.add(
        AvailabilityBlock(
            cottage_id=cottage.id,
            # Overlaps 6/10-6/15 by two nights (6/12, 6/13).
            stay=Range(date(2027, 6, 12), date(2027, 6, 18)),
            source=AvailabilitySource.MANUAL,
        )
    )
    with pytest.raises(IntegrityError, match="ck_availability_blocks_no_overlap"):
        await db_session.commit()


async def test_back_to_back_stays_do_not_overlap(db_session: AsyncSession) -> None:
    """`[)` bounds: one guest's checkout and the next guest's check-in on the
    same day must NOT count as a conflict, or the cottage sits empty needlessly.
    """
    cottage = await _make_cottage(db_session, "constraint-test-2")
    db_session.add(
        AvailabilityBlock(
            cottage_id=cottage.id,
            stay=Range(date(2027, 7, 1), date(2027, 7, 5)),
            source=AvailabilitySource.MANUAL,
        )
    )
    await db_session.commit()

    db_session.add(
        AvailabilityBlock(
            cottage_id=cottage.id,
            stay=Range(date(2027, 7, 5), date(2027, 7, 9)),  # starts exactly on checkout day
            source=AvailabilitySource.MANUAL,
        )
    )
    await db_session.commit()  # must not raise


async def test_same_dates_on_a_different_cottage_are_independent(
    db_session: AsyncSession,
) -> None:
    cottage_a = await _make_cottage(db_session, "constraint-test-3a")
    cottage_b = await _make_cottage(db_session, "constraint-test-3b")
    same_stay = Range(date(2027, 8, 1), date(2027, 8, 5))

    db_session.add(
        AvailabilityBlock(cottage_id=cottage_a.id, stay=same_stay, source=AvailabilitySource.MANUAL)
    )
    await db_session.commit()

    db_session.add(
        AvailabilityBlock(cottage_id=cottage_b.id, stay=same_stay, source=AvailabilitySource.MANUAL)
    )
    await db_session.commit()  # must not raise — the constraint is per-cottage


async def test_empty_stay_range_is_rejected(db_session: AsyncSession) -> None:
    cottage = await _make_cottage(db_session, "constraint-test-4")
    db_session.add(
        AvailabilityBlock(
            cottage_id=cottage.id,
            stay=Range(date(2027, 9, 1), date(2027, 9, 1)),  # check-in == check-out
            source=AvailabilitySource.MANUAL,
        )
    )
    with pytest.raises(IntegrityError, match="ck_availability_blocks_stay_not_empty"):
        await db_session.commit()
