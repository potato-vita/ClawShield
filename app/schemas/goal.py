from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class GoalSummary(BaseModel):
    goal_id: str
    run_id: str
    task_intent: str
    objective_summary: str
    allowed_action_types: list[str]
    allowed_tools: list[str]
    allowed_resource_scopes: list[str]
    expected_outputs: list[str]
    forbidden_actions: list[str]
    forbidden_effects: list[str]
    risk_constraints: list[str]
    confidence: float
    created_at: datetime
