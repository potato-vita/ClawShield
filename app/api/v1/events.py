from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.common import APIResponse, success_response
from app.services.audit_service import audit_service

router = APIRouter(prefix="/events")


@router.get("", response_model=APIResponse)
def list_events(
    run_id: str | None = None,
    event_type: str | None = None,
    risk_level: str | None = None,
    tool_id: str | None = None,
    resource_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
    order: str = "desc",
    db: Session = Depends(get_db),
) -> APIResponse:
    events = audit_service.list_events(
        db=db,
        run_id=run_id,
        event_type=event_type,
        risk_level=risk_level,
        tool_id=tool_id,
        resource_type=resource_type,
        limit=limit,
        offset=offset,
        order=order,
    )
    return success_response(data={"events": [item.model_dump() for item in events]})
