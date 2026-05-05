from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.task_step import TaskStep


class StepRepository:
    """Persistence access for task step entities."""

    def create(self, db: Session, step: TaskStep) -> TaskStep:
        db.add(step)
        db.flush()
        return step

    def get_active_by_run_id(self, db: Session, run_id: str) -> TaskStep | None:
        stmt: Select[tuple[TaskStep]] = (
            select(TaskStep)
            .where(TaskStep.run_id == run_id, TaskStep.status == "active")
            .order_by(TaskStep.created_at.desc())
            .limit(1)
        )
        return db.execute(stmt).scalar_one_or_none()

    def list_by_run_id(self, db: Session, run_id: str) -> list[TaskStep]:
        stmt: Select[tuple[TaskStep]] = select(TaskStep).where(TaskStep.run_id == run_id).order_by(TaskStep.created_at.asc())
        return db.execute(stmt).scalars().all()


step_repository = StepRepository()
