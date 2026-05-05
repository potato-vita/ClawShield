from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.common import APIResponse, success_response
from app.services.audit_service import audit_service

router = APIRouter(prefix="/events")


def _parse_event_types(raw: str | None) -> list[str] | None:
    if raw is None:
        return None
    items = [part.strip() for part in raw.split(",") if part.strip()]
    return items or None


@router.get("", response_model=APIResponse)
def list_events(
    run_id: str | None = None,
    event_type: str | None = None,
    event_types: str | None = None,
    risk_level: str | None = None,
    tool_id: str | None = None,
    resource_type: str | None = None,
    since_ts: datetime | None = None,
    tool_call_id: str | None = None,
    step_id: str | None = None,
    alignment_decision: str | None = None,
    limit: int = 100,
    offset: int = 0,
    order: str = "desc",
    db: Session = Depends(get_db),
) -> APIResponse:
    parsed_event_types = _parse_event_types(event_types)
    events = audit_service.list_events(
        db=db,
        run_id=run_id,
        event_type=event_type,
        event_types=parsed_event_types,
        risk_level=risk_level,
        tool_id=tool_id,
        resource_type=resource_type,
        since_ts=since_ts,
        tool_call_id=tool_call_id,
        step_id=step_id,
        alignment_decision=alignment_decision,
        limit=limit,
        offset=offset,
        order=order,
    )
    total_count = audit_service.count_events(
        db=db,
        run_id=run_id,
        event_type=event_type,
        event_types=parsed_event_types,
        risk_level=risk_level,
        tool_id=tool_id,
        resource_type=resource_type,
        since_ts=since_ts,
        tool_call_id=tool_call_id,
        step_id=step_id,
        alignment_decision=alignment_decision,
    )
    return success_response(
        data={
            "events": [item.model_dump() for item in events],
            "pagination": {
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
                "order": order,
                "has_more": (offset + len(events)) < total_count,
            },
        }
    )
