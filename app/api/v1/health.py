from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.db import get_engine
from app.schemas.common import APIResponse, success_response
from app.services.guardrails_service import guardrails_service
from app.services.opencaw_service import opencaw_service

router = APIRouter()


@router.get("/health", response_model=APIResponse)
def health_check() -> APIResponse:
    db_status = "ok"
    db_detail = "connected"

    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = "error"
        db_detail = f"{exc.__class__.__name__}: {exc}"

    return success_response(
        data={
            "app_status": "ok",
            "db_status": db_status,
            "db_detail": db_detail,
            "opencaw_status": opencaw_service.status().get("state", "unknown"),
            "guardrails_status": guardrails_service.status().get("state", "unknown"),
        }
    )
