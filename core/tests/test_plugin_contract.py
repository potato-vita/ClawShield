import json
from pathlib import Path

from app.schemas.plugin import AuditDecisionResponse, AuditToolCallRequest, TraceEvent


def test_real_plugin_fixture_parses() -> None:
    fixture = Path(__file__).parent / "fixtures" / "plugin_audit_request.json"
    request = AuditToolCallRequest.model_validate_json(fixture.read_text())
    assert request.raw_params == {"cmd": "ls"}
    assert request.context.user_goal == "List files"


def test_taskbook_params_alias_and_default_context() -> None:
    request = AuditToolCallRequest.model_validate({
        "session_id": "s", "run_id": "r", "trace_id": "t", "tool_call_id": "c",
        "tool_name": "read", "params": {},
    })
    assert request.raw_params == {}
    assert request.context.recent_message_hashes == []


def test_trace_event_accepts_type_and_event_type() -> None:
    base = {"event_id": "e", "timestamp": 1, "payload": {}}
    assert TraceEvent.model_validate({**base, "type": "llm_input"}).event_type == "llm_input"
    assert TraceEvent.model_validate({**base, "event_id": "e2", "event_type": "agent_end"}).event_type == "agent_end"


def test_audit_response_serializes_plugin_fields() -> None:
    response = AuditDecisionResponse(
        decision="ALLOW", risk_level="low", risk_score=5, reason="ok", matched_rules=["r"]
    )
    data = json.loads(response.model_dump_json())
    assert data["decision"] == "ALLOW"
    assert data["modified_params"] is None
    assert data["approval"] is None
