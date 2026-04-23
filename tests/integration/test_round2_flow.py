from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.db import init_database
from app.main import app
from app.services.opencaw_service import opencaw_service
from app.settings import get_settings


def _sqlite_file_path(database_url: str) -> Path | None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None

    db_path = database_url[len(prefix) :]
    if db_path == ":memory:":
        return None
    return Path(db_path)


class RoundTwoFlowTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        settings = get_settings()
        sqlite_path = _sqlite_file_path(settings.database_url)
        if sqlite_path and sqlite_path.exists():
            sqlite_path.unlink()
        init_database()

    def setUp(self) -> None:
        opencaw_service.stop()

    def tearDown(self) -> None:
        opencaw_service.stop()

    def test_system_start_and_stop(self) -> None:
        with TestClient(app) as client:
            start_resp = client.post(
                "/api/v1/system/start",
                json={"mode": "dev", "auto_launch_opencaw": True},
            )
            self.assertEqual(start_resp.status_code, 200)
            start_payload = start_resp.json()

            self.assertTrue(start_payload["success"])
            self.assertEqual(start_payload["data"]["system_status"], "running")
            self.assertEqual(start_payload["data"]["opencaw_status"], "running")
            self.assertIsNotNone(start_payload["data"]["opencaw_pid"])

            stop_resp = client.post("/api/v1/system/stop")
            self.assertEqual(stop_resp.status_code, 200)
            stop_payload = stop_resp.json()

            self.assertTrue(stop_payload["success"])
            self.assertEqual(stop_payload["data"]["system_status"], "running")
            self.assertEqual(stop_payload["data"]["opencaw_status"], "stopped")

    def test_task_ingest_and_run_queries(self) -> None:
        with TestClient(app) as client:
            ingest_resp = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": "sess_round2",
                    "user_input": "summarize files in workspace",
                    "source": "ui",
                    "metadata": {"scenario": "round2"},
                },
            )
            self.assertEqual(ingest_resp.status_code, 200)
            ingest_payload = ingest_resp.json()
            self.assertTrue(ingest_payload["success"])

            run_id = ingest_payload["data"]["run_id"]
            self.assertTrue(run_id.startswith("run_"))

            run_resp = client.get(f"/api/v1/runs/{run_id}")
            self.assertEqual(run_resp.status_code, 200)
            run_payload = run_resp.json()
            self.assertEqual(run_payload["data"]["run_id"], run_id)

            list_resp = client.get("/api/v1/runs")
            self.assertEqual(list_resp.status_code, 200)
            list_payload = list_resp.json()
            listed_run_ids = {item["run_id"] for item in list_payload["data"]["runs"]}
            self.assertIn(run_id, listed_run_ids)

            events_resp = client.get("/api/v1/events", params={"run_id": run_id})
            self.assertEqual(events_resp.status_code, 200)
            events_payload = events_resp.json()
            event_types = {item["event_type"] for item in events_payload["data"]["events"]}
            self.assertIn("task_received", event_types)
            self.assertIn("run_created", event_types)


if __name__ == "__main__":
    unittest.main()
