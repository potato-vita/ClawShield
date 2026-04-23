from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app


class RoundFourGatewayTestCase(unittest.TestCase):
    def test_gateway_chain_for_multiple_action_types(self) -> None:
        with TestClient(app) as client:
            ingest_resp = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": "sess_round4",
                    "user_input": "请分析这些信息",
                    "source": "ui",
                    "metadata": {"round": 4},
                },
            )
            self.assertEqual(ingest_resp.status_code, 200)
            run_id = ingest_resp.json()["data"]["run_id"]

            payloads = [
                {
                    "run_id": run_id,
                    "tool_call_id": "tc_round4_file",
                    "tool_id": "workspace_reader",
                    "arguments": {"file_path": "./workspace/a.txt"},
                },
                {
                    "run_id": run_id,
                    "tool_call_id": "tc_round4_http",
                    "tool_id": "http_fetcher",
                    "arguments": {"url": "https://example.com/api"},
                },
                {
                    "run_id": run_id,
                    "tool_call_id": "tc_round4_env",
                    "tool_id": "env_reader",
                    "arguments": {"env_key": "OPENAI_KEY"},
                },
            ]

            for payload in payloads:
                response = client.post("/api/v1/bridge/opencaw/tool-call", json=payload)
                self.assertEqual(response.status_code, 200)
                data = response.json()["data"]
                self.assertIn(data["decision"], ["allow", "warn", "deny"])
                self.assertIn("execution_status", data)

            tool_result_resp = client.post(
                "/api/v1/bridge/opencaw/tool-result",
                json={
                    "run_id": run_id,
                    "tool_call_id": "tc_round4_http",
                    "tool_id": "http_fetcher",
                    "result_summary": "http mock completed",
                    "raw_result": {"ok": True},
                    "execution_status": "ok",
                    "latency_ms": 10,
                },
            )
            self.assertEqual(tool_result_resp.status_code, 200)
            self.assertTrue(tool_result_resp.json()["data"]["accepted"])

            events_resp = client.get("/api/v1/events", params={"run_id": run_id})
            self.assertEqual(events_resp.status_code, 200)
            events = events_resp.json()["data"]["events"]
            event_types = [item["event_type"] for item in events]

            self.assertIn("tool_call_requested", event_types)
            self.assertIn("resource_access_requested", event_types)
            self.assertIn("tool_execution_started", event_types)
            self.assertIn("tool_execution_completed", event_types)
            self.assertIn("tool_result_received", event_types)

            self.assertGreaterEqual(event_types.count("resource_access_requested"), 3)


if __name__ == "__main__":
    unittest.main()
