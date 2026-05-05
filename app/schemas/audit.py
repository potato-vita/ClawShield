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


class GoalReportSummary(BaseModel):
    task_intent: str | None = None
    objective_summary: str | None = None
    allowed_actions: list[str] = Field(default_factory=list)


class AlignmentReportSummary(BaseModel):
    total_tool_calls: int = 0
    allowed_count: int = 0
    review_count: int = 0
    denied_count: int = 0
    min_score: float | None = None
    worst_call: str | None = None


class ImpactReportSummary(BaseModel):
    sensitive_access_count: int = 0
    external_request_count: int = 0
    high_impact_count: int = 0


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
    goal_summary: GoalReportSummary = Field(default_factory=GoalReportSummary)
    alignment_summary: AlignmentReportSummary = Field(default_factory=AlignmentReportSummary)
    impact_summary: ImpactReportSummary = Field(default_factory=ImpactReportSummary)
    explainability_trace: list[dict[str, Any]] = Field(default_factory=list)
    conclusion: str
