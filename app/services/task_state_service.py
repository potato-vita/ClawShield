from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.ids import generate_step_id
from app.models.task_goal import TaskGoal
from app.models.task_step import TaskStep
from app.repositories.step_repo import StepRepository, step_repository


class TaskStateService:
    """Manage task execution steps and current step retrieval."""

    def __init__(self, repository: StepRepository) -> None:
        self._repository = repository

    def initialize_first_step(self, db: Session, *, run_id: str, goal: TaskGoal) -> TaskStep:
        step = TaskStep(
            step_id=generate_step_id(),
            run_id=run_id,
            goal_id=goal.goal_id,
            step_index=1,
            step_name="initial_goal_step",
            objective=goal.objective_summary,
            status="active",
            is_current=True,
            allowed_action_types_json=list(goal.allowed_action_types_json or []),
            allowed_tools_json=list(goal.allowed_tools_json or []),
        )
        return self._repository.create(db=db, step=step)

    def get_current_step(self, db: Session, *, run_id: str) -> TaskStep | None:
        return self._repository.get_current_by_run_id(db=db, run_id=run_id)

    def transition_after_tool_call(
        self,
        db: Session,
        *,
        run_id: str,
        tool_id: str,
        final_decision: str,
        execution_status: str,
    ) -> tuple[TaskStep | None, TaskStep | None]:
        final_decision_norm = (final_decision or "").lower()
        execution_status_norm = (execution_status or "").lower()
        if final_decision_norm == "deny" or "blocked" in execution_status_norm:
            return None, None

        current = self._repository.get_current_by_run_id(db=db, run_id=run_id)
        if current is None:
            return None, None
        if (current.status or "").lower() != "active":
            return None, None

        current.is_current = False
        current.status = "completed"
        db.add(current)

        latest = self._repository.get_latest_by_run_id(db=db, run_id=run_id)
        next_index = 1 if latest is None else int(latest.step_index) + 1
        next_step = TaskStep(
            step_id=generate_step_id(),
            run_id=run_id,
            goal_id=current.goal_id,
            step_index=next_index,
            step_name=f"post_tool_{tool_id}",
            objective=f"Review output of `{tool_id}` and continue toward goal.",
            status="active",
            is_current=True,
            allowed_action_types_json=list(current.allowed_action_types_json or []),
            allowed_tools_json=list(current.allowed_tools_json or []),
        )
        created = self._repository.create(db=db, step=next_step)
        return current, created


task_state_service = TaskStateService(repository=step_repository)
