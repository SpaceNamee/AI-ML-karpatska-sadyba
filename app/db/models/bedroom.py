"""Bedroom: a room inside a cottage, with its bed composition.

Modelling choice — bed counts are integer columns on the room, not a separate
`beds` table. Rationale: 3 cottages, ~18 rooms, layouts are fixed and rarely
change, and every query we need ("total sleeping capacity", "rooms with a real
bed") is a simple sum. A child `beds` table would add a join for zero benefit at
this scale. Revisit only if bed *attributes* appear (size, "can be split", price).
"""

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.cottage import Cottage


class Bedroom(Base):
    __tablename__ = "bedrooms"
    __table_args__ = (
        UniqueConstraint("cottage_id", "position", name="uq_bedrooms_cottage_position"),
        CheckConstraint(
            "double_beds >= 0 AND single_beds >= 0 AND sofa_beds >= 0",
            name="ck_bedrooms_bed_counts_non_negative",
        ),
        CheckConstraint(
            "double_beds + single_beds + sofa_beds > 0",
            name="ck_bedrooms_has_at_least_one_bed",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cottage_id: Mapped[int] = mapped_column(
        ForeignKey("cottages.id", ondelete="CASCADE"),
    )
    position: Mapped[int]  # display order within the cottage (1, 2, 3, ...)
    label: Mapped[str] = mapped_column(String(50))  # "Спальня 1", "Вітальня"
    is_living_room: Mapped[bool] = mapped_column(default=False, server_default="false")

    double_beds: Mapped[int] = mapped_column(default=0, server_default="0")
    single_beds: Mapped[int] = mapped_column(default=0, server_default="0")
    sofa_beds: Mapped[int] = mapped_column(default=0, server_default="0")

    cottage: Mapped[Cottage] = relationship(back_populates="bedrooms")
