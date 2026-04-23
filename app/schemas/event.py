from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class EventSummary(BaseModel):
    event_id: str
    run_id: str
    session_id: str | None = None
    event_type: str
    event_stage: str | None = None
    ts: datetime
    actor_type: str | None = None
    tool_id: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    semantic_decision: str | None = None
    policy_decision: str | None = None
    risk_level: str | None = None
    disposition: str | None = None
    status: str | None = None


class EventListResponse(BaseModel):
    events: list[EventSummary]
