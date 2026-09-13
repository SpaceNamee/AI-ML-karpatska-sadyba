"""Shared FastAPI dependencies: session -> repository -> service, wired once."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.availability_repository import AvailabilityRepository
from app.repositories.cottage_repository import CottageRepository
from app.services.availability_service import AvailabilityService
from app.services.catalog_service import CatalogService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_catalog_service(session: SessionDep) -> CatalogService:
    return CatalogService(CottageRepository(session))


CatalogServiceDep = Annotated[CatalogService, Depends(get_catalog_service)]


def get_availability_service(
    session: SessionDep, catalog: CatalogServiceDep
) -> AvailabilityService:
    return AvailabilityService(catalog, AvailabilityRepository(session))


AvailabilityServiceDep = Annotated[AvailabilityService, Depends(get_availability_service)]
