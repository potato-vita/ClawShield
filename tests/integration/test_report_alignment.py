from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


class ReportAlignmentTestCase(unittest.TestCase):
    def test_report_contains_alignment_sections(self) -> None:
        with TestClient(app) as client:
            ingest = client.post(
                "/api/v1/tasks/ingest",
                json={"session_id": "report_align_1", "user_input": "请总结 workspace/a.md", "source": "test"},
            )
            run_id = ingest.json()["data"]["run_id"]
            _ = client.post(
                "/api/v1/bridge/opencaw/tool-call",
                json={
                    "run_id": run_id,
                    "tool_call_id": "report_align_call_1",
                    "tool_id": "workspace_reader",
                    "arguments": {"file_path": "./workspace/a.md"},
                    "model_reason": "read for summary",
                },
            )
            report = client.get(f"/api/v1/runs/{run_id}/report")
            self.assertEqual(report.status_code, 200)
            data = report.json()["data"]
            self.assertIn("goal_summary", data)
            self.assertIn("alignment_summary", data)
            self.assertIn("impact_summary", data)
            self.assertIn("explainability_trace", data)
            self.assertGreaterEqual(len(data["explainability_trace"]), 1)
            trace = data["explainability_trace"][0]
            self.assertIn("justification_ref", trace)
            self.assertIn("counterfactual_note", trace)


if __name__ == "__main__":
    unittest.main()
