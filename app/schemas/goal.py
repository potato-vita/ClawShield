from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TaskGoalSummary(BaseModel):
    goal_id: str
    run_id: str
    task_intent: str
    objective_summary: str

    allowed_action_types: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    allowed_resource_scopes: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    forbidden_effects: list[str] = Field(default_factory=list)

    confidence: float
    created_at: datetime
    updated_at: datetime
