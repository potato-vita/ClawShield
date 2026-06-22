from typing import Any

from pydantic import BaseModel


class DashboardResponse(BaseModel):
    success: bool
    data: dict[str, Any]


class EventDetailResponse(BaseModel):
    success: bool
    event: dict[str, Any]
    risk_explanation: str
    recommended_actions: list[str]
    tool_call: dict[str, Any]
    audit_decision: dict[str, Any]
    evidence: list[dict[str, Any]]
    risk_graph: list[dict[str, Any]]
