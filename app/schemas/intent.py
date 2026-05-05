from __future__ import annotations

from pydantic import BaseModel


class ToolCallIntent(BaseModel):
    run_id: str
    tool_call_id: str
    tool_id: str
    step_id: str | None = None
    action_type: str
    operation: str
    inferred_purpose: str
    target_resource_type: str
    target_resource_id: str
    intended_effect: str
    data_direction: str
    model_reason: str | None = None
    confidence: float
