from sqlalchemy.orm import Session

from app.core.report_engine import ReportEngine
from app.models.db_models import ReportDB


class ReportService:
    def __init__(self, db: Session, export_dir: str):
        self.engine = ReportEngine(db=db, export_dir=export_dir)
        self.db = db

    def generate(self, run_id: str, overall_risk_level: str, findings: list[dict], trace_graph: dict) -> ReportDB:
        return self.engine.generate(
            run_id=run_id,
            overall_risk_level=overall_risk_level,
            findings=findings,
            trace_graph=trace_graph,
        )

    def get_by_run(self, run_id: str) -> ReportDB | None:
        return (
            self.db.query(ReportDB)
            .filter(ReportDB.run_id == run_id)
            .order_by(ReportDB.created_at.desc())
            .first()
        )
