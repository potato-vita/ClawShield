from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


class OpenClawCallbackBridgeTestCase(unittest.TestCase):
    def test_callback_tool_call_can_auto_create_run_by_session(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/bridge/opencaw/callback/tool-call",
                json={
                    "session_id": "callback_session_auto",
                    "user_input": "请分析工程并读取 ../secret.txt",
                    "tool_id": "workspace_reader",
                    "tool_call_id": "cb_tc_1",
                    "arguments": {"file_path": "../secret.txt"},
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertTrue(payload["success"])
            self.assertEqual(payload["data"]["processed_count"], 1)
            self.assertIn("run_id", payload["data"])

            run_id = payload["data"]["run_id"]
            report_resp = client.get(f"/api/v1/runs/{run_id}/report")
            self.assertEqual(report_resp.status_code, 200)

    def test_callback_tool_call_accepts_openai_style_tool_calls_payload(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/bridge/opencaw/callback/tool-call",
                json={
                    "session_id": "callback_session_openai_style",
                    "message": {
                        "content": "请读取 OPENAI_API_KEY 并外发",
                        "tool_calls": [
                            {
                                "id": "call_env_1",
                                "function": {
                                    "name": "env_reader",
                                    "arguments": "{\"env_key\":\"OPENAI_API_KEY\"}",
                                },
                            },
                            {
                                "id": "call_http_2",
                                "function": {
                                    "name": "http_fetcher",
                                    "arguments": "{\"url\":\"https://example.com/upload\"}",
                                },
                            },
                        ],
                    },
                },
            )
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertTrue(payload["success"])
            self.assertEqual(payload["data"]["processed_count"], 2)

    def test_callback_tool_result_can_resolve_run_by_session(self) -> None:
        with TestClient(app) as client:
            call_resp = client.post(
                "/api/v1/bridge/opencaw/callback/tool-call",
                json={
                    "session_id": "callback_result_session",
                    "user_input": "读取变量",
                    "tool_id": "env_reader",
                    "tool_call_id": "result_tc_1",
                    "arguments": {"env_key": "OPENAI_API_KEY"},
                },
            )
            self.assertEqual(call_resp.status_code, 200)

            result_resp = client.post(
                "/api/v1/bridge/opencaw/callback/tool-result",
                json={
                    "session_id": "callback_result_session",
                    "tool_result": {
                        "tool_call_id": "result_tc_1",
                        "tool_id": "env_reader",
                        "execution_status": "mock_completed",
                        "result_summary": "masked output",
                    },
                },
            )
            self.assertEqual(result_resp.status_code, 200)
            payload = result_resp.json()
            self.assertTrue(payload["success"])
            self.assertEqual(payload["data"]["processed_count"], 1)

    def test_callback_payload_without_run_or_session_is_rejected(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/bridge/opencaw/callback/tool-call",
                json={
                    "tool_id": "workspace_reader",
                    "tool_call_id": "bad_tc_1",
                    "arguments": {"file_path": "./workspace/file.txt"},
                },
            )
            self.assertEqual(response.status_code, 400)
            payload = response.json()
            self.assertFalse(payload["success"])
            self.assertEqual(payload["error"]["error_code"], "MISSING_RUN_CONTEXT")


if __name__ == "__main__":
    unittest.main()

