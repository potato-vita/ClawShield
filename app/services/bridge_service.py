from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import AppError, BadRequestError, NotFoundError, RuntimePipelineError
from app.gateway.gateway_manager import gateway_manager
from app.repositories.run_repo import run_repository
from app.schemas.tool_call import ActionRequest, ToolCallRequest, ToolResultPayload
from app.services.audit_service import audit_service
from app.services.guardrails_service import guardrails_service

logger = logging.getLogger(__name__)


class BridgeService:
    """Orchestrate tool-call pipeline used by OpenClaw bridge and demo runner."""

    @staticmethod
    def _resolve_action_type(payload: ToolCallRequest) -> str:
        tool_lower = payload.tool_id.lower()

        if "http" in tool_lower or "url" in payload.arguments:
            return "http"
        if "env" in tool_lower or "env_key" in payload.arguments or "key" in payload.arguments:
            return "env_read"
        if "file" in tool_lower or "path" in payload.arguments or "file_path" in payload.arguments:
            return "file_read"
        return "tool_call"

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
        )

        try:
            decision = guardrails_service.evaluate_tool_call(db=db, payload=payload)
            action_request = ActionRequest(
                run_id=payload.run_id,
                tool_call_id=payload.tool_call_id,
                tool_id=payload.tool_id,
                action_type=self._resolve_action_type(payload),  # type: ignore[arg-type]
                arguments=payload.arguments,
                task_type=decision.task_type,
                semantic_decision=decision.decision,
                semantic_reason=decision.semantic_reason,
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
        logger.info(
            "bridge_service.tool_call.done run_id=%s tool_call_id=%s decision=%s status=%s",
            payload.run_id,
            payload.tool_call_id,
            response_payload["decision"],
            response_payload["execution_status"],
        )
        return response_payload

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

