from fastapi import APIRouter

from app.api.v1.endpoints import auth, cottages, documents

router = APIRouter(prefix="/api/v1")
router.include_router(cottages.router)
router.include_router(auth.router)
router.include_router(documents.router)
