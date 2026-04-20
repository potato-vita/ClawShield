from pydantic import BaseModel, Field


class ExecutionContext(BaseModel):
    run_id: str
    task_id: str
    skill_id: str | None = None
    tool_id: str | None = None
    actor: str = "openclaw"
    trace_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class GatewayResponse(BaseModel):
    status: str
    message: str
    decision: str
    result: dict = Field(default_factory=dict)
    event_ids: list[str] = Field(default_factory=list)
