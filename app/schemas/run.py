from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RunSummary(BaseModel):
    run_id: str
    session_id: str | None = None
    task_summary: str | None = None
    task_type: str = "unknown"
    status: str = "created"
    final_risk_level: str | None = None
    disposition: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime


class RunListResponse(BaseModel):
    runs: list[RunSummary]
