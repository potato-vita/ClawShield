from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.event_repo import EventRepository, event_repository
from app.schemas.event import EventSummary
from app.telemetry.collector import telemetry_collector


class AuditService:
    """Audit event recording and query service."""

    def __init__(self, repository: EventRepository) -> None:
        self._repository = repository

    def record_event(
        self,
        db: Session,
        run_id: str,
        event_type: str,
        session_id: str | None = None,
        event_stage: str | None = None,
        actor_type: str | None = None,
        actor_id: str | None = None,
        tool_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        input_summary: str | None = None,
        output_summary: str | None = None,
        semantic_decision: str | None = None,
        policy_decision: str | None = None,
        risk_level: str | None = None,
        disposition: str | None = None,
        status: str | None = None,
    ):
        return telemetry_collector.collect(
            db=db,
            payload={
                "run_id": run_id,
                "session_id": session_id,
                "event_type": event_type,
                "event_stage": event_stage,
                "actor_type": actor_type,
                "actor_id": actor_id,
                "tool_id": tool_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "input_summary": input_summary,
                "output_summary": output_summary,
                "semantic_decision": semantic_decision,
                "policy_decision": policy_decision,
                "risk_level": risk_level,
                "disposition": disposition,
                "status": status,
            },
        )

    def list_events(
        self,
        db: Session,
        run_id: str | None = None,
        event_type: str | None = None,
        risk_level: str | None = None,
        tool_id: str | None = None,
        resource_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
        order: str = "desc",
    ) -> list[EventSummary]:
        rows = self._repository.list_by_filters(
            db=db,
            run_id=run_id,
            event_type=event_type,
            risk_level=risk_level,
            tool_id=tool_id,
            resource_type=resource_type,
            limit=limit,
            offset=offset,
            order=order,
        )
        return [
            EventSummary(
                event_id=item.event_id,
                run_id=item.run_id,
                session_id=item.session_id,
                event_type=item.event_type,
                event_stage=item.event_stage,
                ts=item.ts,
                actor_type=item.actor_type,
                tool_id=item.tool_id,
                resource_type=item.resource_type,
                resource_id=item.resource_id,
                semantic_decision=item.semantic_decision,
                policy_decision=item.policy_decision,
                risk_level=item.risk_level,
                disposition=item.disposition,
                status=item.status,
            )
            for item in rows
        ]


audit_service = AuditService(repository=event_repository)
