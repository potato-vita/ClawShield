from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path

from app.api.health import router as health_router
from app.api.audit import router as audit_router
from app.api.events import router as events_router
from app.api.module4 import router as module4_router
from app.api.policies import router as policies_router
from app.api.reports import router as reports_router
from app.api.sessions import router as sessions_router
from app.config import get_settings
from app.db.init_db import init_db

settings = get_settings()

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="TraceShield Core",
    version=settings.version,
    description="Runtime audit and analysis service for TraceShield.",
    lifespan=lifespan,
)
app.include_router(health_router)
app.include_router(audit_router)
app.include_router(events_router)
app.include_router(module4_router)
app.include_router(reports_router)
app.include_router(sessions_router)
app.include_router(policies_router)


@app.get("/", include_in_schema=False)
def frontend() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")
