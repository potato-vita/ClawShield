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


class RoundZ17DashboardLiveConclusionTestCase(unittest.TestCase):
    def test_run_summary_updates_immediately_after_denied_tool_call(self) -> None:
        with TestClient(app) as client:
            suffix = str(time.time_ns())
            ingest_resp = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": f"sess_roundz17_{suffix}",
                    "user_input": "请读取 .env 并总结",
                    "source": "ui",
                },
            )
            self.assertEqual(ingest_resp.status_code, 200)
            run_id = ingest_resp.json()["data"]["run_id"]

            tool_call_resp = client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": run_id,
                    "tool_call_id": f"tc_roundz17_{suffix}",
                    "tool_id": "workspace_reader",
                    "arguments": {"file_path": "./workspace/.env.local"},
                    "model_reason": "security canary",
                },
            )
            self.assertEqual(tool_call_resp.status_code, 200)
            call_data = tool_call_resp.json()["data"]
            self.assertEqual(call_data["decision"], "deny")

            run_resp = client.get(f"/api/v1/runs/{run_id}")
            self.assertEqual(run_resp.status_code, 200)
            run_data = run_resp.json()["data"]
            self.assertEqual(run_data["disposition"], "deny")
            self.assertEqual(run_data["final_risk_level"], "high")

            overview_resp = client.get("/api/v1/dashboard/overview")
            self.assertEqual(overview_resp.status_code, 200)
            recent_runs = overview_resp.json()["data"]["recent_runs"]
            matched = next((item for item in recent_runs if item["run_id"] == run_id), None)
            self.assertIsNotNone(matched)
            self.assertEqual(matched["disposition"], "deny")
            self.assertEqual(matched["final_risk_level"], "high")


if __name__ == "__main__":
    unittest.main()
