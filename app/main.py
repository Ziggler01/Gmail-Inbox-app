# app/main.py
from __future__ import annotations

from functools import lru_cache

from fastapi import FastAPI
from pydantic_settings import BaseSettings

from app.db.base import Base, engine
from app.routes.reports import router as reports_router  # ensure file exists
try:
    # Optional routers (only if you've added them)
    from app.routes.actions import router as actions_router  # type: ignore
except Exception:  # pragma: no cover
    actions_router = None  # type: ignore
try:
    from app.routes.insights import router as insights_router  # type: ignore
except Exception:  # pragma: no cover
    insights_router = None  # type: ignore


class Settings(BaseSettings):
    # Provide defaults so `Settings()` is mypy-safe; env will override at runtime.
    APP_NAME: str = "Gmail Inbox Cleaner"
    OWNER_EMAIL: str = "owner@example.com"
    GOOGLE_CLIENT_ID: str = "dummy-client-id"
    GOOGLE_CLIENT_SECRET: str = "dummy-client-secret"
    GOOGLE_REDIRECT_URI: str = "http://localhost/oauth/callback"
    GOOGLE_SCOPES: str = "https://www.googleapis.com/auth/gmail.readonly"
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
    # Enable/disable dev auto-creation of tables at startup (migrations in prod)
    DEV_CREATE_ALL: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.APP_NAME)

    # Routers
    app.include_router(reports_router)
    if actions_router:
        app.include_router(actions_router)  # /actions/plan
    if insights_router:
        app.include_router(insights_router)  # /insights/unsubscribe_stats

    @app.on_event("startup")
    async def startup_create_tables() -> None:
        # For dev/test convenience only; in prod rely on Alembic migrations.
        if settings.DEV_CREATE_ALL:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

    @app.get("/")
    def root() -> dict[str, str]:
        return {"app": settings.APP_NAME, "owner": settings.OWNER_EMAIL}

    return app


# Uvicorn/Gunicorn entrypoint
app = create_app()
