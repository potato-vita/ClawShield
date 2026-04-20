from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_api_run_lifecycle(tmp_path):
    # Use app as-is to validate full stack wiring.
    with TestClient(app) as client:
        start = client.post(
            "/api/runs/start",
            json={
                "task_name": "api_test_task",
                "description": "api test",
                "actor": "pytest",
                "skill_id": "skill_pytest",
            },
        )
        assert start.status_code == 200
        run_id = start.json()["run_id"]

        execute = client.post(
            f"/api/runs/{run_id}/execute-scenario",
            json={"scenario_id": "normal"},
        )
        assert execute.status_code == 200
        payload = execute.json()
        assert payload["run_id"] == run_id
        assert "report_id" in payload

        events = client.get(f"/api/runs/{run_id}/events")
        assert events.status_code == 200
        assert isinstance(events.json(), list)
