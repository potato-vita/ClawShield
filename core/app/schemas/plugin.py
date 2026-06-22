from datetime import datetime
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, Field, model_validator


Decision = Literal["ALLOW", "WARN", "ASK", "BLOCK"]
RiskLevel = Literal["low", "medium", "high", "critical"]


class AuditContext(BaseModel):
    user_goal: str | None = None
    recent_messages: list[Any] = Field(default_factory=list)
    recent_message_hashes: list[str] = Field(default_factory=list)
    workspace_root: str | None = None
    username: str | None = None
    department_name: str | None = None
    host_name: str | None = None
    ip_address: str | None = None


class AuditToolCallRequest(BaseModel):
    request_id: str | None = None
    schema_version: str = "v1"
    session_id: str
    run_id: str
    trace_id: str
    tool_call_id: str
    tool_name: str
    tool_kind: str = "unknown"
    params: dict[str, Any] = Field(default_factory=dict)
    raw_params: dict[str, Any] = Field(default_factory=dict)
    param_summary: dict[str, Any] = Field(default_factory=dict)
    resource_hint: str | None = None
    risk_hint: str | None = None
    context: AuditContext = Field(default_factory=AuditContext)
    timestamp: datetime | int | float | str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_params(cls, value: Any) -> Any:
        if isinstance(value, dict):
            data = dict(value)
            if "raw_params" not in data and "params" in data:
                data["raw_params"] = data["params"]
            if "params" not in data and "raw_params" in data:
                data["params"] = data["raw_params"]
            return data
        return value


class ApprovalInfo(BaseModel):
    approval_id: str
    title: str
    description: str
    default_action: Literal["ALLOW", "BLOCK"] = "BLOCK"
    timeout_ms: int = 30_000


class EvidenceItem(BaseModel):
    type: str
    key: str | None = None
    value: str | None = None
    description: str | None = None


class AuditDecisionResponse(BaseModel):
    decision: Decision
    risk_level: RiskLevel
    risk_score: float
    reason: str
    matched_rules: list[str] = Field(default_factory=list)
    modified_params: dict[str, Any] | None = None
    approval: ApprovalInfo | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    fallback_used: bool = False


class TraceEvent(BaseModel):
    event_id: str
    schema_version: str = "v1"
    event_type: str = Field(validation_alias=AliasChoices("event_type", "type"))
    session_id: str | None = None
    run_id: str | None = None
    trace_id: str | None = None
    timestamp: datetime | int | float | str
    plugin_id: str | None = None
    gateway_id: str | None = None
    mode: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)

    @property
    def type(self) -> str:
        return self.event_type


class EventBatchRequest(BaseModel):
    events: list[dict[str, Any]]


class EventBatchResponse(BaseModel):
    success: bool
    accepted: int
    duplicated: int
    failed: int
