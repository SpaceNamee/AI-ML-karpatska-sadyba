"""Catalog business logic. No HTTP, no LLM — see CLAUDE.md rule #2: this module
must stay importable from the agent, a background job, or a test with a fake
repository, without pulling in FastAPI.
"""

from collections.abc import Sequence
from typing import Protocol

from app.core.exceptions import CottageNotFoundError
from app.db.models.cottage import Cottage


class CottageRepositoryLike(Protocol):
    """What CatalogService needs from a repository — nothing more.

    Depending on this Protocol instead of the concrete `CottageRepository`
    class is what makes `list_cottages`/`get_cottage` unit-testable with an
    in-memory fake instead of a real Postgres connection (CLAUDE.md: unit tests
    use fake repositories; integration tests use a real database).
    """

    async def list_all(self) -> Sequence[Cottage]: ...
    async def get_by_slug(self, slug: str) -> Cottage | None: ...


class CatalogService:
    def __init__(self, repository: CottageRepositoryLike) -> None:
        self._repository = repository

    async def list_cottages(self) -> Sequence[Cottage]:
        return await self._repository.list_all()

    async def get_cottage(self, slug: str) -> Cottage:
        cottage = await self._repository.get_by_slug(slug)
        if cottage is None:
            raise CottageNotFoundError(slug)
        return cottage
