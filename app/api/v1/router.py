from fastapi import APIRouter

from app.api.v1.endpoints import cottages

router = APIRouter(prefix="/api/v1")
router.include_router(cottages.router)
