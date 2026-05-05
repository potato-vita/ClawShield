from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AlignmentEvaluationData(BaseModel):
    eval_id: str
    run_id: str
    tool_call_id: str
    goal_id: str | None = None
    step_id: str | None = None
    goal_relevance: float
    state_legality: float
    resource_necessity: float
    effect_safety: float
    reason_support: float
    anomaly_penalty: float = 0.0
    exfiltration_penalty: float = 0.0
    necessity_verdict: str = "weakly_necessary"
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    justification_ref: str | None = None
    counterfactual_note: str | None = None
    overall_score: float
    decision: str
    risk_level: str
    reasons: list[str] = Field(default_factory=list)
    matched_rules: list[dict] = Field(default_factory=list)
    hard_reason_codes: list[str] = Field(default_factory=list)
    created_at: datetime
