"""Shared FastAPI dependencies: session -> repository -> service, wired once."""

from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import InvalidTokenError
from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.session import get_session
from app.jobs.queue import ArqIngestQueue, IngestQueueLike
from app.repositories.availability_repository import AvailabilityRepository
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.cottage_repository import CottageRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.availability_service import AvailabilityService
from app.services.catalog_service import CatalogService
from app.services.knowledge_base_service import KnowledgeBaseService
from app.services.search_service import SearchService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_catalog_service(session: SessionDep) -> CatalogService:
    return CatalogService(CottageRepository(session))


CatalogServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]


def get_availability_service(
    session: SessionDep, catalog: CatalogServiceDep
) -> AvailabilityService:
    return AvailabilityService(catalog, AvailabilityRepository(session))


AvailabilityServiceDep = Annotated[AvailabilityService, Depends(get_availability_service)]


def get_auth_service(session: SessionDep) -> AuthService:
    return AuthService(UserRepository(session))


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_ingest_queue() -> IngestQueueLike:
    return ArqIngestQueue()


IngestQueueDep = Annotated[IngestQueueLike, Depends(get_ingest_queue)]


def get_knowledge_base_service(session: SessionDep, queue: IngestQueueDep) -> KnowledgeBaseService:
    return KnowledgeBaseService(
        DocumentRepository(session), settings.storage_dir, settings.max_upload_size_bytes, queue
    )


KnowledgeBaseServiceDep = Annotated[KnowledgeBaseService, Depends(get_knowledge_base_service)]


def get_search_service(session: SessionDep) -> SearchService:
    return SearchService(ChunkRepository(session))


SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]

# tokenUrl documents where a client gets a token (shows up as the "Authorize"
# flow in Swagger UI) — it's advertisement, not a redirect the dependency follows.
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(_oauth2_scheme)], session: SessionDep
) -> User:
    try:
        email = decode_access_token(token)
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError() from exc

    user = await UserRepository(session).get_by_email(email)
    if user is None or not user.is_active:
        raise InvalidTokenError()
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
