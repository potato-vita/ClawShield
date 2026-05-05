from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.ids import generate_run_id
from app.models.run import Run
from app.repositories.run_repo import RunRepository, run_repository
from app.schemas.run import RunSummary


class RunService:
    """Run lifecycle and read/query operations."""

    def __init__(self, repository: RunRepository) -> None:
        self._repository = repository

    def initialize_run(
        self,
        db: Session,
        session_id: str | None,
        task_summary: str,
        task_type: str = "unknown",
    ) -> Run:
        run = Run(
            run_id=generate_run_id(),
            session_id=session_id,
            task_summary=task_summary,
            task_type=task_type,
            status="created",
            started_at=datetime.now(timezone.utc),
        )
        return self._repository.create(db=db, run=run)

    def list_runs(self, db: Session, limit: int = 50) -> list[RunSummary]:
        runs = self._repository.list_recent(db=db, limit=limit)
        return [self._to_summary(item) for item in runs]

    def get_run(self, db: Session, run_id: str) -> RunSummary | None:
        run = self._repository.get_by_run_id(db=db, run_id=run_id)
        if run is None:
            return None
        return self._to_summary(run)

    @staticmethod
    def _to_summary(run: Run) -> RunSummary:
        return RunSummary(
            run_id=run.run_id,
            session_id=run.session_id,
            task_summary=run.task_summary,
            task_type=run.task_type,
            status=run.status,
            final_risk_level=run.final_risk_level,
            disposition=run.disposition,
            started_at=run.started_at,
            ended_at=run.ended_at,
            created_at=run.created_at,
        )


run_service = RunService(repository=run_repository)
