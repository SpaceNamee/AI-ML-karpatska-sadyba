"""FastAPI application entry point.

Run locally:  uv run uvicorn app.main:app --reload
Docs (Swagger UI):  http://localhost:8000/docs
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.exceptions import AuthenticationError, DomainError
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware

configure_logging(debug=settings.debug)

app = FastAPI(title="Karpatska Sadyba API", debug=settings.debug)
app.add_middleware(RequestIDMiddleware)
app.include_router(v1_router)


@app.exception_handler(DomainError)
async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    # Same envelope shape as FastAPI's own HTTPException (`{"detail": ...}`), so
    # a client never has to branch on which kind of error came back. Every
    # DomainError subclass just declares its own status_code.
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, AuthenticationError) else None
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)}, headers=headers)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
