"""Password hashing and JWT issuing/verification.

Nothing here talks to a database or FastAPI — it's pure functions over strings,
callable from a service, a script, or a test without any of that machinery.
"""

from datetime import UTC, datetime, timedelta

import jwt
from passlib.context import CryptContext

from app.core.config import settings

# argon2, not bcrypt: it's the current OWASP-recommended default and has no
# 72-byte input truncation footgun. `deprecated="auto"` means if we ever add a
# second scheme (e.g. to migrate away from an old one), existing hashes verify
# and get silently re-hashed with the current default on next login.
_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(password, hashed_password)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """`subject` is the user's email — the one thing the token needs to carry."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Returns the subject (email) or raises `jwt.InvalidTokenError` — expired,
    bad signature, and malformed tokens all raise a subclass of it, so callers
    only need to catch the one base class.
    """
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise jwt.InvalidTokenError("token has no subject")
    return subject
