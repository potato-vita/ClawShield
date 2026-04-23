from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class SystemStartRequest(BaseModel):
    mode: Literal["dev", "demo"] = "dev"
    auto_launch_opencaw: bool = True


class SystemStartResponse(BaseModel):
    system_status: str
    opencaw_status: str
    opencaw_pid: int | None
    started_at: datetime
    mode: str


class SystemStopResponse(BaseModel):
    system_status: str
    opencaw_status: str
    opencaw_pid: int | None
    stopped_at: datetime


class SystemStatusResponse(BaseModel):
    system_status: str
    opencaw_status: str
    opencaw_pid: int | None
    guardrails_status: str
    guardrails_detail: str | None = None
    checked_at: datetime
