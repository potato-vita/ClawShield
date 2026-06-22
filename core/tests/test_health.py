from fastapi.testclient import TestClient


def test_module4_health_reports_database_ok(client: TestClient) -> None:
    response = client.get("/api/module4/health")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "database": "ok",
        "service": "traceshield-core",
        "version": "0.1.0",
    }
