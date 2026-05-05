from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.run import Run


class RunRepository:
    """Persistence access for run entities."""

    def create(self, db: Session, run: Run) -> Run:
        db.add(run)
        db.flush()
        return run

    def list_recent(self, db: Session, limit: int = 50) -> list[Run]:
        stmt: Select[tuple[Run]] = select(Run).order_by(Run.created_at.desc()).limit(limit)
        return db.execute(stmt).scalars().all()

    def get_by_run_id(self, db: Session, run_id: str) -> Run | None:
        stmt: Select[tuple[Run]] = select(Run).where(Run.run_id == run_id)
        return db.execute(stmt).scalar_one_or_none()

    def get_latest_by_session_id(self, db: Session, session_id: str) -> Run | None:
        stmt: Select[tuple[Run]] = (
            select(Run)
            .where(Run.session_id == session_id)
            .order_by(Run.created_at.desc())
            .limit(1)
        )
        return db.execute(stmt).scalar_one_or_none()

    def update_status(self, db: Session, run: Run, status: str) -> Run:
        run.status = status
        db.add(run)
        db.flush()
        return run

    def update_risk_conclusion(
        self,
        db: Session,
        run_id: str,
        final_risk_level: str | None,
        disposition: str | None,
    ) -> Run | None:
        run = self.get_by_run_id(db=db, run_id=run_id)
        if run is None:
            return None

        run.final_risk_level = final_risk_level
        run.disposition = disposition
        db.flush()
        return run


run_repository = RunRepository()
