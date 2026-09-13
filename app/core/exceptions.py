"""Domain-level exceptions and their translation to HTTP responses.

Services raise these; nothing under `services/` imports `fastapi` (see
CLAUDE.md), so the mapping to a status code happens once, centrally, in the
handler registered on `app` in `app/main.py` — not scattered across endpoints.
"""


class DomainError(Exception):
    """Base for every error a service can raise that the API translates."""


class NotFoundError(DomainError):
    """A requested resource does not exist."""


class CottageNotFoundError(NotFoundError):
    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"Cottage '{slug}' not found")
