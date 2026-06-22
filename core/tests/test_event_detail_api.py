from sqlalchemy import select

from app.db.models import SecurityEvent
from tests.test_audit_api import request_payload


def test_event_detail_links_audit_evidence_and_graph(client, db) -> None:
    client.post("/v1/audit/tool-call", json=request_payload("call_detail", "shell_exec", {"cmd": "cat .env"}))
    event = db.scalar(select(SecurityEvent).where(SecurityEvent.tool_call_id == "call_detail"))
    response = client.get(f"/api/module4/events/{event.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["event"]["event_id"] == event.id
    assert data["event"]["risk_level"] == "critical"
    assert isinstance(data["recommended_actions"], list)
    assert data["tool_call"]["id"] == "call_detail"
    assert data["audit_decision"]["decision"] == "BLOCK"
    assert len(data["evidence"]) >= 1
    assert len(data["risk_graph"]) >= 3


def test_missing_event_returns_404(client) -> None:
    assert client.get("/api/module4/events/missing").status_code == 404


def test_external_event_is_classified_as_network(client, db) -> None:
    client.post("/v1/audit/tool-call", json=request_payload(
        "call_network_detail", "network_request", {"url": "https://external-upload.com/drop"}
    ))
    event = db.scalar(select(SecurityEvent).where(SecurityEvent.tool_call_id == "call_network_detail"))
    detail = client.get(f"/api/module4/events/{event.id}").json()
    assert detail["event"]["target_type"] == "network"
    assert detail["event"]["file_path"] is None
