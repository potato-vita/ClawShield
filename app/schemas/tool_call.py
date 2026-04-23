from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


SemanticDecision = Literal["allow", "warn", "deny"]
ActionType = Literal["tool_call", "http", "file_read", "env_read"]


class ToolCallRequest(BaseModel):
    run_id: str
    tool_call_id: str
    tool_id: str
    tool_name: str | None = None
    arguments: dict[str, Any] = Field(default_factory=dict)
    raw_context: dict[str, Any] = Field(default_factory=dict)
    model_reason: str | None = None


class ToolCallDecision(BaseModel):
    run_id: str
    tool_call_id: str
    decision: SemanticDecision
    semantic_reason: str
    policy_reason: str | None = None
    disposition: str
    evaluated_at: datetime
    task_type: str
    dialog_state: str


class ToolResultPayload(BaseModel):
    run_id: str
    tool_call_id: str
    tool_id: str
    result_summary: str | None = None
    raw_result: dict[str, Any] = Field(default_factory=dict)
    execution_status: str = "unknown"
    latency_ms: int | None = None


class ActionRequest(BaseModel):
    run_id: str
    tool_call_id: str
    tool_id: str
    action_type: ActionType
    arguments: dict[str, Any] = Field(default_factory=dict)
    task_type: str = "unknown"
    semantic_decision: SemanticDecision
    semantic_reason: str


class ActionResult(BaseModel):
    run_id: str
    tool_call_id: str
    tool_id: str
    action_type: ActionType
    final_decision: str
    policy_decision: str
    risk_level: str
    disposition: str
    execution_status: str
    resource_type: str
    resource_id: str
    output_summary: str
    executor_name: str
    matched_rules: list[dict[str, Any]] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    completed_at: datetime
