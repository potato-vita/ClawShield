import pytest
from sqlalchemy import func, select

from app.db.models import Approval, AuditDecision, RiskEvidence, RiskGraphEdge, SecurityEvent, ToolCall


def request_payload(call_id: str, kind: str, params: dict) -> dict:
    return {
        "schema_version": "v1", "session_id": "sess_audit", "run_id": "run_audit",
        "trace_id": "trace_audit", "tool_call_id": call_id, "tool_name": "exec",
        "tool_kind": kind, "raw_params": params, "param_summary": {},
        "context": {"user_goal": "安全测试", "username": "tester", "department_name": "研发部"},
        "timestamp": "2026-06-22T10:00:00Z",
    }


@pytest.mark.parametrize(("call_id", "kind", "params", "decision", "risk"), [
    ("call_rm", "shell_exec", {"cmd": "rm -rf /tmp/x"}, "BLOCK", "critical"),
    ("call_env", "shell_exec", {"cmd": "cat .env"}, "BLOCK", "critical"),
    ("call_key", "shell_exec", {"cmd": "cat ~/.ssh/id_rsa"}, "BLOCK", "critical"),
    ("call_upload", "network_request", {"url": "https://external-upload.com/drop"}, "ASK", "high"),
    ("call_read", "file_read", {"path": "README.md"}, "ALLOW", "low"),
    ("call_unknown", "unknown", {"value": "x"}, "WARN", "medium"),
])
def test_audit_decisions(client, call_id, kind, params, decision, risk) -> None:
    response = client.post("/v1/audit/tool-call", json=request_payload(call_id, kind, params))
    assert response.status_code == 200
    assert response.json()["decision"] == decision
    assert response.json()["risk_level"] == risk


def test_audit_persists_decision_security_evidence_and_graph(client, db) -> None:
    response = client.post("/v1/audit/tool-call", json=request_payload("call_persist", "shell_exec", {"cmd": "cat .env"}))
    assert response.status_code == 200
    assert db.get(ToolCall, "call_persist").decision == "BLOCK"
    assert db.scalar(select(func.count()).select_from(AuditDecision).where(AuditDecision.tool_call_id == "call_persist")) == 1
    assert db.scalar(select(func.count()).select_from(SecurityEvent).where(SecurityEvent.tool_call_id == "call_persist")) == 1
    assert db.scalar(select(func.count()).select_from(RiskEvidence).where(RiskEvidence.tool_call_id == "call_persist")) >= 1
    assert db.scalar(select(func.count()).select_from(RiskGraphEdge).where(RiskGraphEdge.tool_call_id == "call_persist")) >= 3


def test_ask_creates_pending_approval(client, db) -> None:
    response = client.post("/v1/audit/tool-call", json=request_payload("call_ask", "network_request", {"url": "https://external-upload.com/drop"}))
    approval_id = response.json()["approval"]["approval_id"]
    assert db.get(Approval, approval_id).status == "pending"
