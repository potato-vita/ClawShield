from pydantic import BaseModel


class ReportCreate(BaseModel):
    session_id: str | None = None
    title: str = "TraceShield 安全分析报告"
    report_type: str = "security_summary"
    time_range: str = "7d"
