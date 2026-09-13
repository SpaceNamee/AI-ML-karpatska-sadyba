import pytest

from app.core.exceptions import InvalidCredentialsError
from app.core.security import hash_password
from app.db.models.user import User
from app.services.auth_service import AuthService


class FakeUserRepository:
    def __init__(self, users: list[User]) -> None:
        self._users = users

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._users if u.email == email), None)


def _user(email: str, password: str, *, is_active: bool = True) -> User:
    return User(email=email, hashed_password=hash_password(password), is_active=is_active)


async def test_authenticate_succeeds_with_correct_password() -> None:
    service = AuthService(FakeUserRepository([_user("host@example.com", "correct-horse")]))

    user = await service.authenticate("host@example.com", "correct-horse")

    assert user.email == "host@example.com"


async def test_authenticate_rejects_wrong_password() -> None:
    service = AuthService(FakeUserRepository([_user("host@example.com", "correct-horse")]))

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate("host@example.com", "wrong-password")


async def test_authenticate_rejects_unknown_email() -> None:
    service = AuthService(FakeUserRepository([]))

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate("nobody@example.com", "anything")


async def test_authenticate_rejects_inactive_user() -> None:
    service = AuthService(
        FakeUserRepository([_user("host@example.com", "correct-horse", is_active=False)])
    )

    with pytest.raises(InvalidCredentialsError):
        await service.authenticate("host@example.com", "correct-horse")
