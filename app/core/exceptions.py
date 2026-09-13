"""Domain-level exceptions and their translation to HTTP responses.

Services raise these; nothing under `services/` imports `fastapi` (see
CLAUDE.md), so the mapping to a status code happens once, centrally, via a
single handler registered on `app` in `app/main.py` — not scattered across
endpoints. Each subclass just declares which status code it means.
"""


class DomainError(Exception):
    """Base for every error a service can raise that the API translates."""

    status_code: int = 500


class NotFoundError(DomainError):
    status_code = 404


class CottageNotFoundError(NotFoundError):
    def __init__(self, slug: str) -> None:
        self.slug = slug
        super().__init__(f"Cottage '{slug}' not found")


class AuthenticationError(DomainError):
    """401s. The handler adds a `WWW-Authenticate: Bearer` header for these,
    per the OAuth2 bearer-token spec.
    """

    status_code = 401


class InvalidCredentialsError(AuthenticationError):
    def __init__(self) -> None:
        super().__init__("Incorrect email or password")


class InvalidTokenError(AuthenticationError):
    def __init__(self) -> None:
        super().__init__("Could not validate credentials")


class UnsupportedDocumentTypeError(DomainError):
    status_code = 415

    def __init__(self, filename: str) -> None:
        self.filename = filename
        super().__init__(f"Unsupported document type: '{filename}' (allowed: .txt, .pdf)")


class UploadTooLargeError(DomainError):
    status_code = 413

    def __init__(self, max_bytes: int) -> None:
        self.max_bytes = max_bytes
        super().__init__(f"Upload exceeds the {max_bytes}-byte limit")
