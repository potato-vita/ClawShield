from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


class RunListOrderByLatestEventTestCase(unittest.TestCase):
    def test_runs_list_prefers_latest_event_time_over_created_time(self) -> None:
        with TestClient(app) as client:
            run_a_resp = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": "run_list_order_session_a",
                    "user_input": "run-a baseline",
                    "source": "test",
                },
            )
            self.assertEqual(run_a_resp.status_code, 200)
            run_a = run_a_resp.json()["data"]["run_id"]

            run_b_resp = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": "run_list_order_session_b",
                    "user_input": "run-b baseline",
                    "source": "test",
                },
            )
            self.assertEqual(run_b_resp.status_code, 200)
            run_b = run_b_resp.json()["data"]["run_id"]

            callback_resp = client.post(
                "/api/v1/bridge/opencaw/callback/message",
                json={
                    "session_id": "run_list_order_session_a",
                    "message": "latest message should make run-a appear first",
                    "role": "user",
                },
            )
            self.assertEqual(callback_resp.status_code, 200)

            runs_resp = client.get("/api/v1/runs", params={"limit": 200})
            self.assertEqual(runs_resp.status_code, 200)
            runs = runs_resp.json()["data"]["runs"]
            run_ids = [item["run_id"] for item in runs]

            self.assertIn(run_a, run_ids)
            self.assertIn(run_b, run_ids)
            self.assertLess(run_ids.index(run_a), run_ids.index(run_b))


if __name__ == "__main__":
    unittest.main()
