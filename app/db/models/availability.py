"""Availability blocks: the single source of truth for "is this cottage free on
these dates" — our own confirmed bookings, imported Booking.com blocks, and
manual holds, unified in one table so a query never has to check three places.
"""

import enum
from datetime import date, datetime

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import DATERANGE, ExcludeConstraint, Range
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TZDateTime, pg_enum
from app.db.models.cottage import Cottage


class AvailabilitySource(enum.StrEnum):
    OWN_BOOKING = "own_booking"
    BOOKING_COM = "booking_com"
    MANUAL = "manual"


class AvailabilityBlock(Base):
    """A closed date range during which a cottage is unavailable.

    Discovery §6 also has a `request_id` FK to `booking_requests` — that table
    doesn't exist yet (booking requests land in a later sprint), so it's left
    out rather than modelled against nothing. Add it back when bookings exist.
    """

    __tablename__ = "availability_blocks"
    __table_args__ = (
        # THE core guarantee of the whole project (CLAUDE.md rule #3): two
        # blocks for the same cottage can never have overlapping `stay` ranges —
        # enforced by Postgres itself, not by a Python check-then-insert that
        # races under concurrent requests. `=` on an integer only works inside a
        # GiST index because of btree_gist, which is why that extension was
        # created in the very first migration, before anything used it yet.
        ExcludeConstraint(
            ("cottage_id", "="),
            ("stay", "&&"),
            using="gist",
            name="ck_availability_blocks_no_overlap",
        ),
        # NULLs never collide under UNIQUE, so this only dedupes the iCal rows
        # that actually carry an external_uid (source = booking_com).
        UniqueConstraint("source", "external_uid", name="uq_availability_blocks_external"),
        CheckConstraint("NOT isempty(stay)", name="ck_availability_blocks_stay_not_empty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cottage_id: Mapped[int] = mapped_column(ForeignKey("cottages.id", ondelete="CASCADE"))
    # '[)' (Range's default bounds): check-in inclusive, check-out exclusive, so
    # one guest's checkout and the next guest's check-in on the same day do not
    # count as overlapping.
    stay: Mapped[Range[date]] = mapped_column(DATERANGE)
    source: Mapped[AvailabilitySource] = mapped_column(pg_enum(AvailabilitySource))
    external_uid: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(TZDateTime, server_default=func.now())

    cottage: Mapped[Cottage] = relationship()
