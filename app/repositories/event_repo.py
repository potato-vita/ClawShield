from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


class EventRepository:
    """Persistence access for audit event entities."""

    MAX_LIST_LIMIT = 500

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
        since_ts: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
        order: str = "desc",
    ) -> list[AuditEvent]:
        stmt: Select[tuple[AuditEvent]] = select(AuditEvent)

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
        if since_ts:
            stmt = stmt.where(AuditEvent.ts > since_ts)

        order_normalized = order.lower()
        if order_normalized == "asc":
            stmt = stmt.order_by(AuditEvent.ts.asc())
        else:
            stmt = stmt.order_by(AuditEvent.ts.desc())

        limit_normalized = min(max(limit, 1), self.MAX_LIST_LIMIT)
        offset_normalized = max(offset, 0)
        stmt = stmt.offset(offset_normalized).limit(limit_normalized)

        return db.execute(stmt).scalars().all()

    def get_latest_marker(self, db: Session, run_id: str) -> tuple[str | None, datetime | None]:
        stmt = (
            select(AuditEvent.event_id, AuditEvent.ts)
            .where(AuditEvent.run_id == run_id)
            .order_by(AuditEvent.ts.desc(), AuditEvent.id.desc())
            .limit(1)
        )
        row = db.execute(stmt).first()
        if row is None:
            return None, None
        return row[0], row[1]


event_repository = EventRepository()
