from sqlalchemy import func, select

from app.db.models import OpenClawRun, ToolCall, ToolResult, TraceEvent


def event(event_id: str, event_type: str, payload: dict) -> dict:
    return {
        "event_id": event_id, "schema_version": "v1", "type": event_type,
        "session_id": "sess_events", "run_id": "run_events", "trace_id": "trace_events",
        "timestamp": 1782100000000, "plugin_id": "traceshield-security-plugin",
        "mode": "async", "payload": payload,
    }


def test_event_batch_is_idempotent(client, db) -> None:
    item = event("evt_once", "message_received", {"content": "hello"})
    first = client.post("/v1/events/batch", json={"events": [item]}).json()
    second = client.post("/v1/events/batch", json={"events": [item]}).json()
    assert first == {"success": True, "accepted": 1, "duplicated": 0, "failed": 0}
    assert second["duplicated"] == 1
    assert db.scalar(select(func.count()).select_from(TraceEvent)) == 1


def test_before_after_and_agent_end_projection(client, db) -> None:
    events = [
        event("evt_before", "before_tool_call", {"tool_call_id": "call_event", "tool_name": "read", "tool_kind": "file_read", "params": {"path": "README.md"}}),
        event("evt_after", "after_tool_call", {"tool_call_id": "call_event", "tool_name": "read", "tool_kind": "file_read", "result_preview": "# TraceShield", "result_size": 13}),
        event("evt_end", "agent_end", {"status": "completed"}),
    ]
    response = client.post("/v1/events/batch", json={"events": events}).json()
    assert response["accepted"] == 3
    assert db.get(ToolCall, "call_event").status == "completed"
    assert db.scalar(select(func.count()).select_from(ToolResult).where(ToolResult.tool_call_id == "call_event")) == 1
    assert db.get(OpenClawRun, "run_events").status == "completed"


def test_bad_event_does_not_block_good_event(client) -> None:
    response = client.post("/v1/events/batch", json={"events": [
        {"bad": "event"},
        event("evt_good", "llm_output", {"content": "ok"}),
    ]}).json()
    assert response == {"success": False, "accepted": 1, "duplicated": 0, "failed": 1}
