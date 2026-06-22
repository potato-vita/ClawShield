from sqlalchemy import select

from app.db.models import Approval
from tests.test_audit_api import request_payload


def test_ask_approval_can_be_approved(client, db) -> None:
    session_id = client.post("/sessions", json={"title": "审批"}).json()["id"]
    payload = request_payload("call_approval", "network_request", {"url": "https://external-upload.com/drop"})
    payload["session_id"] = session_id
    audit = client.post("/v1/audit/tool-call", json=payload).json()
    assert audit["decision"] == "ASK"
    response = client.post(f"/sessions/{session_id}/approve", json={"approved": True, "reason": "业务需要"})
    assert response.json()["status"] == "approved"
    assert db.scalar(select(Approval).where(Approval.id == audit["approval"]["approval_id"])).status == "approved"


def test_approval_reject_and_missing(client) -> None:
    session_id = client.post("/sessions", json={"title": "审批"}).json()["id"]
    assert client.post(f"/sessions/{session_id}/approve", json={"approved": False}).status_code == 404
    payload = request_payload("call_reject", "network_request", {"url": "https://external-upload.com/drop"})
    payload["session_id"] = session_id
    client.post("/v1/audit/tool-call", json=payload)
    assert client.post(f"/sessions/{session_id}/approve", json={"approved": False}).json()["status"] == "rejected"
