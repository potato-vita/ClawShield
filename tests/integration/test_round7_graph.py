from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app


class RoundSevenGraphTestCase(unittest.TestCase):
    def test_three_standard_risk_chains_and_graph_payload(self) -> None:
        with TestClient(app) as client:
            workspace_run = self._create_run(client, "sess_round7_workspace", "请分析项目并读取上级目录秘密文件")
            client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": workspace_run,
                    "tool_call_id": "tc_round7_workspace",
                    "tool_id": "workspace_reader",
                    "arguments": {"file_path": "../secret.txt"},
                },
            )
            workspace_graph = self._get_graph(client, workspace_run)
            self.assertIn("chain_workspace_escape", workspace_graph["summary"]["chain_ids"])
            self.assertGreater(len(workspace_graph["nodes"]), 0)
            self.assertGreater(len(workspace_graph["edges"]), 0)
            self.assertGreater(len(workspace_graph["highlighted_paths"]), 0)

            env_http_run = self._create_run(client, "sess_round7_env_http", "分析环境变量并请求外部接口")
            client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": env_http_run,
                    "tool_call_id": "tc_round7_env",
                    "tool_id": "env_reader",
                    "arguments": {"env_key": "OPENAI_API_KEY"},
                },
            )
            client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": env_http_run,
                    "tool_call_id": "tc_round7_http",
                    "tool_id": "http_fetcher",
                    "arguments": {"url": "https://example.com/upload"},
                },
            )
            env_http_graph = self._get_graph(client, env_http_run)
            self.assertIn("chain_env_then_http", env_http_graph["summary"]["chain_ids"])

            high_risk_run = self._create_run(client, "sess_round7_tool", "分析这个项目并执行高危插件")
            client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": high_risk_run,
                    "tool_call_id": "tc_round7_tool",
                    "tool_id": "danger_exec_plugin",
                    "arguments": {},
                },
            )
            high_risk_graph = self._get_graph(client, high_risk_run)
            self.assertIn("chain_analysis_high_risk_tool", high_risk_graph["summary"]["chain_ids"])

            events_resp = client.get(
                "/api/v1/events",
                params={"run_id": high_risk_run, "order": "asc", "limit": 300},
            )
            self.assertEqual(events_resp.status_code, 200)
            event_types = {item["event_type"] for item in events_resp.json()["data"]["events"]}
            self.assertIn("risk_chain_formed", event_types)
            self.assertIn("final_risk_conclusion_generated", event_types)

    @staticmethod
    def _create_run(client: TestClient, session_id: str, user_input: str) -> str:
        response = client.post(
            "/api/v1/tasks/ingest",
            json={
                "session_id": session_id,
                "user_input": user_input,
                "source": "ui",
                "metadata": {"round": 7},
            },
        )
        assert response.status_code == 200, response.text
        return response.json()["data"]["run_id"]

    @staticmethod
    def _get_graph(client: TestClient, run_id: str) -> dict:
        response = client.get(f"/api/v1/runs/{run_id}/graph")
        assert response.status_code == 200, response.text
        return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
