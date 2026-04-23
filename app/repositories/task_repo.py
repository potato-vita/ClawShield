from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.task import Task


class TaskRepository:
    """Persistence access for task entities."""

    def create(self, db: Session, task: Task) -> Task:
        db.add(task)
        db.flush()
        return task

    def list_recent(self, db: Session, limit: int = 50) -> list[Task]:
        stmt: Select[tuple[Task]] = select(Task).order_by(Task.created_at.desc()).limit(limit)
        return db.execute(stmt).scalars().all()

    def get_by_run_id(self, db: Session, run_id: str) -> list[Task]:
        stmt: Select[tuple[Task]] = select(Task).where(Task.run_id == run_id).order_by(Task.created_at.asc())
        return db.execute(stmt).scalars().all()

    def get_latest_by_run_id(self, db: Session, run_id: str) -> Task | None:
        stmt: Select[tuple[Task]] = (
            select(Task).where(Task.run_id == run_id).order_by(Task.created_at.desc()).limit(1)
        )
        return db.execute(stmt).scalar_one_or_none()


task_repository = TaskRepository()
