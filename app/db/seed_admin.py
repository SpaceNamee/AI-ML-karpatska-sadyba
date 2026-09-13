"""One-off creation of the first admin account.

Run with:  uv run python -m app.db.seed_admin

Requires ADMIN_SEED_PASSWORD in the environment — deliberately not defaulted,
so nobody gets a working account by copying `.env.example`. Idempotent: does
nothing if a user with ADMIN_EMAIL already exists.
"""

import asyncio
import sys

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionFactory
from app.repositories.user_repository import UserRepository


async def seed_admin() -> None:
    if not settings.admin_seed_password:
        print("ADMIN_SEED_PASSWORD is not set — nothing to do.", file=sys.stderr)
        return

    async with SessionFactory() as session:
        repository = UserRepository(session)
        existing = await repository.get_by_email(settings.admin_email)
        if existing is not None:
            print(f"{settings.admin_email} already exists — nothing to do.")
            return

        await repository.create(
            email=settings.admin_email,
            hashed_password=hash_password(settings.admin_seed_password),
        )
        print(f"Created admin user {settings.admin_email}.")


if __name__ == "__main__":
    asyncio.run(seed_admin())
