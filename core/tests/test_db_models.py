from sqlalchemy import inspect

from app.db.models import AnalysisSession, AuditDecision, SecurityEvent, ToolCall


def test_core_tables_are_created(client) -> None:
    from app.db.session import engine
    tables = set(inspect(engine).get_table_names())
    assert {
        "analysis_sessions", "chat_messages", "openclaw_runs", "trace_events",
        "tool_calls", "tool_results", "audit_decisions", "security_events",
    }.issubset(tables)


def test_core_models_can_be_inserted(db) -> None:
    session = AnalysisSession(id="sess_db", title="DB test")
    db.add(session)
    call = ToolCall(id="call_db", tool_name="read", tool_kind="file_read", status="audited")
    db.add(call)
    db.flush()
    decision = AuditDecision(
        id="decision_db", tool_call_id="call_db", decision="BLOCK", risk_level="critical",
        risk_score=95, reason="test",
    )
    db.add(decision)
    db.flush()
    event = SecurityEvent(
        id="event_db", tool_call_id="call_db", audit_decision_id="decision_db",
        event_title="test", event_type="test", risk_level="critical", risk_score=95,
    )
    db.add(event)
    db.commit()

    assert db.get(AnalysisSession, "sess_db") is not None
    assert db.get(ToolCall, "call_db") is not None
    assert db.get(AuditDecision, "decision_db") is not None
    assert db.get(SecurityEvent, "event_db") is not None
