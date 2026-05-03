from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


class EventsFilterAndTotalTestCase(unittest.TestCase):
    def test_events_api_supports_session_filter_and_total_count(self) -> None:
        suffix = str(time.time_ns())
        session_a = f"roundz15_session_a_{suffix}"
        session_b = f"roundz15_session_b_{suffix}"

        with TestClient(app) as client:
            ingest_a = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": session_a,
                    "user_input": "session-a baseline task",
                    "source": "test",
                },
            )
            self.assertEqual(ingest_a.status_code, 200)
            run_a = ingest_a.json()["data"]["run_id"]

            callback_a = client.post(
                "/api/v1/bridge/opencaw/callback/message",
                json={
                    "session_id": session_a,
                    "message": "session-a message for filter test",
                    "role": "user",
                },
            )
            self.assertEqual(callback_a.status_code, 200)

            ingest_b = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": session_b,
                    "user_input": "session-b baseline task",
                    "source": "test",
                },
            )
            self.assertEqual(ingest_b.status_code, 200)

            resp = client.get(
                "/api/v1/events",
                params={
                    "run_id": run_a,
                    "session_id": session_a,
                    "limit": 3,
                    "offset": 0,
                    "order": "desc",
                    "include_total": True,
                },
            )
            self.assertEqual(resp.status_code, 200)
            payload = resp.json()["data"]
            events = payload["events"]

            self.assertIn("total", payload)
            self.assertGreaterEqual(payload["total"], len(events))
            self.assertEqual(payload["limit"], 3)
            self.assertEqual(payload["offset"], 0)
            self.assertEqual(payload["order"], "desc")
            self.assertGreaterEqual(len(events), 1)
            for event in events:
                self.assertEqual(event["run_id"], run_a)
                self.assertEqual(event["session_id"], session_a)


if __name__ == "__main__":
    unittest.main()
