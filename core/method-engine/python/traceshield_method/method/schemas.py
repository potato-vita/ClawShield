from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


VIOLATION_PRIORITY = [
    "prompt_injection_induced_drift",
    "chain_semantic_drift",
    "intent_resource_inconsistency",
    "intent_tool_inconsistency",
    "step_step_inconsistency",
]


class IntentFrame(BaseModel):
    task_goal: str
    allowed_actions: List[str] = Field(default_factory=list)
    allowed_resources: List[str] = Field(default_factory=list)
    forbidden_actions: List[str] = Field(default_factory=list)
    forbidden_resources: List[str] = Field(default_factory=list)
    sensitive_resources: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)


class ToolEvent(BaseModel):
    step_id: int
    tool_name: str
    args: Dict[str, Any] = Field(default_factory=dict)
    raw_call: Optional[str] = None
    observation: Optional[str] = None


class SemanticEvent(BaseModel):
    step_id: int
    tool_name: str
    tool_type: str
    semantic_action: str
    target_resource: Optional[str] = None
    risk_level: str = "low"
    raw_event: ToolEvent


class Violation(BaseModel):
    violation_type: str
    evidence_steps: List[int] = Field(default_factory=list)
    reason: str
    target: Optional[str] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditResult(BaseModel):
    sample_id: str
    decision: Literal["allow", "deny"]
    violations: List[Violation] = Field(default_factory=list)
    evidence_steps: List[int] = Field(default_factory=list)
    primary_violation_type: Optional[str] = None
    primary_evidence_steps: List[int] = Field(default_factory=list)
    explanation: str = ""
    latency_ms: Optional[float] = None


class DatasetSample(BaseModel):
    id: str
    source: str
    domain: str
    user_query: str
    intent_frame: IntentFrame
    context: Dict[str, Any] = Field(default_factory=dict)
    trace: List[ToolEvent]
    final_output: Optional[str] = None
    ground_truth: Dict[str, Any] = Field(default_factory=dict)


def select_primary_violation(violations: List[Violation]) -> Optional[Violation]:
    if not violations:
        return None

    priority = {violation_type: index for index, violation_type in enumerate(VIOLATION_PRIORITY)}
    return min(
        violations,
        key=lambda violation: (
            priority.get(violation.violation_type, len(VIOLATION_PRIORITY)),
            min(violation.evidence_steps or [10**9]),
            violation.violation_type,
        ),
    )
