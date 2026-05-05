from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, utc_now


class AuditEvent(TimestampMixin, Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_run_id_ts", "run_id", "ts"),
        Index("ix_audit_events_ts", "ts"),
        Index("ix_audit_events_run_id_event_type_ts", "run_id", "event_type", "ts"),
        Index("ix_audit_events_run_id_risk_level_ts", "run_id", "risk_level", "ts"),
        Index("ix_audit_events_run_id_alignment_decision_ts", "run_id", "alignment_decision", "ts"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    run_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    event_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    actor_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tool_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    semantic_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    policy_decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    disposition: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    step_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    parent_event_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    span_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    alignment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    alignment_decision: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    alignment_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    intended_effect: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actual_effect: Mapped[str | None] = mapped_column(String(64), nullable=True)
    impact_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    argument_digest: Mapped[str | None] = mapped_column(String(128), nullable=True)

    @property
    def justification_ref(self) -> str | None:
        if not isinstance(self.metadata_json, dict):
            return None
        value = self.metadata_json.get("justification_ref")
        return str(value) if value else None

    @property
    def counterfactual_note(self) -> str | None:
        if not isinstance(self.metadata_json, dict):
            return None
        value = self.metadata_json.get("counterfactual_note")
        return str(value) if value else None
