from pydantic import BaseModel


class TaskSummary(BaseModel):
    run_id: str
    task_name: str
    status: str
    risk_level: str
