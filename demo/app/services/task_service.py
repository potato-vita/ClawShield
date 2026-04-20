from sqlalchemy.orm import Session

from app.models.db_models import RunDB


class TaskService:
    def __init__(self, db: Session):
        self.db = db

    def dashboard_summary(self) -> dict:
        runs = self.db.query(RunDB).all()
        total = len(runs)
        high_risk = len([r for r in runs if r.overall_risk_level in {"high", "critical"}])
        finished = len([r for r in runs if r.status == "finished"])
        running = len([r for r in runs if r.status == "running"])
        return {
            "total_runs": total,
            "high_risk_runs": high_risk,
            "finished_runs": finished,
            "running_runs": running,
        }
