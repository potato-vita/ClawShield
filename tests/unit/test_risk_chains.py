from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app


class RiskChainsTestCase(unittest.TestCase):
    def test_chain_workspace_escape(self) -> None:
        with TestClient(app) as client:
            run_id = self._ingest(client, "unit_chain_workspace", "请分析项目并读取上级目录秘密文件")
            client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": run_id,
                    "tool_call_id": "unit_tc_workspace",
                    "tool_id": "workspace_reader",
                    "arguments": {"file_path": "../secret.txt"},
                },
            )

            summary = self._graph_summary(client, run_id)
            self.assertIn("chain_workspace_escape", summary["chain_ids"])

    def test_chain_env_then_http(self) -> None:
        with TestClient(app) as client:
            run_id = self._ingest(client, "unit_chain_env_http", "分析环境变量并请求外部接口")
            client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": run_id,
                    "tool_call_id": "unit_tc_env",
                    "tool_id": "env_reader",
                    "arguments": {"env_key": "OPENAI_API_KEY"},
                },
            )
            client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": run_id,
                    "tool_call_id": "unit_tc_http",
                    "tool_id": "http_fetcher",
                    "arguments": {"url": "https://example.com/upload"},
                },
            )

            summary = self._graph_summary(client, run_id)
            self.assertIn("chain_env_then_http", summary["chain_ids"])

    def test_chain_analysis_high_risk_tool(self) -> None:
        with TestClient(app) as client:
            run_id = self._ingest(client, "unit_chain_tool", "分析工程并执行高危插件")
            client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": run_id,
                    "tool_call_id": "unit_tc_tool",
                    "tool_id": "danger_exec_plugin",
                    "arguments": {},
                },
            )

            summary = self._graph_summary(client, run_id)
            self.assertIn("chain_analysis_high_risk_tool", summary["chain_ids"])

    @staticmethod
    def _ingest(client: TestClient, session_id: str, user_input: str) -> str:
        response = client.post(
            "/api/v1/tasks/ingest",
            json={
                "session_id": session_id,
                "user_input": user_input,
                "source": "unit",
                "metadata": {"round": 9},
            },
        )
        assert response.status_code == 200, response.text
        return response.json()["data"]["run_id"]

    @staticmethod
    def _graph_summary(client: TestClient, run_id: str) -> dict:
        response = client.get(f"/api/v1/runs/{run_id}/graph")
        assert response.status_code == 200, response.text
        return response.json()["data"]["summary"]


if __name__ == "__main__":
    unittest.main()
