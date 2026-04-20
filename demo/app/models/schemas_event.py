from datetime import datetime

from pydantic import BaseModel, Field


class EventCreate(BaseModel):
    run_id: str
    task_id: str | None = None
    parent_event_id: str | None = None
    event_type: str
    action: str
    resource_type: str = "unknown"
    resource: str = ""
    params_summary: str = ""
    decision: str = "allow"
    result_status: str = "ok"
    severity: str = "low"
    message: str = ""
    trace_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class EventRead(BaseModel):
    event_id: str
    run_id: str
    task_id: str | None
    parent_event_id: str | None
    event_type: str
    action: str
    resource_type: str
    resource: str
    params_summary: str
    decision: str
    result_status: str
    severity: str
    message: str
    created_at: datetime
    trace_id: str | None
    metadata_json: dict

    model_config = {"from_attributes": True}
