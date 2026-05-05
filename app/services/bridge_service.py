from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError, BadRequestError, NotFoundError, RuntimePipelineError
from app.gateway.action_intent import infer_action_intent, infer_tool_call_intent
from app.gateway.gateway_manager import gateway_manager
from app.repositories.goal_repo import goal_repository
from app.repositories.run_repo import run_repository
from app.repositories.step_repo import step_repository
from app.schemas.tool_call import ActionRequest, ToolCallRequest, ToolResultPayload
from app.services.alignment_service import alignment_service
from app.services.audit_service import audit_service
from app.services.guardrails_service import guardrails_service
from app.services.resource_impact_service import resource_impact_service
from app.services.task_state_service import task_state_service

logger = logging.getLogger(__name__)


class BridgeService:
    """Orchestrate tool-call pipeline used by OpenClaw bridge and demo runner."""

    def process_tool_call(self, db: Session, payload: ToolCallRequest) -> dict[str, Any]:
        logger.info(
            "bridge_service.tool_call.start run_id=%s tool_call_id=%s tool_id=%s",
            payload.run_id,
            payload.tool_call_id,
            payload.tool_id,
        )
        run = run_repository.get_by_run_id(db=db, run_id=payload.run_id)
        if run is None:
            raise NotFoundError(
                message="run not found",
                details={"run_id": payload.run_id},
                error_code="RUN_NOT_FOUND",
            )

        audit_service.record_event(
            db=db,
            run_id=payload.run_id,
            session_id=run.session_id,
            event_type="tool_call_requested",
            event_stage="semantic_guard",
            actor_type="model",
            tool_id=payload.tool_id,
            input_summary=payload.model_reason,
            status="recorded",
            tool_call_id=payload.tool_call_id,
            step_id=payload.step_id,
        )
        active_step = task_state_service.ensure_active_step_for_tool_call(db=db, run_id=payload.run_id)
        if active_step.state != "tool_planning":
            transitioned = task_state_service.transition_step(
                db=db,
                run_id=payload.run_id,
                target_state="tool_planning",
                reason="tool_call_received",
            )
            if transitioned.step_id != active_step.step_id:
                audit_service.record_event(
                    db=db,
                    run_id=payload.run_id,
                    session_id=run.session_id,
                    event_type="task_step_transitioned",
                    event_stage="state_management",
                    actor_type="system",
                    status="recorded",
                    output_summary=f"from={active_step.state}; to={transitioned.state}; step_id={transitioned.step_id}",
                )
            active_step = transitioned

        try:
            tool_intent = infer_tool_call_intent(
                run_id=payload.run_id,
                tool_call_id=payload.tool_call_id,
                tool_id=payload.tool_id,
                arguments=payload.arguments,
                step_id=payload.step_id,
                model_reason=payload.model_reason,
            )
            resource_impact = resource_impact_service.assess(tool_intent, payload.arguments)
            goal = goal_repository.get_latest_by_run_id(db=db, run_id=payload.run_id)
            step = step_repository.get_active_by_run_id(db=db, run_id=payload.run_id)
            causal_context = task_state_service.build_causal_explanation(
                goal=goal,
                step=step,
                intent=tool_intent,
                impact=resource_impact,
            )
            alignment = alignment_service.evaluate(
                db=db,
                goal=goal,
                step=step,
                intent=tool_intent,
                impact=resource_impact,
                model_reason=payload.model_reason,
                justification_ref=(causal_context.get("justification_ref") if isinstance(causal_context.get("justification_ref"), str) else None),
                counterfactual_note=(causal_context.get("counterfactual_note") if isinstance(causal_context.get("counterfactual_note"), str) else None),
                enforce_justification=True,
            )
            alignment_reason = self._compose_alignment_reason(
                reasons=alignment.reasons,
                justification_ref=alignment.justification_ref,
            )
            audit_service.record_event(
                db=db,
                run_id=payload.run_id,
                session_id=run.session_id,
                event_type="alignment_evaluation_completed",
                event_stage="alignment",
                actor_type="system",
                tool_id=payload.tool_id,
                resource_type=resource_impact.resource_type,
                resource_id=resource_impact.resource_id,
                status="recorded",
                output_summary=f"decision={alignment.decision}; score={alignment.overall_score:.2f}",
                tool_call_id=payload.tool_call_id,
                step_id=(step.step_id if step else payload.step_id),
                alignment_score=alignment.overall_score,
                alignment_decision=alignment.decision,
                alignment_reason=alignment_reason,
                intended_effect=tool_intent.intended_effect,
                impact_level=resource_impact.impact_level,
                metadata_json={
                    "justification_ref": alignment.justification_ref,
                    "counterfactual_note": alignment.counterfactual_note,
                    "necessity_verdict": alignment.necessity_verdict,
                    "score_breakdown": alignment.score_breakdown,
                },
            )
            hard_block_codes = {
                "hard_forbidden_action",
                "hard_forbidden_effect",
                "hard_unknown_goal_high_risk_action",
                "hard_resource_scope_violation",
                "hard_redline_rule",
                "hard_state_action_violation",
                "hard_untrusted_upload",
            }
            exfiltration_blockable = resource_impact.exfiltration_risk and (
                goal is None or goal.task_intent in {"summary", "analysis", "qa", "file_process", "admin_op"}
            )
            should_alignment_block = (
                alignment.decision == "deny"
                and (
                    bool(set(alignment.hard_reason_codes).intersection(hard_block_codes))
                    or exfiltration_blockable
                    or resource_impact.impact_level == "critical"
                )
            )
            if should_alignment_block:
                audit_service.record_event(
                    db=db,
                    run_id=payload.run_id,
                    session_id=run.session_id,
                    event_type="alignment_blocked",
                    event_stage="alignment",
                    actor_type="system",
                    tool_id=payload.tool_id,
                    resource_type=resource_impact.resource_type,
                    resource_id=resource_impact.resource_id,
                    disposition="deny",
                    risk_level=alignment.risk_level,
                    status="blocked_by_alignment",
                    output_summary="tool call blocked before gateway execution",
                    tool_call_id=payload.tool_call_id,
                    step_id=(step.step_id if step else payload.step_id),
                    alignment_score=alignment.overall_score,
                    alignment_decision=alignment.decision,
                    alignment_reason=alignment_reason,
                    intended_effect=tool_intent.intended_effect,
                    impact_level=resource_impact.impact_level,
                    metadata_json={
                        "justification_ref": alignment.justification_ref,
                        "counterfactual_note": alignment.counterfactual_note,
                        "necessity_verdict": alignment.necessity_verdict,
                        "score_breakdown": alignment.score_breakdown,
                    },
                )
                return {
                    "run_id": payload.run_id,
                    "tool_call_id": payload.tool_call_id,
                    "decision": "deny",
                    "semantic_reason": "blocked by alignment evaluation",
                    "policy_reason": "alignment deny",
                    "disposition": "deny",
                    "evaluated_at": alignment.created_at.isoformat(),
                    "task_type": run.task_type,
                    "dialog_state": (step.state if step else "unknown"),
                    "execution_status": "blocked_by_alignment",
                    "resource_type": resource_impact.resource_type,
                    "resource_id": resource_impact.resource_id,
                    "risk_level": alignment.risk_level,
                    "matched_rules": alignment.matched_rules,
                    "explanations": alignment.reasons,
                    "resource_impact": resource_impact.model_dump(),
                    "alignment_score": alignment.overall_score,
                    "alignment_decision": alignment.decision,
                    "alignment_reasons": alignment.reasons,
                    "alignment_hard_reasons": alignment.hard_reason_codes,
                    "necessity_verdict": alignment.necessity_verdict,
                    "justification_ref": alignment.justification_ref,
                    "counterfactual_note": alignment.counterfactual_note,
                }
            decision = guardrails_service.evaluate_tool_call(db=db, payload=payload)
            action_type, normalized_arguments = infer_action_intent(
                tool_id=payload.tool_id,
                arguments=payload.arguments,
            )
            action_request = ActionRequest(
                run_id=payload.run_id,
                tool_call_id=payload.tool_call_id,
                tool_id=payload.tool_id,
                action_type=action_type,
                arguments=normalized_arguments,
                task_type=decision.task_type,
                semantic_decision=decision.decision,
                semantic_reason=decision.semantic_reason,
            )
            executing_step = task_state_service.transition_step(
                db=db,
                run_id=payload.run_id,
                target_state="tool_executing",
                reason="tool_call_gated",
            )
            if executing_step.step_id != active_step.step_id:
                audit_service.record_event(
                    db=db,
                    run_id=payload.run_id,
                    session_id=run.session_id,
                    event_type="task_step_transitioned",
                    event_stage="state_management",
                    actor_type="system",
                    status="recorded",
                    output_summary=f"from={active_step.state}; to={executing_step.state}; step_id={executing_step.step_id}",
                )
            action_result = gateway_manager.execute(db=db, request=action_request, session_id=run.session_id)
        except AppError:
            raise
        except RuntimeError as exc:
            raise BadRequestError(
                message=str(exc),
                error_code="TOOL_CALL_RUNTIME_ERROR",
                details={"run_id": payload.run_id, "tool_call_id": payload.tool_call_id},
            ) from exc
        except Exception as exc:
            raise RuntimePipelineError(
                message=f"tool-call pipeline failed: {exc}",
                error_code="TOOL_CALL_PIPELINE_ERROR",
                details={"run_id": payload.run_id, "tool_call_id": payload.tool_call_id},
            ) from exc

        response_payload = decision.model_dump()
        response_payload["decision"] = action_result.final_decision
        response_payload["disposition"] = action_result.disposition
        response_payload["policy_reason"] = (
            f"policy decision: {action_result.policy_decision}; "
            f"gateway execution status: {action_result.execution_status}; executor: {action_result.executor_name}"
        )
        response_payload["execution_status"] = action_result.execution_status
        response_payload["resource_type"] = action_result.resource_type
        response_payload["resource_id"] = action_result.resource_id
        response_payload["risk_level"] = action_result.risk_level
        response_payload["matched_rules"] = action_result.matched_rules
        response_payload["explanations"] = action_result.explanations
        response_payload["resource_impact"] = resource_impact.model_dump()
        response_payload["alignment_score"] = alignment.overall_score
        response_payload["alignment_decision"] = alignment.decision
        response_payload["alignment_reasons"] = alignment.reasons
        response_payload["alignment_hard_reasons"] = alignment.hard_reason_codes
        response_payload["necessity_verdict"] = alignment.necessity_verdict
        response_payload["justification_ref"] = alignment.justification_ref
        response_payload["counterfactual_note"] = alignment.counterfactual_note

        review_step = task_state_service.transition_step(
            db=db,
            run_id=payload.run_id,
            target_state="result_review",
            reason="tool_call_completed",
        )
        if review_step.state == "result_review":
            audit_service.record_event(
                db=db,
                run_id=payload.run_id,
                session_id=run.session_id,
                event_type="task_step_transitioned",
                event_stage="state_management",
                actor_type="system",
                status="recorded",
                output_summary=f"to={review_step.state}; step_id={review_step.step_id}",
            )
        logger.info(
            "bridge_service.tool_call.done run_id=%s tool_call_id=%s decision=%s status=%s",
            payload.run_id,
            payload.tool_call_id,
            response_payload["decision"],
            response_payload["execution_status"],
        )
        return response_payload

    @staticmethod
    def _compose_alignment_reason(reasons: list[str], justification_ref: str | None) -> str:
        base = "; ".join(reasons[:3]) if reasons else "alignment_checked"
        if justification_ref:
            return f"{base}; justification={justification_ref}"
        return base

    def process_tool_result(self, db: Session, payload: ToolResultPayload) -> dict[str, Any]:
        logger.info(
            "bridge_service.tool_result.start run_id=%s tool_call_id=%s tool_id=%s status=%s",
            payload.run_id,
            payload.tool_call_id,
            payload.tool_id,
            payload.execution_status,
        )
        run = run_repository.get_by_run_id(db=db, run_id=payload.run_id)
        if run is None:
            raise NotFoundError(
                message="run not found",
                details={"run_id": payload.run_id},
                error_code="RUN_NOT_FOUND",
            )

        try:
            audit_service.record_event(
                db=db,
                run_id=payload.run_id,
                session_id=run.session_id,
                event_type="tool_result_received",
                event_stage="result_review",
                actor_type="tool",
                tool_id=payload.tool_id,
                output_summary=payload.result_summary,
                status=payload.execution_status,
                tool_call_id=payload.tool_call_id,
            )
        except AppError:
            raise
        except Exception as exc:
            raise RuntimePipelineError(
                message=f"tool-result persistence failed: {exc}",
                error_code="TOOL_RESULT_FAILED",
                details={"run_id": payload.run_id, "tool_call_id": payload.tool_call_id},
            ) from exc

        logger.info(
            "bridge_service.tool_result.done run_id=%s tool_call_id=%s status=%s",
            payload.run_id,
            payload.tool_call_id,
            payload.execution_status,
        )
        return {
            "accepted": True,
            "output_tags": [payload.execution_status],
            "additional_risk_hits": [],
            "persist_status": "recorded",
        }


bridge_service = BridgeService()
