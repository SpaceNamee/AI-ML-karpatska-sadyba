"""Pydantic schemas for the cottage catalog — the API's external contract.

This is the homework from `docs/technical-discovery-v1.md` §10. Answers to its
five questions are in the comments below, next to the code that answers them.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.db.models.cottage import AmenityCategory, CottageView


class AmenityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    category: AmenityCategory
    is_free: bool


class BedroomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    position: int
    label: str
    is_living_room: bool
    double_beds: int
    single_beds: int
    sofa_beds: int


class CottageBase(BaseModel):
    """Fields both directions agree on.

    Q2 — price would belong here if `Cottage` had one (it doesn't yet; pricing
    is `rate_rules`, a later sprint). The rule for when it arrives: `Decimal`,
    never `float`. `float` is binary floating point — `0.1 + 0.2 != 0.3` — so a
    chain of additions/discounts on a price silently drifts by fractions of a
    kopiyka. `Decimal` does exact base-10 arithmetic, which is what an invoice
    needs. Same reasoning as the `numeric` column type on the database side.
    """

    name: str
    area_sqm: int
    max_guests: int
    base_guests: int
    bathrooms: int
    view: CottageView
    description: str = ""

    # Q3 — a cross-field invariant can't live on a single field's own validator,
    # so it goes in a model-level one. This mirrors the database CheckConstraint
    # of the same name in `Cottage.__table_args__`: the DB is the guarantee that
    # can never be bypassed, this is the same rule enforced earlier, with a
    # response the client gets *before* a wasted round trip to the database.
    @model_validator(mode="after")
    def _check_guest_counts(self) -> Self:
        if self.base_guests <= 0:
            raise ValueError("base_guests must be positive")
        if self.base_guests > self.max_guests:
            raise ValueError("base_guests must not exceed max_guests")
        return self


class CottageCreate(CottageBase):
    """What an admin submits to create a cottage.

    Q5 — no `id` here. Identity is assigned by the database (`SERIAL`/identity
    column); accepting a client-supplied id would let two admins race for the
    same value, or let a client dictate primary keys it has no business
    choosing. `slug` *is* included even though it's also server-facing: unlike
    `id` it's a business-meaningful value (the URL), chosen by a human, not a
    generated surrogate — so the client provides it, same as `name`.
    """

    slug: str


class CottageRead(CottageBase):
    """What the API hands back.

    Q1 — CottageRead and CottageCreate are different models, not one model with
    every field Optional, because they answer different questions. Create says
    "what must a client provide to make one" (no id, no bedrooms yet — those
    are added afterward through their own endpoints). Read says "what does the
    server hand back" (id, and everything nested for display). An
    Optional-everything model can't express either of those; every field looks
    equally optional, and nothing stops a client from POSTing an `id` or
    reading back a cottage with `name: None`. Two narrow models are the
    documentation, not just the validation.

    Q4 — `amenities` is `list[AmenityRead]`, not `list[str]` or an `Enum`.
    `list[str]` can't catch a typo ("wifi" vs "wi-fi") and drops the metadata
    (category, is_free) a client needs to render anything useful. An `Enum`
    catches the typo but fights the fact that amenities are already a real,
    growing database table — every new amenity would need a code change and a
    deploy. A model built from the ORM row keeps the two in lockstep, is
    extensible without touching this file, and gets the same treatment as
    `BedroomRead` below for the same reason.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    bedrooms: list[BedroomRead]
    amenities: list[AmenityRead]
