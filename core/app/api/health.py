from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.session import get_db

router = APIRouter(prefix="/api/module4", tags=["health"])


class HealthResponse(BaseModel):
    success: bool
    database: str
    service: str
    version: str
    error: str | None = None


@router.get("/health", response_model=HealthResponse, response_model_exclude_none=True)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    settings = get_settings()
    try:
        db.execute(text("SELECT 1"))
        return HealthResponse(
            success=True,
            database="ok",
            service=settings.service_name,
            version=settings.version,
        )
    except Exception as exc:
        return HealthResponse(
            success=False,
            database="error",
            service=settings.service_name,
            version=settings.version,
            error=str(exc),
        )
