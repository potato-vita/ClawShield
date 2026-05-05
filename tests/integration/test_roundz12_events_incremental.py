from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


class IncrementalEventsApiTestCase(unittest.TestCase):
    def test_events_since_ts_returns_only_newer_records(self) -> None:
        with TestClient(app) as client:
            ingest_resp = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": "incremental_events_session",
                    "user_input": "baseline task for incremental event query",
                    "source": "test",
                    "metadata": {"case": "roundz12"},
                },
            )
            self.assertEqual(ingest_resp.status_code, 200)
            run_id = ingest_resp.json()["data"]["run_id"]

            baseline_resp = client.get(
                "/api/v1/events",
                params={"run_id": run_id, "order": "asc", "limit": 300},
            )
            self.assertEqual(baseline_resp.status_code, 200)
            baseline_events = baseline_resp.json()["data"]["events"]
            self.assertGreaterEqual(len(baseline_events), 1)
            last_ts = baseline_events[-1]["ts"]

            callback_resp = client.post(
                "/api/v1/bridge/opencaw/callback/message",
                json={
                    "session_id": "incremental_events_session",
                    "message": "new chat event for since_ts validation",
                    "role": "user",
                },
            )
            self.assertEqual(callback_resp.status_code, 200)

            incremental_resp = client.get(
                "/api/v1/events",
                params={
                    "run_id": run_id,
                    "order": "asc",
                    "limit": 300,
                    "since_ts": last_ts,
                },
            )
            self.assertEqual(incremental_resp.status_code, 200)
            incremental_events = incremental_resp.json()["data"]["events"]

            self.assertGreaterEqual(len(incremental_events), 1)
            event_types = {item["event_type"] for item in incremental_events}
            self.assertIn("chat_message_received", event_types)


if __name__ == "__main__":
    unittest.main()
