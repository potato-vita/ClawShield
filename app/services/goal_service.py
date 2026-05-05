from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.core.ids import generate_goal_id
from app.models.task_goal import TaskGoal
from app.repositories.goal_repo import GoalRepository, goal_repository
from app.schemas.goal import GoalSummary

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTENT_RULES_PATH = PROJECT_ROOT / "configs" / "rules" / "intent_rules.yaml"


class GoalService:
    """Build and query deterministic task-goal contracts."""

    def __init__(self, repository: GoalRepository) -> None:
        self._repository = repository

    def create_goal_for_task(
        self,
        db: Session,
        run_id: str,
        user_input: str,
        task_type: str = "unknown",
        metadata: dict[str, Any] | None = None,
    ) -> TaskGoal:
        rules = self._load_intent_rules()
        task_intent = self._infer_task_intent(user_input=user_input, task_type=task_type, rules=rules)
        profile = rules["profiles"].get(task_intent) or rules["profiles"]["unknown"]

        goal = TaskGoal(
            goal_id=generate_goal_id(),
            run_id=run_id,
            task_intent=task_intent,
            objective_summary=self._build_objective_summary(user_input=user_input, task_intent=task_intent),
            allowed_action_types_json=list(profile.get("allowed_action_types", [])),
            allowed_tools_json=list(profile.get("allowed_tools", [])),
            allowed_resource_scopes_json=list(profile.get("allowed_resource_scopes", [])),
            expected_outputs_json=list(profile.get("expected_outputs", [])),
            forbidden_actions_json=list(profile.get("forbidden_actions", [])),
            forbidden_effects_json=list(profile.get("forbidden_effects", [])),
            risk_constraints_json=list(profile.get("risk_constraints", [])),
            confidence=float(profile.get("confidence", 0.5)),
            metadata_json={"rule_version": rules.get("version", "v1"), "task_type": task_type, **(metadata or {})},
        )
        return self._repository.create(db=db, goal=goal)

    def get_latest_by_run_id(self, db: Session, run_id: str) -> GoalSummary | None:
        goal = self._repository.get_latest_by_run_id(db=db, run_id=run_id)
        if goal is None:
            return None
        return self._to_summary(goal)

    @staticmethod
    def _build_objective_summary(user_input: str, task_intent: str) -> str:
        compact = " ".join(user_input.strip().split())
        if len(compact) > 160:
            compact = compact[:157] + "..."
        return f"{task_intent}: {compact}"

    @staticmethod
    def _infer_task_intent(user_input: str, task_type: str, rules: dict[str, Any]) -> str:
        text = f"{task_type} {user_input}".lower()
        for intent_name, spec in rules.get("intent_detection", {}).items():
            keywords = spec.get("keywords", [])
            if any(keyword.lower() in text for keyword in keywords):
                return intent_name
        return "unknown"

    @staticmethod
    def _load_intent_rules() -> dict[str, Any]:
        with INTENT_RULES_PATH.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        if not isinstance(loaded, dict):
            raise RuntimeError("intent_rules.yaml must be a mapping")
        if "profiles" not in loaded:
            raise RuntimeError("intent_rules.yaml missing profiles")
        return loaded

    @staticmethod
    def _to_summary(goal: TaskGoal) -> GoalSummary:
        return GoalSummary(
            goal_id=goal.goal_id,
            run_id=goal.run_id,
            task_intent=goal.task_intent,
            objective_summary=goal.objective_summary,
            allowed_action_types=list(goal.allowed_action_types_json),
            allowed_tools=list(goal.allowed_tools_json),
            allowed_resource_scopes=list(goal.allowed_resource_scopes_json),
            expected_outputs=list(goal.expected_outputs_json),
            forbidden_actions=list(goal.forbidden_actions_json),
            forbidden_effects=list(goal.forbidden_effects_json),
            risk_constraints=list(goal.risk_constraints_json),
            confidence=goal.confidence,
            created_at=goal.created_at,
        )


goal_service = GoalService(repository=goal_repository)
