from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.gateway.executors.base import BaseExecutor
from app.gateway.executors.env_executor import EnvExecutor
from app.gateway.executors.file_executor import FileExecutor
from app.gateway.executors.http_executor import HttpExecutor
from app.gateway.executors.tool_executor import ToolExecutor
from app.gateway.interceptors.base import BaseInterceptor
from app.gateway.interceptors.env_read_interceptor import EnvReadInterceptor
from app.gateway.interceptors.file_read_interceptor import FileReadInterceptor
from app.gateway.interceptors.http_interceptor import HttpInterceptor
from app.gateway.interceptors.tool_call_interceptor import ToolCallInterceptor
from app.policy.engine import PolicyEngine, policy_engine
from app.schemas.tool_call import ActionRequest, ActionResult
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)


class GatewayManager:
    """Coordinate interception and execution for all runtime actions."""

    def __init__(self, engine: PolicyEngine | None = None) -> None:
        self._policy_engine = engine or policy_engine
        self._interceptors: dict[str, BaseInterceptor] = {
            "tool_call": ToolCallInterceptor(),
            "http": HttpInterceptor(),
            "file_read": FileReadInterceptor(),
            "env_read": EnvReadInterceptor(),
        }
        self._executors: dict[str, BaseExecutor] = {
            "tool_call": ToolExecutor(),
            "http": HttpExecutor(),
            "file_read": FileExecutor(),
            "env_read": EnvExecutor(),
        }

    def execute(self, db: Session, request: ActionRequest, session_id: str | None = None) -> ActionResult:
        logger.info(
            "gateway.execute.start run_id=%s tool_call_id=%s tool_id=%s action_type=%s",
            request.run_id,
            request.tool_call_id,
            request.tool_id,
            request.action_type,
        )
        interceptor = self._interceptors[request.action_type]
        executor = self._executors[request.action_type]

        intercepted = interceptor.intercept(request)

        policy_eval = self._policy_engine.evaluate(
            task_type=request.task_type,
            tool_id=request.tool_id,
            resource_type=intercepted.resource_type,
            resource_id=intercepted.resource_id,
        )

        audit_service.record_event(
            db=db,
            run_id=request.run_id,
            session_id=session_id,
            event_type="policy_check_completed",
            event_stage="policy_eval",
            actor_type="system",
            tool_id=request.tool_id,
            resource_type=intercepted.resource_type,
            resource_id=intercepted.resource_id,
            semantic_decision=request.semantic_decision,
            policy_decision=policy_eval.decision,
            risk_level=policy_eval.risk_level,
            disposition=policy_eval.disposition,
            status="recorded",
        )

        for matched in policy_eval.matched_rules:
            audit_service.record_event(
                db=db,
                run_id=request.run_id,
                session_id=session_id,
                event_type="risk_rule_matched",
                event_stage="policy_eval",
                actor_type="system",
                tool_id=request.tool_id,
                resource_type=intercepted.resource_type,
                resource_id=intercepted.resource_id,
                semantic_decision=request.semantic_decision,
                policy_decision=matched.decision,
                risk_level=matched.risk_level,
                disposition=policy_eval.disposition,
                input_summary=matched.reason,
                status="recorded",
            )

        audit_service.record_event(
            db=db,
            run_id=request.run_id,
            session_id=session_id,
            event_type="disposition_applied",
            event_stage="policy_eval",
            actor_type="system",
            tool_id=request.tool_id,
            resource_type=intercepted.resource_type,
            resource_id=intercepted.resource_id,
            semantic_decision=request.semantic_decision,
            policy_decision=policy_eval.decision,
            risk_level=policy_eval.risk_level,
            disposition=policy_eval.disposition,
            status="recorded",
        )

        audit_service.record_event(
            db=db,
            run_id=request.run_id,
            session_id=session_id,
            event_type="resource_access_requested",
            event_stage="gateway_exec",
            actor_type="tool",
            tool_id=request.tool_id,
            resource_type=intercepted.resource_type,
            resource_id=intercepted.resource_id,
            semantic_decision=request.semantic_decision,
            policy_decision=policy_eval.decision,
            risk_level=policy_eval.risk_level,
            disposition=policy_eval.disposition,
            status="recorded",
        )

        final_decision = request.semantic_decision
        if policy_eval.decision == "deny" or request.semantic_decision == "deny":
            final_decision = "deny"
        elif policy_eval.decision == "warn" or request.semantic_decision == "warn":
            final_decision = "warn"

        if final_decision == "deny":
            logger.info(
                "gateway.execute.blocked run_id=%s tool_call_id=%s decision=%s policy=%s",
                request.run_id,
                request.tool_call_id,
                final_decision,
                policy_eval.decision,
            )
            return ActionResult(
                run_id=request.run_id,
                tool_call_id=request.tool_call_id,
                tool_id=request.tool_id,
                action_type=request.action_type,
                final_decision=final_decision,
                policy_decision=policy_eval.decision,
                risk_level=policy_eval.risk_level,
                disposition=policy_eval.disposition,
                execution_status="blocked_by_policy_or_semantic_guard",
                resource_type=intercepted.resource_type,
                resource_id=intercepted.resource_id,
                output_summary="execution blocked by policy/semantic guard",
                executor_name="none",
                matched_rules=[item.__dict__ for item in policy_eval.matched_rules],
                explanations=policy_eval.explanations,
                completed_at=datetime.now(timezone.utc),
            )

        audit_service.record_event(
            db=db,
            run_id=request.run_id,
            session_id=session_id,
            event_type="tool_execution_started",
            event_stage="gateway_exec",
            actor_type="system",
            tool_id=request.tool_id,
            resource_type=intercepted.resource_type,
            resource_id=intercepted.resource_id,
            semantic_decision=request.semantic_decision,
            policy_decision=policy_eval.decision,
            risk_level=policy_eval.risk_level,
            disposition=policy_eval.disposition,
            status="recorded",
        )

        output = executor.execute(intercepted)

        logger.info(
            "gateway.execute.done run_id=%s tool_call_id=%s decision=%s policy=%s status=%s executor=%s",
            request.run_id,
            request.tool_call_id,
            final_decision,
            policy_eval.decision,
            output.execution_status,
            output.executor_name,
        )

        audit_service.record_event(
            db=db,
            run_id=request.run_id,
            session_id=session_id,
            event_type="tool_execution_completed",
            event_stage="gateway_exec",
            actor_type="system",
            tool_id=request.tool_id,
            resource_type=intercepted.resource_type,
            resource_id=intercepted.resource_id,
            semantic_decision=request.semantic_decision,
            policy_decision=policy_eval.decision,
            risk_level=policy_eval.risk_level,
            disposition=policy_eval.disposition,
            status="recorded",
            output_summary=output.output_summary,
        )

        return ActionResult(
            run_id=request.run_id,
            tool_call_id=request.tool_call_id,
            tool_id=request.tool_id,
            action_type=request.action_type,
            final_decision=final_decision,
            policy_decision=policy_eval.decision,
            risk_level=policy_eval.risk_level,
            disposition=policy_eval.disposition,
            execution_status=output.execution_status,
            resource_type=intercepted.resource_type,
            resource_id=intercepted.resource_id,
            output_summary=output.output_summary,
            executor_name=output.executor_name,
            matched_rules=[item.__dict__ for item in policy_eval.matched_rules],
            explanations=policy_eval.explanations,
            completed_at=datetime.now(timezone.utc),
        )


gateway_manager = GatewayManager(engine=policy_engine)
