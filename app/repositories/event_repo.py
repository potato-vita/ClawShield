from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


class EventRepository:
    """Persistence access for audit event entities."""

    def create(self, db: Session, event: AuditEvent) -> AuditEvent:
        db.add(event)
        db.flush()
        return event

    def list_by_filters(
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
    ) -> list[AuditEvent]:
        order_normalized = order.lower()
        if order_normalized == "asc":
            stmt: Select[tuple[AuditEvent]] = select(AuditEvent).order_by(AuditEvent.ts.asc())
        else:
            stmt = select(AuditEvent).order_by(AuditEvent.ts.desc())

        stmt = stmt.offset(max(offset, 0)).limit(max(limit, 1))

        if run_id:
            stmt = stmt.where(AuditEvent.run_id == run_id)
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if risk_level:
            stmt = stmt.where(AuditEvent.risk_level == risk_level)
        if tool_id:
            stmt = stmt.where(AuditEvent.tool_id == tool_id)
        if resource_type:
            stmt = stmt.where(AuditEvent.resource_type == resource_type)

        return db.execute(stmt).scalars().all()


event_repository = EventRepository()
