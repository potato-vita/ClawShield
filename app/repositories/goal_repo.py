from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.task_goal import TaskGoal


class GoalRepository:
    """Persistence access for task goal entities."""

    def create(self, db: Session, goal: TaskGoal) -> TaskGoal:
        db.add(goal)
        db.flush()
        return goal

    def get_latest_by_run_id(self, db: Session, run_id: str) -> TaskGoal | None:
        stmt: Select[tuple[TaskGoal]] = (
            select(TaskGoal)
            .where(TaskGoal.run_id == run_id)
            .order_by(TaskGoal.created_at.desc())
            .limit(1)
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_by_goal_id(self, db: Session, goal_id: str) -> TaskGoal | None:
        stmt: Select[tuple[TaskGoal]] = select(TaskGoal).where(TaskGoal.goal_id == goal_id).limit(1)
        return db.execute(stmt).scalar_one_or_none()


goal_repository = GoalRepository()
