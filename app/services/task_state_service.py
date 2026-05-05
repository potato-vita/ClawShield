from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.models.task_goal import TaskGoal
from app.core.ids import generate_step_id
from app.models.task_step import TaskStep
from app.repositories.step_repo import StepRepository, step_repository
from app.schemas.impact import ResourceImpact
from app.schemas.intent import ToolCallIntent
from app.schemas.step import StepSummary

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_TRANSITIONS_PATH = PROJECT_ROOT / "configs" / "rules" / "state_transitions.yaml"


class TaskStateService:
    """Manage step-level task state and transition rules."""

    def __init__(self, repository: StepRepository) -> None:
        self._repository = repository

    def create_initial_step(
        self,
        db: Session,
        run_id: str,
        goal_id: str | None,
        task_intent: str,
        allowed_action_types: list[str],
    ) -> TaskStep:
        rules = self._load_rules()
        initial_state = str(rules.get("initial_state", "analyzing"))
        profile = self._state_profile(rules, initial_state)
        step_goal = f"Analyze goal intent '{task_intent}' and prepare safe tool usage."
        merged_actions = allowed_action_types or list(profile.get("allowed_action_types", []))

        step = TaskStep(
            step_id=generate_step_id(),
            run_id=run_id,
            goal_id=goal_id,
            state=initial_state,
            step_goal=step_goal,
            allowed_action_types_json=list(merged_actions),
            allowed_tools_json=list(profile.get("allowed_tools", [])),
            allowed_effects_json=list(profile.get("allowed_effects", [])),
            status="active",
            metadata_json={"source": "ingest"},
        )
        return self._repository.create(db=db, step=step)

    def ensure_active_step_for_tool_call(self, db: Session, run_id: str) -> TaskStep:
        active = self._repository.get_active_by_run_id(db=db, run_id=run_id)
        if active is not None:
            return active

        rules = self._load_rules()
        profile = self._state_profile(rules, "tool_planning")
        step = TaskStep(
            step_id=generate_step_id(),
            run_id=run_id,
            goal_id=None,
            state="tool_planning",
            step_goal="Plan required tool action for current run.",
            allowed_action_types_json=list(profile.get("allowed_action_types", [])),
            allowed_tools_json=list(profile.get("allowed_tools", [])),
            allowed_effects_json=list(profile.get("allowed_effects", [])),
            status="active",
            metadata_json={"source": "tool_call_autocreate"},
        )
        return self._repository.create(db=db, step=step)

    def transition_step(self, db: Session, run_id: str, target_state: str, reason: str | None = None) -> TaskStep:
        rules = self._load_rules()
        active = self._repository.get_active_by_run_id(db=db, run_id=run_id)
        if active is None:
            return self.ensure_active_step_for_tool_call(db=db, run_id=run_id)

        if active.state == target_state:
            return active

        allowed_targets = set(self._allowed_transitions(rules, active.state))
        if target_state not in allowed_targets:
            return active

        active.status = "completed"
        db.flush()

        profile = self._state_profile(rules, target_state)
        next_step = TaskStep(
            step_id=generate_step_id(),
            run_id=run_id,
            goal_id=active.goal_id,
            state=target_state,
            step_goal=f"State moved to {target_state}.",
            allowed_action_types_json=list(profile.get("allowed_action_types", [])),
            allowed_tools_json=list(profile.get("allowed_tools", [])),
            allowed_effects_json=list(profile.get("allowed_effects", [])),
            status="active",
            parent_step_id=active.step_id,
            metadata_json={"reason": reason} if reason else None,
        )
        return self._repository.create(db=db, step=next_step)

    def on_message(self, db: Session, run_id: str, actor_type: str, content: str) -> TaskStep:
        active = self._repository.get_active_by_run_id(db=db, run_id=run_id)
        if active is None:
            return self.ensure_active_step_for_tool_call(db=db, run_id=run_id)

        if actor_type == "user":
            if active.state in {"tool_executing", "result_review", "finished"}:
                return self.transition_step(
                    db=db,
                    run_id=run_id,
                    target_state="analyzing",
                    reason="user_message_reset",
                )
            return active

        metadata = dict(active.metadata_json or {})
        metadata["last_model_message"] = content[:200]
        active.metadata_json = metadata
        db.flush()
        return active

    def list_steps(self, db: Session, run_id: str) -> list[StepSummary]:
        return [self._to_summary(item) for item in self._repository.list_by_run_id(db=db, run_id=run_id)]

    @staticmethod
    def build_causal_explanation(
        goal: TaskGoal | None,
        step: TaskStep | None,
        intent: ToolCallIntent,
        impact: ResourceImpact,
    ) -> dict[str, str | bool | None]:
        goal_anchor = ""
        step_anchor = ""
        if goal is not None:
            objective = (goal.objective_summary or "").strip()
            if len(objective) > 140:
                objective = objective[:137] + "..."
            goal_anchor = f"{goal.goal_id}:{objective}"
        if step is not None:
            step_anchor = step.causal_anchor

        justification_ref = None
        if goal_anchor and step_anchor:
            justification_ref = f"goal[{goal_anchor}] -> step[{step_anchor}]"
        elif goal_anchor:
            justification_ref = f"goal[{goal_anchor}]"
        elif step_anchor:
            justification_ref = f"step[{step_anchor}]"

        counterfactual_note = TaskStateService._counterfactual_by_action(
            action_type=intent.action_type,
            impact=impact,
        )
        return {
            "justification_ref": justification_ref,
            "counterfactual_note": counterfactual_note,
            "justification_present": bool(justification_ref),
        }

    @staticmethod
    def _counterfactual_by_action(action_type: str, impact: ResourceImpact) -> str:
        if action_type == "file_read":
            return "若不读取该文件，模型可能缺少完成当前步骤所需上下文，可先尝试使用已获得信息。"
        if action_type == "http":
            if (impact.domain_trust_level or "") == "untrusted":
                return "若不发起该外部请求，可优先使用本地信息或可信源，避免向不可信域名暴露数据。"
            return "若不发起该请求，可先验证本地信息是否足够，再决定是否访问外部接口。"
        if action_type == "env_read":
            return "若不读取环境变量，可先判断是否存在非敏感替代参数，减少凭证暴露面。"
        return "若不执行该工具，可先评估是否有更低风险步骤可达到同一目标。"

    @staticmethod
    def _load_rules() -> dict[str, Any]:
        with STATE_TRANSITIONS_PATH.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        if not isinstance(loaded, dict):
            raise RuntimeError("state_transitions.yaml must be a mapping")
        return loaded

    @staticmethod
    def _state_profile(rules: dict[str, Any], state: str) -> dict[str, Any]:
        profiles = rules.get("state_profiles", {})
        profile = profiles.get(state, {})
        if not isinstance(profile, dict):
            return {}
        return profile

    @staticmethod
    def _allowed_transitions(rules: dict[str, Any], state: str) -> list[str]:
        transitions = rules.get("allowed_transitions", {})
        allowed = transitions.get(state, [])
        if isinstance(allowed, list):
            return [str(item) for item in allowed]
        return []

    @staticmethod
    def _to_summary(step: TaskStep) -> StepSummary:
        return StepSummary(
            step_id=step.step_id,
            run_id=step.run_id,
            goal_id=step.goal_id,
            state=step.state,
            step_goal=step.step_goal,
            allowed_action_types=list(step.allowed_action_types_json),
            allowed_tools=list(step.allowed_tools_json),
            allowed_effects=list(step.allowed_effects_json),
            parent_step_id=step.parent_step_id,
            status=step.status,
            created_at=step.created_at,
            updated_at=step.updated_at,
        )


task_state_service = TaskStateService(repository=step_repository)
