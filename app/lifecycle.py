from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.db import init_database, init_engine
from app.settings import get_settings
from app.services.opencaw_service import opencaw_service


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    init_engine()
    init_database()
    app.state.settings = settings
    app.state.opencaw_service = opencaw_service

    if settings.openclaw_auto_launch:
        opencaw_service.start(mode=settings.app_env)

    try:
        yield
    finally:
        opencaw_service.shutdown()
