"""Authentication business logic. No HTTP, no SQL — see CLAUDE.md rule #2."""

from typing import Protocol

from app.core.exceptions import InvalidCredentialsError
from app.core.security import verify_password
from app.db.models.user import User


class UserRepositoryLike(Protocol):
    async def get_by_email(self, email: str) -> User | None: ...


class AuthService:
    def __init__(self, repository: UserRepositoryLike) -> None:
        self._repository = repository

    async def authenticate(self, email: str, password: str) -> User:
        user = await self._repository.get_by_email(email)
        # Deliberately one error for "no such user" and "wrong password": telling
        # a caller *which* is true is exactly what lets them enumerate accounts.
        password_ok = user is not None and verify_password(password, user.hashed_password)
        if user is None or not user.is_active or not password_ok:
            raise InvalidCredentialsError()
        return user
