from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app


class RoundFivePolicyTestCase(unittest.TestCase):
    def test_policy_engine_blocks_disallowed_tools_and_resources(self) -> None:
        with TestClient(app) as client:
            ingest_resp = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": "sess_round5",
                    "user_input": "请分析这些文件并总结",
                    "source": "ui",
                    "metadata": {"round": 5},
                },
            )
            self.assertEqual(ingest_resp.status_code, 200)
            run_id = ingest_resp.json()["data"]["run_id"]

            high_risk_resp = client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": run_id,
                    "tool_call_id": "tc_round5_highrisk",
                    "tool_id": "high_risk_plugin",
                    "arguments": {},
                },
            )
            self.assertEqual(high_risk_resp.status_code, 200)
            high_risk_data = high_risk_resp.json()["data"]
            self.assertEqual(high_risk_data["decision"], "deny", msg=str(high_risk_data))
            self.assertIn("blocked", high_risk_data["execution_status"])
            self.assertTrue(any(rule["rule_id"] == "task-analysis-basic-tools" for rule in high_risk_data["matched_rules"]))

            boundary_resp = client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": run_id,
                    "tool_call_id": "tc_round5_boundary",
                    "tool_id": "workspace_reader",
                    "arguments": {"file_path": "../secrets.txt"},
                },
            )
            self.assertEqual(boundary_resp.status_code, 200)
            boundary_data = boundary_resp.json()["data"]
            self.assertEqual(boundary_data["decision"], "deny", msg=str(boundary_data))
            self.assertTrue(any(rule["rule_id"] == "workspace-reader-boundary" for rule in boundary_data["matched_rules"]))

            events_resp = client.get("/api/v1/events", params={"run_id": run_id})
            self.assertEqual(events_resp.status_code, 200)
            event_types = {item["event_type"] for item in events_resp.json()["data"]["events"]}
            self.assertIn("policy_check_completed", event_types)
            self.assertIn("risk_rule_matched", event_types)
            self.assertIn("disposition_applied", event_types)


if __name__ == "__main__":
    unittest.main()
