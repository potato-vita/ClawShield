from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


class CallbackSessionResolutionByLatestActivityTestCase(unittest.TestCase):
    def test_callback_tool_call_prefers_most_recently_active_run_in_session(self) -> None:
        with TestClient(app) as client:
            session_id = "callback_session_activity_resolution"

            run_a_resp = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": session_id,
                    "user_input": "first run",
                    "source": "test",
                },
            )
            self.assertEqual(run_a_resp.status_code, 200)
            run_a = run_a_resp.json()["data"]["run_id"]

            run_b_resp = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": session_id,
                    "user_input": "second run",
                    "source": "test",
                },
            )
            self.assertEqual(run_b_resp.status_code, 200)
            run_b = run_b_resp.json()["data"]["run_id"]
            self.assertNotEqual(run_a, run_b)

            msg_resp = client.post(
                "/api/v1/bridge/opencaw/callback/message",
                json={
                    "run_id": run_a,
                    "message": {"role": "user", "content": "touch run-a as latest active run"},
                },
            )
            self.assertEqual(msg_resp.status_code, 200)
            self.assertTrue(msg_resp.json()["success"])

            callback_resp = client.post(
                "/api/v1/bridge/opencaw/callback/tool-call",
                json={
                    "session_id": session_id,
                    "tool_call_id": "cb_activity_1",
                    "tool_id": "workspace_reader",
                    "arguments": {"file_path": "./workspace/demo.txt"},
                },
            )
            self.assertEqual(callback_resp.status_code, 200)
            payload = callback_resp.json()
            self.assertTrue(payload["success"])
            self.assertEqual(payload["data"]["run_id"], run_a)


if __name__ == "__main__":
    unittest.main()
