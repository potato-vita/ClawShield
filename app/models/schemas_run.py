from datetime import datetime

from pydantic import BaseModel, Field


class RunCreate(BaseModel):
    task_name: str
    description: str = ""
    skill_id: str | None = None
    actor: str = "openclaw"
    workspace_root: str | None = None


class RunRead(BaseModel):
    run_id: str
    task_name: str
    description: str
    status: str
    started_at: datetime | None
    ended_at: datetime | None
    workspace_root: str
    actor: str
    skill_id: str | None
    overall_risk_level: str

    model_config = {"from_attributes": True}


class ScenarioExecuteRequest(BaseModel):
    scenario_id: str = Field(description="normal|workspace_escape|sensitive_exfiltration")
