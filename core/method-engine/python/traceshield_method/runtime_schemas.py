from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class RuntimeIntentFrame(BaseModel):
    task_goal: str = ""
    allowed_actions: List[str] = Field(default_factory=list)
    allowed_resources: List[str] = Field(default_factory=list)
    forbidden_actions: List[str] = Field(default_factory=list)
    forbidden_resources: List[str] = Field(default_factory=list)
    sensitive_resources: List[str] = Field(default_factory=list)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    authorized_risky_calls: List[Dict[str, Any]] = Field(default_factory=list)


class RuntimeEvent(BaseModel):
    step_id: int = Field(gt=0)
    tool_name: str
    tool_kind: str = "unknown"
    semantic_action_hint: Optional[str] = None
    target_resource_hint: Optional[str] = None
    args: Dict[str, Any] = Field(default_factory=dict)
    observation: Optional[str] = None
    observation_hash: Optional[str] = None
    status: Literal["pending", "completed", "error", "unknown"] = "unknown"


class RuntimeParams(BaseModel):
    session_id: str
    run_id: str
    trace_id: str
    current_step_seq: int = Field(gt=0)
    profile: str = "balanced"
    profile_version: str = "balanced-v1"
    method_version: str = "phase0-baseline"
    semantic_schema_version: Literal["v1"] = "v1"
    intent_frame: RuntimeIntentFrame
    events: List[RuntimeEvent]
    trace_completeness: str = "complete"


class RuntimeRequest(BaseModel):
    protocol_version: Literal["v1"]
    request_id: str
    method: Literal["health", "evaluate_runtime_trace", "detect_observation", "shutdown"]
    params: Optional[Dict[str, Any]] = None


class RuntimeError(BaseModel):
    code: str
    message: str


class RuntimeResponse(BaseModel):
    protocol_version: Literal["v1"] = "v1"
    request_id: str
    ok: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[RuntimeError] = None
