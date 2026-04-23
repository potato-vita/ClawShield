from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskIngestRequest(BaseModel):
    session_id: str | None = None
    user_input: str = Field(min_length=1)
    source: str = Field(default="ui")
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskIngestResponse(BaseModel):
    run_id: str
    session_id: str | None = None
    task_type: str = "unknown"
    status: str = "created"
    created_at: datetime
