from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.gateway.path_utils import normalize_file_resource_id
from app.repositories.goal_repo import GoalRepository, goal_repository
from app.repositories.step_repo import StepRepository, step_repository
from app.schemas.tool_call import ActionType


@dataclass(frozen=True)
class AlignmentEvaluation:
    alignment_score: float
    alignment_decision: str
    alignment_reason: str
    intended_effect: str


class AlignmentService:
    """Evaluate whether a tool call is aligned with the run goal contract."""

    def __init__(self, goal_repo: GoalRepository, step_repo: StepRepository) -> None:
        self._goal_repo = goal_repo
        self._step_repo = step_repo

    def evaluate(
        self,
        db: Session,
        *,
        run_id: str,
        tool_id: str,
        action_type: ActionType,
        arguments: dict[str, Any],
        model_reason: str | None,
        raw_context: dict[str, Any] | None,
    ) -> AlignmentEvaluation:
        goal = self._goal_repo.get_latest_by_run_id(db=db, run_id=run_id)
        step = self._step_repo.get_current_by_run_id(db=db, run_id=run_id)
        intended_effect = self._infer_intended_effect(tool_id=tool_id, action_type=action_type, arguments=arguments)

        if goal is None:
            return AlignmentEvaluation(
                alignment_score=0.5,
                alignment_decision="warn",
                alignment_reason="no goal contract found for this run",
                intended_effect=intended_effect,
            )

        score = 1.0
        reasons: list[str] = []

        allowed_action_types = set(goal.allowed_action_types_json or [])
        allowed_tools = set(goal.allowed_tools_json or [])
        forbidden_actions = set(goal.forbidden_actions_json or [])
        forbidden_effects = set(goal.forbidden_effects_json or [])

        if allowed_action_types and action_type not in allowed_action_types:
            score -= 0.45
            reasons.append(f"action_type `{action_type}` not in allowed_action_types")

        if allowed_tools and tool_id not in allowed_tools:
            score -= 0.35
            reasons.append(f"tool `{tool_id}` not in allowed_tools")

        if "shell_exec" in forbidden_actions and self._is_shell_like(tool_id=tool_id, arguments=arguments):
            score -= 0.5
            reasons.append("shell-like operation violates forbidden_actions")

        if intended_effect in forbidden_effects:
            score -= 0.55
            reasons.append(f"intended_effect `{intended_effect}` in forbidden_effects")

        if step is not None:
            step_allowed_actions = set(step.allowed_action_types_json or [])
            step_allowed_tools = set(step.allowed_tools_json or [])
            if step_allowed_actions and action_type not in step_allowed_actions:
                score -= 0.35
                reasons.append(f"action_type `{action_type}` violates current step `{step.step_name}`")
            if step_allowed_tools and tool_id not in step_allowed_tools:
                score -= 0.25
                reasons.append(f"tool `{tool_id}` violates current step `{step.step_name}`")

        if not (model_reason or "").strip():
            score -= 0.1
            reasons.append("missing model_reason")

        if self._looks_exfiltration(raw_context=raw_context, arguments=arguments):
            score -= 0.25
            reasons.append("payload/context indicates potential exfiltration")

        score = max(0.0, min(1.0, score))
        if score < 0.35:
            decision = "deny"
        elif score < 0.7:
            decision = "warn"
        else:
            decision = "allow"

        reason_text = "; ".join(reasons) if reasons else "goal/action/effect matched"
        return AlignmentEvaluation(
            alignment_score=score,
            alignment_decision=decision,
            alignment_reason=reason_text,
            intended_effect=intended_effect,
        )

    @staticmethod
    def _is_shell_like(tool_id: str, arguments: dict[str, Any]) -> bool:
        if (tool_id or "").lower() in {"exec", "shell", "terminal"}:
            return True
        command = str(arguments.get("command") or "").lower()
        return any(token in command for token in ("bash", "sh ", "sudo", "rm ", "chmod ", "curl ", "wget "))

    @staticmethod
    def _looks_exfiltration(raw_context: dict[str, Any] | None, arguments: dict[str, Any]) -> bool:
        context_text = str(raw_context or "").lower()
        arg_text = str(arguments).lower()
        hints = ("upload", "exfil", "send", "发送", "上传", "外发")
        return any(token in context_text or token in arg_text for token in hints)

    @staticmethod
    def _infer_intended_effect(*, tool_id: str, action_type: ActionType, arguments: dict[str, Any]) -> str:
        tool_lower = (tool_id or "").lower()
        if action_type == "env_read":
            return "read_secret"

        if action_type == "http":
            method = str(arguments.get("method") or "").upper()
            url_text = str(arguments.get("url") or "").lower()
            body_text = str(arguments.get("data") or arguments.get("body") or "").lower()
            if method in {"POST", "PUT", "PATCH"} or "upload" in url_text or body_text:
                return "external_upload"
            return "external_query"

        if action_type == "file_read":
            path = normalize_file_resource_id(str(arguments.get("file_path") or arguments.get("path") or ""))
            if path.startswith("./workspace/") or path == "./workspace":
                return "workspace_read"
            return "out_of_scope_read"

        if tool_lower in {"exec", "shell", "terminal"}:
            return "shell_exec"

        return "tool_call"


alignment_service = AlignmentService(goal_repo=goal_repository, step_repo=step_repository)
