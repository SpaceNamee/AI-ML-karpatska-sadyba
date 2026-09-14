"""Application configuration.

Settings are read from environment variables (and a local `.env` file if present).
The object is instantiated once at import time as `settings`; if a required variable
is missing or has the wrong type, the process fails here, at startup, with a clear
error — never later, deep in a request.
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["local", "ci", "production"] = "local"
    debug: bool = False

    # No default on purpose: there is no sane guess for a database, so a missing
    # DATABASE_URL must stop the app at startup rather than fail on first query.
    database_url: str

    # Same reasoning as DATABASE_URL: host `localhost` vs `redis` (in compose)
    # is easy to get silently wrong, so there's no default to fall back on.
    redis_url: str

    # The model and its vector width travel together — changing one without the
    # other is a silent bug (a dimension mismatch) or a wasted re-embed (same
    # dimension, different vectors). embeddings.load_model() checks the two
    # agree at worker startup rather than at the first surprising INSERT error.
    embedding_model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dimensions: int = 384

    # No default: a secret with a built-in fallback is a secret that leaks into
    # every clone of this repo. Generate one per environment, e.g. `openssl rand
    # -hex 32`, and put it in `.env` (never `.env.example`).
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12  # a host checks in a couple times a day

    # Where uploaded knowledge-base documents are written. Mounted as a Docker
    # volume in docker-compose.yml so files survive a container restart.
    storage_dir: Path = Path("data/uploads")
    max_upload_size_bytes: int = 20 * 1024 * 1024  # 20 MB — these are text/PDF FAQs, not video

    # Set only to let `app/db/seed_admin.py` create a first admin account. Left
    # unset in .env.example on purpose: nobody should inherit a working default
    # password by copying the template.
    admin_email: str = "admin@karpatska-sadyba.local"
    admin_seed_password: str | None = None


settings = Settings()  # values come from the environment / .env
