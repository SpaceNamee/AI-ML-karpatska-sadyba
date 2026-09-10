"""FastAPI application entry point.

Run locally:  uv run uvicorn app.main:app --reload
Docs (Swagger UI):  http://localhost:8000/docs
"""

from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(title="Karpatska Sadyba API", debug=settings.debug)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
