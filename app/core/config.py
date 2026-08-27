"""
Centralized, typed application settings.

Why this matters for a production system: every config value the app needs is
declared here, once, with a type. If a required env var is missing or malformed,
the app refuses to start — you find out at `docker compose up`, not three hours
into a live demo when a request 500s because DATABASE_URL had a typo.

Never read os.environ directly anywhere else in the codebase. Import `settings`.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    ENV: Literal["dev", "test", "prod"] = "dev"
    APP_NAME: str = "Widget & Lead-Capture Platform"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    # Used to build the <script src="..."> embed snippet returned with each widget.
    PUBLIC_BASE_URL: str = "http://localhost:8000"
    # Bumped when the widget.js loader itself ships a breaking change.
    # A new version = a new URL (widget.v2.js), never mutating this file's
    # content in place — see app/api/public.py.
    WIDGET_BUNDLE_VERSION: str = "v1"

    # --- Database ---
    DATABASE_URL: str = Field(..., description="asyncpg SQLAlchemy URL, e.g. postgresql+asyncpg://user:pass@host/db")
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT_SECONDS: int = 30
    # Recycle connections periodically so the pool never hands out a connection
    # the DB (or a proxy/load balancer in front of it) has silently dropped.
    DB_POOL_RECYCLE_SECONDS: int = 1800

    # --- Auth ---
    JWT_SECRET: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 12

    # --- CORS ---
    # Comma-separated list of allowed origins for the PUBLIC submission endpoint.
    # Deliberately explicit allow-list, never "*", because credentials/config
    # responses ride the same CORS policy.
    ALLOWED_ORIGINS: str = "http://localhost:5500,http://127.0.0.1:5500"

    # --- Rate limiting ---
    SUBMISSION_RATE_LIMIT_PER_IP: str = "5/minute"
    SUBMISSION_RATE_LIMIT_PER_WIDGET: str = "60/minute"

    # --- Enrichment providers ---
    GEO_PROVIDER_A_URL: str = "http://ip-api.com/json/{ip}"
    GEO_PROVIDER_B_URL: str = "https://ipapi.co/{ip}/json/"
    GEO_PROVIDER_TIMEOUT_SECONDS: float = 2.0
    # Demo/testing aid ONLY — never set true in a real deployment. Forces
    # provider A to behave as if it were down, without depending on a real
    # third-party outage happening to occur during a live demo. See
    # app/enrichment/ip_api.py.
    GEO_PROVIDER_A_FORCE_FAIL: bool = False

    # --- Notifications (safe side effect) ---
    NOTIFY_BACKEND: Literal["console", "webhook"] = "console"
    NOTIFY_WEBHOOK_URL: str | None = None
    # Same demo/testing purpose as GEO_PROVIDER_A_FORCE_FAIL above, applied
    # to the notification side effect. See app/notifications/console.py.
    NOTIFY_FORCE_FAIL: bool = False

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        # Cheap sanity check at boot time rather than a cryptic driver error later.
        if not v.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use the postgresql+asyncpg:// driver")
        return v

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so we parse/validate env vars exactly once per process."""
    return Settings()


settings = get_settings()
