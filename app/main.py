from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

from app.api.error_handlers import register_error_handlers
from app.api.router import router as api_router
from app.core.logging import configure_logging
from app.lifecycle import lifespan
from app.settings import get_settings

settings = get_settings()
configure_logging()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)
app.add_middleware(GZipMiddleware, minimum_size=1024)
register_error_handlers(app)
app.include_router(api_router, prefix="/api")
