from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, default="eino", nullable=False)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[str | None] = mapped_column(Text)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("analysis_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String, default="markdown")
    parent_id: Mapped[str | None] = mapped_column(String)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    related_tool_call_id: Mapped[str | None] = mapped_column(String)
    related_event_id: Mapped[str | None] = mapped_column(String)
    related_report_id: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OpenClawRun(Base):
    __tablename__ = "openclaw_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    analysis_session_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_sessions.id"))
    openclaw_session_id: Mapped[str | None] = mapped_column(String)
    user_goal: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    blocked_count: Mapped[int] = mapped_column(Integer, default=0)
    ask_count: Mapped[int] = mapped_column(Integer, default=0)
    warn_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[str | None] = mapped_column(Text)


class TraceEvent(Base):
    __tablename__ = "trace_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    schema_version: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String, index=True)
    run_id: Mapped[str | None] = mapped_column(String, index=True)
    trace_id: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String, default="openclaw-plugin")
    severity: Mapped[str] = mapped_column(String, default="info")
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    payload_hash: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ToolCall(Base):
    __tablename__ = "tool_calls"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("openclaw_runs.id"), index=True)
    session_id: Mapped[str | None] = mapped_column(String, index=True)
    trace_id: Mapped[str | None] = mapped_column(String)
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    tool_kind: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    decision: Mapped[str | None] = mapped_column(String)
    raw_params_json: Mapped[str | None] = mapped_column(Text)
    sanitized_params_json: Mapped[str | None] = mapped_column(Text)
    param_summary: Mapped[str | None] = mapped_column(Text)
    resource_type: Mapped[str | None] = mapped_column(String)
    resource_value: Mapped[str | None] = mapped_column(String)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[int | None] = mapped_column(Integer)


class ToolResult(Base):
    __tablename__ = "tool_results"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tool_call_id: Mapped[str] = mapped_column(ForeignKey("tool_calls.id"), index=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    exit_code: Mapped[int | None] = mapped_column(Integer)
    result_preview: Mapped[str | None] = mapped_column(Text)
    result_hash: Mapped[str | None] = mapped_column(String)
    result_size: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditDecision(Base):
    __tablename__ = "audit_decisions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tool_call_id: Mapped[str] = mapped_column(ForeignKey("tool_calls.id"), index=True)
    decision: Mapped[str] = mapped_column(String, nullable=False)
    risk_level: Mapped[str] = mapped_column(String, nullable=False)
    risk_score: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    matched_rules_json: Mapped[str | None] = mapped_column(Text)
    modified_params_json: Mapped[str | None] = mapped_column(Text)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    core_latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SecurityEvent(Base):
    __tablename__ = "security_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str | None] = mapped_column(String, index=True)
    run_id: Mapped[str | None] = mapped_column(String, index=True)
    tool_call_id: Mapped[str | None] = mapped_column(ForeignKey("tool_calls.id"))
    audit_decision_id: Mapped[str | None] = mapped_column(ForeignKey("audit_decisions.id"))
    event_title: Mapped[str] = mapped_column(String, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    risk_level: Mapped[str] = mapped_column(String, nullable=False, index=True)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    event_status: Mapped[str] = mapped_column(String, default="open")
    username: Mapped[str | None] = mapped_column(String)
    user_id: Mapped[str | None] = mapped_column(String)
    department_name: Mapped[str | None] = mapped_column(String)
    department_id: Mapped[str | None] = mapped_column(String)
    host_name: Mapped[str | None] = mapped_column(String)
    host_id: Mapped[str | None] = mapped_column(String)
    ip_address: Mapped[str | None] = mapped_column(String)
    file_name: Mapped[str | None] = mapped_column(String)
    file_path: Mapped[str | None] = mapped_column(String)
    sensitive_type: Mapped[str | None] = mapped_column(String)
    sensitive_level: Mapped[str | None] = mapped_column(String)
    operation: Mapped[str | None] = mapped_column(String)
    process_name: Mapped[str | None] = mapped_column(String)
    target: Mapped[str | None] = mapped_column(String)
    target_type: Mapped[str | None] = mapped_column(String)
    risk_explanation: Mapped[str | None] = mapped_column(Text)
    recommended_actions_json: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_sessions.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    report_type: Mapped[str] = mapped_column(String, nullable=False)
    time_range: Mapped[str | None] = mapped_column(String)
    content_markdown: Mapped[str | None] = mapped_column(Text)
    content_html_path: Mapped[str | None] = mapped_column(String)
    content_pdf_path: Mapped[str | None] = mapped_column(String)
    generated_by: Mapped[str] = mapped_column(String, default="eino-agent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RiskEvidence(Base):
    __tablename__ = "risk_evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    audit_decision_id: Mapped[str] = mapped_column(ForeignKey("audit_decisions.id"), index=True)
    tool_call_id: Mapped[str] = mapped_column(ForeignKey("tool_calls.id"), index=True)
    evidence_type: Mapped[str] = mapped_column(String, nullable=False)
    evidence_key: Mapped[str | None] = mapped_column(String)
    evidence_value: Mapped[str | None] = mapped_column(Text)
    evidence_hash: Mapped[str | None] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RiskGraphEdge(Base):
    __tablename__ = "risk_graph_edges"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("openclaw_runs.id"), index=True)
    tool_call_id: Mapped[str | None] = mapped_column(ForeignKey("tool_calls.id"))
    source_node: Mapped[str] = mapped_column(String, nullable=False)
    target_node: Mapped[str] = mapped_column(String, nullable=False)
    edge_type: Mapped[str] = mapped_column(String, nullable=False)
    evidence_id: Mapped[str | None] = mapped_column(ForeignKey("risk_evidence.id"))
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Policy(Base):
    __tablename__ = "policies"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    target: Mapped[str] = mapped_column(String, nullable=False)
    condition_json: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    tool_call_id: Mapped[str] = mapped_column(ForeignKey("tool_calls.id"), index=True)
    audit_decision_id: Mapped[str | None] = mapped_column(ForeignKey("audit_decisions.id"))
    session_id: Mapped[str | None] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String)


class UploadedDocument(Base):
    __tablename__ = "uploaded_documents"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_sessions.id"), index=True)
    original_name: Mapped[str] = mapped_column(String, nullable=False)
    stored_path: Mapped[str] = mapped_column(String, nullable=False)
    file_hash: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    parsed_text_preview: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
