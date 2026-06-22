from tests.test_audit_api import request_payload


def test_policy_crud_and_rule_priority(client) -> None:
    created = client.post("/api/module4/policies", json={
        "name": "禁止 secret.txt", "condition": {"field": "path", "operator": "contains", "value": "secret.txt"},
        "action": "BLOCK", "priority": 500,
    }).json()
    assert created["enabled"] is True
    assert any(item["id"] == created["id"] for item in client.get("/api/module4/policies").json())
    response = client.post("/v1/audit/tool-call", json=request_payload("call_policy", "file_read", {"path": "secret.txt"}))
    assert response.json()["decision"] == "BLOCK"
    client.patch(f"/api/module4/policies/{created['id']}", json={"enabled": False})
    response = client.post("/v1/audit/tool-call", json=request_payload("call_policy_off", "file_read", {"path": "secret.txt"}))
    assert response.json()["decision"] == "ALLOW"


def test_higher_priority_policy_matches_first(client) -> None:
    condition = {"field": "path", "operator": "contains", "value": "priority.txt"}
    client.post("/api/module4/policies", json={"name": "warn", "condition": condition, "action": "WARN", "priority": 10})
    client.post("/api/module4/policies", json={"name": "block", "condition": condition, "action": "BLOCK", "priority": 100})
    result = client.post("/v1/audit/tool-call", json=request_payload("call_priority", "file_read", {"path": "priority.txt"})).json()
    assert result["decision"] == "BLOCK"
