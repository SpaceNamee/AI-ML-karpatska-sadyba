"""FastAPI application entry point.

Run locally:  uv run uvicorn app.main:app --reload
Docs (Swagger UI):  http://localhost:8000/docs
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.exceptions import NotFoundError

app = FastAPI(title="Karpatska Sadyba API", debug=settings.debug)
app.include_router(v1_router)


@app.exception_handler(NotFoundError)
async def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
    # Same envelope shape as FastAPI's own HTTPException (`{"detail": ...}`), so
    # a client never has to branch on which kind of error came back.
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
