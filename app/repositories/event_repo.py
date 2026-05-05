from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


class EventRepository:
    """Persistence access for audit event entities."""

    MAX_LIST_LIMIT = 500

    @staticmethod
    def _apply_filters(
        stmt: Select,
        run_id: str | None = None,
        event_type: str | None = None,
        event_types: list[str] | None = None,
        risk_level: str | None = None,
        tool_id: str | None = None,
        resource_type: str | None = None,
        since_ts: datetime | None = None,
        tool_call_id: str | None = None,
        step_id: str | None = None,
        alignment_decision: str | None = None,
    ) -> Select:
        if run_id:
            stmt = stmt.where(AuditEvent.run_id == run_id)
        if event_types:
            stmt = stmt.where(AuditEvent.event_type.in_(event_types))
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
        if tool_call_id:
            stmt = stmt.where(AuditEvent.tool_call_id == tool_call_id)
        if step_id:
            stmt = stmt.where(AuditEvent.step_id == step_id)
        if alignment_decision:
            stmt = stmt.where(AuditEvent.alignment_decision == alignment_decision)
        return stmt

    def create(self, db: Session, event: AuditEvent) -> AuditEvent:
        db.add(event)
        db.flush()
        return event

    def list_by_filters(
        self,
        db: Session,
        run_id: str | None = None,
        event_type: str | None = None,
        event_types: list[str] | None = None,
        risk_level: str | None = None,
        tool_id: str | None = None,
        resource_type: str | None = None,
        since_ts: datetime | None = None,
        tool_call_id: str | None = None,
        step_id: str | None = None,
        alignment_decision: str | None = None,
        limit: int = 100,
        offset: int = 0,
        order: str = "desc",
    ) -> list[AuditEvent]:
        stmt: Select[tuple[AuditEvent]] = select(AuditEvent)
        stmt = self._apply_filters(
            stmt=stmt,
            run_id=run_id,
            event_type=event_type,
            event_types=event_types,
            risk_level=risk_level,
            tool_id=tool_id,
            resource_type=resource_type,
            since_ts=since_ts,
            tool_call_id=tool_call_id,
            step_id=step_id,
            alignment_decision=alignment_decision,
        )

        order_normalized = order.lower()
        if order_normalized == "asc":
            stmt = stmt.order_by(AuditEvent.ts.asc(), AuditEvent.id.asc())
        else:
            stmt = stmt.order_by(AuditEvent.ts.desc(), AuditEvent.id.desc())

        limit_normalized = min(max(limit, 1), self.MAX_LIST_LIMIT)
        offset_normalized = max(offset, 0)
        stmt = stmt.offset(offset_normalized).limit(limit_normalized)

        return db.execute(stmt).scalars().all()

    def count_by_filters(
        self,
        db: Session,
        run_id: str | None = None,
        event_type: str | None = None,
        event_types: list[str] | None = None,
        risk_level: str | None = None,
        tool_id: str | None = None,
        resource_type: str | None = None,
        since_ts: datetime | None = None,
        tool_call_id: str | None = None,
        step_id: str | None = None,
        alignment_decision: str | None = None,
    ) -> int:
        stmt = select(func.count(AuditEvent.id))
        stmt = self._apply_filters(
            stmt=stmt,
            run_id=run_id,
            event_type=event_type,
            event_types=event_types,
            risk_level=risk_level,
            tool_id=tool_id,
            resource_type=resource_type,
            since_ts=since_ts,
            tool_call_id=tool_call_id,
            step_id=step_id,
            alignment_decision=alignment_decision,
        )
        value = db.execute(stmt).scalar_one()
        return int(value)

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
