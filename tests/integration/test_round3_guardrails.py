from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app


class RoundThreeGuardrailsTestCase(unittest.TestCase):
    def test_tool_call_semantic_decision_and_events(self) -> None:
        with TestClient(app) as client:
            health_payload = client.get("/api/v1/health").json()
            self.assertTrue(health_payload["success"])
            self.assertEqual(health_payload["data"]["guardrails_status"], "ready")

            ingest_payload = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": "sess_round3",
                    "user_input": "请分析工作区内容并给我总结",
                    "source": "ui",
                    "metadata": {"round": 3},
                },
            ).json()
            self.assertTrue(ingest_payload["success"])
            run_id = ingest_payload["data"]["run_id"]

            tool_call_resp = client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": run_id,
                    "tool_call_id": "tc_round3_001",
                    "tool_id": "workspace_reader",
                    "tool_name": "workspace_reader",
                    "arguments": {"file_path": "./workspace/README.md"},
                    "raw_context": {"phase": "planning_tool_use"},
                },
            )
            self.assertEqual(tool_call_resp.status_code, 200)

            decision_payload = tool_call_resp.json()
            self.assertTrue(decision_payload["success"])
            decision_data = decision_payload["data"]
            self.assertIn(decision_data["decision"], ["allow", "warn", "deny"])
            self.assertTrue(decision_data["semantic_reason"])
            self.assertIn(decision_data["task_type"], ["analysis", "general", "unknown"])

            events_payload = client.get(
                "/api/v1/events",
                params={"run_id": run_id},
            ).json()
            self.assertTrue(events_payload["success"])

            event_types = {item["event_type"] for item in events_payload["data"]["events"]}
            self.assertIn("task_classified", event_types)
            self.assertIn("dialog_state_changed", event_types)
            self.assertIn("semantic_check_completed", event_types)


if __name__ == "__main__":
    unittest.main()
