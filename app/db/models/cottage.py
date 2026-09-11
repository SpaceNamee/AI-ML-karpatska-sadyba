"""Catalog models: Cottage, Amenity, and the cottage<->amenity link.

This module + `bedroom.py` are the reference for the SQLAlchemy 2.0 patterns used
across the project. The knowledge-base models follow the same shape.
"""

import enum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, pg_enum

if TYPE_CHECKING:
    from app.db.models.bedroom import Bedroom


class CottageView(enum.StrEnum):
    """What you see from the cottage. Stored as a native Postgres ENUM."""

    MOUNTAINS = "mountains"
    POOL_AND_MOUNTAINS = "pool_and_mountains"


class AmenityCategory(enum.StrEnum):
    COMFORT = "comfort"
    KITCHEN = "kitchen"
    OUTDOOR = "outdoor"
    SAFETY = "safety"


# A dataless many-to-many link is a plain Table, not a model. Promote it to a
# mapped class only when the link itself needs columns (e.g. "added_at", "note").
cottage_amenities = Table(
    "cottage_amenities",
    Base.metadata,
    Column("cottage_id", ForeignKey("cottages.id", ondelete="CASCADE"), primary_key=True),
    Column("amenity_id", ForeignKey("amenities.id", ondelete="CASCADE"), primary_key=True),
)


class Cottage(TimestampMixin, Base):
    __tablename__ = "cottages"
    __table_args__ = (
        # The invariant lives in the database. A Pydantic check is a nicer error
        # message; this is the guarantee that survives a bad script or migration.
        CheckConstraint("base_guests > 0", name="ck_cottages_base_guests_positive"),
        CheckConstraint("base_guests <= max_guests", name="ck_cottages_base_le_max"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # `slug` is the URL identifier ("cottage-1"); `unique=True` also builds an index.
    slug: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    area_sqm: Mapped[int]
    max_guests: Mapped[int]
    base_guests: Mapped[int]
    view: Mapped[CottageView] = mapped_column(pg_enum(CottageView))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")

    bedrooms: Mapped[list["Bedroom"]] = relationship(
        back_populates="cottage",
        cascade="all, delete-orphan",  # deleting a cottage deletes its bedrooms
        order_by="Bedroom.position",
    )
    amenities: Mapped[list["Amenity"]] = relationship(
        secondary=cottage_amenities,
        back_populates="cottages",
    )


class Amenity(TimestampMixin, Base):
    __tablename__ = "amenities"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[AmenityCategory] = mapped_column(pg_enum(AmenityCategory))
    is_free: Mapped[bool] = mapped_column(default=True, server_default="true")

    cottages: Mapped[list[Cottage]] = relationship(
        secondary=cottage_amenities,
        back_populates="amenities",
    )
