from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.run import Run
from app.repositories.run_repo import run_repository
from app.repositories.task_repo import task_repository
from app.schemas.tool_call import ToolCallDecision, ToolCallRequest
from app.services.audit_service import audit_service
from guardrails.actions.audit_actions import build_semantic_events
from guardrails.actions.policy_actions import evaluate_candidate_action
from guardrails.actions.task_context_actions import get_task_context


class GuardrailsService:
    """Minimal semantic guardrail service for candidate tool-call evaluation."""

    def __init__(self) -> None:
        self._config_path = Path(__file__).resolve().parents[2] / "guardrails" / "config.yml"

    def _load_config(self) -> dict:
        if not self._config_path.exists():
            raise RuntimeError(f"guardrails config not found: {self._config_path}")

        with self._config_path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}

        if not isinstance(loaded, dict):
            raise RuntimeError("guardrails config must be a mapping")
        return loaded

    def status(self) -> dict:
        try:
            config = self._load_config()
        except RuntimeError as exc:
            return {
                "state": "error",
                "detail": str(exc),
            }

        rails = config.get("rails", {})
        actions = config.get("actions", [])
        if not rails:
            return {
                "state": "error",
                "detail": "rails section missing",
            }

        return {
            "state": "ready",
            "detail": "minimal guardrails profile loaded",
            "registered_rails": sorted(rails.keys()),
            "registered_actions": len(actions) if isinstance(actions, list) else 0,
        }

    @staticmethod
    def _infer_task_type_from_text(user_input: str) -> str:
        text = user_input.lower()
        analysis_keywords = [
            "analy",
            "summar",
            "explain",
            "分析",
            "总结",
            "归纳",
        ]
        if any(token in text for token in analysis_keywords):
            return "analysis"
        return "general"

    def _build_context(self, db: Session, run: Run) -> dict:
        latest_task = task_repository.get_latest_by_run_id(db=db, run_id=run.run_id)
        user_input = latest_task.user_input if latest_task else (run.task_summary or "")
        normalized_task_type = (run.task_type or "").strip().lower()

        if normalized_task_type in {"", "unknown"}:
            inferred = self._infer_task_type_from_text(user_input)
            run.task_type = inferred
            task_type = inferred
        else:
            task_type = normalized_task_type

        return get_task_context(run_id=run.run_id, task_type=task_type, run_status=run.status)

    def evaluate_tool_call(self, db: Session, payload: ToolCallRequest) -> ToolCallDecision:
        _ = self._load_config()

        run = run_repository.get_by_run_id(db=db, run_id=payload.run_id)
        if run is None:
            raise NotFoundError(
                message="run not found",
                details={"run_id": payload.run_id},
                error_code="RUN_NOT_FOUND",
            )

        context = self._build_context(db=db, run=run)
        evaluation = evaluate_candidate_action(
            task_type=context["task_type"],
            tool_id=payload.tool_id,
            dialog_state=context["dialog_state"],
        )

        semantic_decision = str(evaluation["semantic_decision"])
        semantic_reason = str(evaluation["semantic_reason"])
        disposition = "block" if semantic_decision == "deny" else semantic_decision

        semantic_events = build_semantic_events(
            run_id=payload.run_id,
            task_type=context["task_type"],
            dialog_state=context["dialog_state"],
            decision=semantic_decision,
            reason=semantic_reason,
        )

        for item in semantic_events:
            audit_service.record_event(
                db=db,
                run_id=payload.run_id,
                session_id=run.session_id,
                event_type=str(item["event_type"]),
                event_stage=str(item.get("event_stage", "semantic_guard")),
                actor_type="system",
                input_summary=str(item.get("input_summary") or ""),
                semantic_decision=item.get("semantic_decision"),
                status="recorded",
            )

        return ToolCallDecision(
            run_id=payload.run_id,
            tool_call_id=payload.tool_call_id,
            decision=semantic_decision,  # type: ignore[arg-type]
            semantic_reason=semantic_reason,
            policy_reason=None,
            disposition=disposition,
            evaluated_at=datetime.now(timezone.utc),
            task_type=context["task_type"],
            dialog_state=context["dialog_state"],
        )


guardrails_service = GuardrailsService()
