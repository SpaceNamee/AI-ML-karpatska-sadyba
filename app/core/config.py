"""Application configuration.

Settings are read from environment variables (and a local `.env` file if present).
The object is instantiated once at import time as `settings`; if a required variable
is missing or has the wrong type, the process fails here, at startup, with a clear
error — never later, deep in a request.
"""

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


settings = Settings()  # values come from the environment / .env

