from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


class EventsAlignmentFieldsTestCase(unittest.TestCase):
    def test_events_support_tool_call_id_and_alignment_filters(self) -> None:
        with TestClient(app) as client:
            ingest = client.post(
                "/api/v1/tasks/ingest",
                json={"session_id": "evt_align_1", "user_input": "请总结 workspace/a.md", "source": "test"},
            )
            run_id = ingest.json()["data"]["run_id"]
            tool_call_id = "evt_align_call_1"
            _ = client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": run_id,
                    "tool_call_id": tool_call_id,
                    "tool_id": "workspace_reader",
                    "arguments": {"file_path": "./workspace/a.md"},
                    "model_reason": "read file for summary",
                },
            )

            by_call = client.get(
                "/api/v1/events",
                params={"run_id": run_id, "tool_call_id": tool_call_id, "order": "asc"},
            )
            self.assertEqual(by_call.status_code, 200)
            events = by_call.json()["data"]["events"]
            self.assertGreaterEqual(len(events), 1)
            for event in events:
                self.assertEqual(event["tool_call_id"], tool_call_id)

            by_alignment = client.get(
                "/api/v1/events",
                params={"run_id": run_id, "alignment_decision": "allow"},
            )
            self.assertEqual(by_alignment.status_code, 200)
            decision_events = by_alignment.json()["data"]["events"]
            self.assertGreaterEqual(len(decision_events), 1)
            self.assertTrue(all(item["alignment_decision"] == "allow" for item in decision_events))


if __name__ == "__main__":
    unittest.main()
