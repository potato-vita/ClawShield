from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.graph import TimelineItem


class ToolCallSummary(BaseModel):
    tool_id: str
    semantic_decision: str | None = None
    policy_decision: str | None = None
    disposition: str | None = None
    risk_level: str | None = None


class ResourceSummary(BaseModel):
    resource_type: str
    resource_id: str
    access_count: int
    max_risk_level: str | None = None


class RiskHitSummary(BaseModel):
    chain_id: str
    risk_level: str
    explanation: str | None = None


class DispositionSummary(BaseModel):
    allow: int = 0
    warn: int = 0
    deny: int = 0


class AuditReportPayload(BaseModel):
    run_id: str
    task_summary: str | None = None
    semantic_summary: str | None = None
    tool_calls: list[ToolCallSummary] = Field(default_factory=list)
    resources: list[ResourceSummary] = Field(default_factory=list)
    risk_hits: list[RiskHitSummary] = Field(default_factory=list)
    timeline: list[TimelineItem] = Field(default_factory=list)
    graph: dict[str, Any] = Field(default_factory=dict)
    final_risk_level: str | None = None
    final_disposition: str | None = None
    disposition_summary: DispositionSummary = Field(default_factory=DispositionSummary)
    conclusion: str
