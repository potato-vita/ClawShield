from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import Session

from app.core.ids import generate_goal_id
from app.models.task_goal import TaskGoal
from app.repositories.goal_repo import GoalRepository, goal_repository
from app.schemas.goal import TaskGoalSummary
from app.settings import PROJECT_ROOT


@dataclass(frozen=True)
class GoalContract:
    task_intent: str
    objective_summary: str
    allowed_action_types: list[str]
    allowed_tools: list[str]
    allowed_resource_scopes: list[str]
    forbidden_actions: list[str]
    forbidden_effects: list[str]
    confidence: float


class GoalService:
    """Rule-based task goal contract generation and persistence."""

    def __init__(self, repository: GoalRepository) -> None:
        self._repository = repository
        self._rules_path = PROJECT_ROOT / "configs" / "rules" / "intent_rules.yaml"

    def create_goal_for_task(self, db: Session, run_id: str, user_input: str) -> TaskGoal:
        contract = self.build_goal_contract(user_input=user_input)
        goal = TaskGoal(
            goal_id=generate_goal_id(),
            run_id=run_id,
            task_intent=contract.task_intent,
            objective_summary=contract.objective_summary,
            allowed_action_types_json=list(contract.allowed_action_types),
            allowed_tools_json=list(contract.allowed_tools),
            allowed_resource_scopes_json=list(contract.allowed_resource_scopes),
            forbidden_actions_json=list(contract.forbidden_actions),
            forbidden_effects_json=list(contract.forbidden_effects),
            confidence=float(contract.confidence),
        )
        return self._repository.create(db=db, goal=goal)

    def get_goal_summary_by_run_id(self, db: Session, run_id: str) -> TaskGoalSummary | None:
        goal = self._repository.get_latest_by_run_id(db=db, run_id=run_id)
        if goal is None:
            return None
        return self._to_summary(goal)

    def build_goal_contract(self, user_input: str) -> GoalContract:
        text = (user_input or "").strip()
        lowered = text.lower()
        objective_summary = text[:200] if text else "(empty task)"

        rules = self._load_rules()
        rule_list = rules.get("rules")
        defaults = rules.get("defaults") if isinstance(rules.get("defaults"), dict) else {}

        if isinstance(rule_list, list):
            for rule in rule_list:
                if not isinstance(rule, dict):
                    continue

                intent = str(rule.get("intent") or "").strip()
                if not intent:
                    continue

                keywords = rule.get("keywords")
                if not isinstance(keywords, list) or not keywords:
                    continue

                if self._match_any_keyword(lowered=lowered, original=text, keywords=keywords):
                    return GoalContract(
                        task_intent=intent,
                        objective_summary=objective_summary,
                        allowed_action_types=self._get_list(rule, "allowed_action_types", defaults),
                        allowed_tools=self._get_list(rule, "allowed_tools", defaults),
                        allowed_resource_scopes=self._get_list(rule, "allowed_resource_scopes", defaults),
                        forbidden_actions=self._get_list(rule, "forbidden_actions", defaults),
                        forbidden_effects=self._get_list(rule, "forbidden_effects", defaults),
                        confidence=float(rule.get("confidence") or defaults.get("confidence") or 0.5),
                    )

        # Fallback: deterministic heuristics when no rule matches.
        inferred_intent = self._infer_intent_fallback(lowered)
        return GoalContract(
            task_intent=inferred_intent,
            objective_summary=objective_summary,
            allowed_action_types=[],
            allowed_tools=[],
            allowed_resource_scopes=[],
            forbidden_actions=[],
            forbidden_effects=[],
            confidence=0.5,
        )

    def _load_rules(self) -> dict[str, Any]:
        path = Path(self._rules_path)
        if not path.exists():
            return {}

        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}

        if not isinstance(loaded, dict):
            return {}
        return loaded

    @staticmethod
    def _get_list(rule: dict[str, Any], key: str, defaults: dict[str, Any]) -> list[str]:
        value = rule.get(key)
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        default_value = defaults.get(key)
        if isinstance(default_value, list):
            return [str(item) for item in default_value if str(item).strip()]
        return []

    @staticmethod
    def _match_any_keyword(*, lowered: str, original: str, keywords: list[Any]) -> bool:
        for raw in keywords:
            token = str(raw)
            if not token:
                continue
            token_lower = token.lower()
            if token_lower and token_lower in lowered:
                return True
            if token in original:
                return True
        return False

    @staticmethod
    def _infer_intent_fallback(lowered: str) -> str:
        if any(key in lowered for key in ["summar", "summary", "总结", "概括", "归纳"]):
            return "summary"
        if any(key in lowered for key in ["analy", "explain", "分析", "解释"]):
            return "analysis"
        if any(key in lowered for key in ["接口", "api", "http", "weather", "天气", "调用"]):
            return "external_invoke"
        if any(key in lowered for key in ["convert", "extract", "parse", "处理", "转换", "提取"]):
            return "file_process"
        if any(key in lowered for key in ["sudo", "rm ", "删除", "install", "apt "]):
            return "admin_op"
        if "?" in lowered or any(key in lowered for key in ["why", "how", "what", "什么", "为什么", "怎么"]):
            return "qa"
        return "unknown"

    @staticmethod
    def _to_summary(goal: TaskGoal) -> TaskGoalSummary:
        return TaskGoalSummary(
            goal_id=goal.goal_id,
            run_id=goal.run_id,
            task_intent=goal.task_intent,
            objective_summary=goal.objective_summary,
            allowed_action_types=list(goal.allowed_action_types_json or []),
            allowed_tools=list(goal.allowed_tools_json or []),
            allowed_resource_scopes=list(goal.allowed_resource_scopes_json or []),
            forbidden_actions=list(goal.forbidden_actions_json or []),
            forbidden_effects=list(goal.forbidden_effects_json or []),
            confidence=float(goal.confidence),
            created_at=goal.created_at,
            updated_at=goal.updated_at,
        )


goal_service = GoalService(repository=goal_repository)
