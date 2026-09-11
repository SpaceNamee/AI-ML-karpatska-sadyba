"""Async engine, session factory, and the FastAPI `get_session` dependency."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# One engine per process. It owns the connection pool; creating it is cheap here
# because connections are opened lazily on first use.
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # log every SQL statement while developing
)

# expire_on_commit=False is important with async: the default (True) marks every
# loaded attribute stale after commit, so touching `obj.name` later would trigger
# a lazy reload — which is blocking I/O that async SQLAlchemy refuses to do
# implicitly, raising an error. We commit and then still want to read the object.
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a session for the lifetime of one request.

    `async with` guarantees the session is closed, and rolls back if the request
    handler raises. It does NOT commit — that's a deliberate business decision the
    service layer makes, so a read-only request never writes.
    """
    async with SessionFactory() as session:
        yield session
