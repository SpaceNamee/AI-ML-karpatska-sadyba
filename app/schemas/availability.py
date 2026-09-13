from datetime import date

from pydantic import BaseModel

from app.db.models.availability import AvailabilityBlock, AvailabilitySource


class OccupiedRange(BaseModel):
    check_in: date
    check_out: date  # exclusive, matching the '[)' semantics in the database
    source: AvailabilitySource

    @classmethod
    def from_block(cls, block: AvailabilityBlock) -> "OccupiedRange":
        # `stay.lower`/`.upper` are typed Optional (a Postgres range can be
        # unbounded) even though our schema's CheckConstraints make that
        # impossible for a row that reached this code — narrow explicitly
        # rather than asserting past it.
        if block.stay.lower is None or block.stay.upper is None:
            raise ValueError("availability block has an unbounded range")
        return cls(check_in=block.stay.lower, check_out=block.stay.upper, source=block.source)


class AvailabilityRead(BaseModel):
    cottage_slug: str
    window_start: date
    window_end: date
    occupied: list[OccupiedRange]
