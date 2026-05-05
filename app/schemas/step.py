from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class StepSummary(BaseModel):
    step_id: str
    run_id: str
    goal_id: str | None
    state: str
    step_goal: str
    allowed_action_types: list[str]
    allowed_tools: list[str]
    allowed_effects: list[str]
    parent_step_id: str | None
    status: str
    created_at: datetime
    updated_at: datetime
