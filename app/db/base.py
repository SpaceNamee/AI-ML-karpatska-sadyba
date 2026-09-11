"""Declarative base and shared column mixins for all ORM models.

Every model imports `Base` from here. Alembic autogenerate compares the database
against `Base.metadata`, so a model that is never imported is invisible to
migrations — `app/db/models/__init__.py` exists to import them all in one place.
"""

import enum
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Always store timezone-aware timestamps (Postgres `timestamptz`). A naive
# `TIMESTAMP` silently assumes a timezone and breaks the moment two of them exist.
TZDateTime = DateTime(timezone=True)


class Base(DeclarativeBase):
    pass


def pg_enum(enum_cls: type[enum.Enum]) -> SAEnum:
    """A Postgres ENUM column type that stores the member *value*, not its name.

    By default SQLAlchemy stores `MyEnum.FOO` as the string ``"FOO"`` (the member
    name). We almost always want the lowercase `.value` in the database, so route
    every enum column through this helper:

        status: Mapped[JobStatus] = mapped_column(pg_enum(JobStatus))
    """
    return SAEnum(enum_cls, values_callable=lambda e: [m.value for m in e])


class TimestampMixin:
    """Adds `created_at` / `updated_at`, filled by the database, not Python.

    `server_default=func.now()` -> Postgres sets the value on INSERT.
    `onupdate=func.now()` -> SQLAlchemy sets it on every ORM UPDATE. Note this
    fires only for ORM-issued updates, not raw SQL; a trigger would be needed for
    a hard guarantee, which we don't need yet.
    """

    created_at: Mapped[datetime] = mapped_column(TZDateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime,
        server_default=func.now(),
        onupdate=func.now(),
    )
