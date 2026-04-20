from datetime import datetime

from pydantic import BaseModel


class ReportRead(BaseModel):
    report_id: str
    run_id: str
    overall_risk_level: str
    summary_json: dict
    trace_graph_json: dict
    evidence_text: str
    created_at: datetime

    model_config = {"from_attributes": True}
