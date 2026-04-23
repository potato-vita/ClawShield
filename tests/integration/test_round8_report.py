from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from app.main import app


class RoundEightReportTestCase(unittest.TestCase):
    def test_report_endpoint_returns_complete_report_view_model(self) -> None:
        with TestClient(app) as client:
            ingest_resp = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": "sess_round8",
                    "user_input": "分析环境变量并发送到远程接口",
                    "source": "ui",
                    "metadata": {"round": 8},
                },
            )
            self.assertEqual(ingest_resp.status_code, 200)
            run_id = ingest_resp.json()["data"]["run_id"]

            client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": run_id,
                    "tool_call_id": "tc_round8_env",
                    "tool_id": "env_reader",
                    "arguments": {"env_key": "OPENAI_API_KEY"},
                },
            )
            client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": run_id,
                    "tool_call_id": "tc_round8_http",
                    "tool_id": "http_fetcher",
                    "arguments": {"url": "https://example.com/upload"},
                },
            )

            report_resp = client.get(f"/api/v1/runs/{run_id}/report")
            self.assertEqual(report_resp.status_code, 200)
            report = report_resp.json()["data"]

            for key in [
                "task_summary",
                "semantic_summary",
                "tool_calls",
                "resources",
                "risk_hits",
                "timeline",
                "graph",
                "conclusion",
                "final_risk_level",
                "final_disposition",
                "disposition_summary",
            ]:
                self.assertIn(key, report)

            self.assertGreater(len(report["timeline"]), 0)
            self.assertGreater(len(report["graph"]["nodes"]), 0)
            self.assertGreater(len(report["graph"]["edges"]), 0)
            self.assertGreater(len(report["risk_hits"]), 0)
            self.assertIn("chain_env_then_http", {item["chain_id"] for item in report["risk_hits"]})

            # Lightweight pages should be accessible for demo.
            dashboard_page = client.get("/api/v1/ui/dashboard")
            self.assertEqual(dashboard_page.status_code, 200)
            run_detail_page = client.get(f"/api/v1/ui/runs/{run_id}")
            self.assertEqual(run_detail_page.status_code, 200)
            report_page = client.get(f"/api/v1/ui/runs/{run_id}/report")
            self.assertEqual(report_page.status_code, 200)


if __name__ == "__main__":
    unittest.main()
