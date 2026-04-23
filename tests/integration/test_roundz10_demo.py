from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


class RoundTenDemoTestCase(unittest.TestCase):
    def test_dashboard_overview_contains_round10_demo_fields(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/v1/dashboard/overview")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertTrue(payload["success"])

            data = payload["data"]
            self.assertIn("standard_scenarios", data)
            self.assertIn("free_input_examples", data)
            self.assertGreaterEqual(len(data["standard_scenarios"]), 3)
            self.assertGreaterEqual(len(data["free_input_examples"]["safe_tasks"]), 3)
            self.assertGreaterEqual(len(data["free_input_examples"]["risk_tasks"]), 3)

    def test_dashboard_can_run_standard_scenario_with_single_api_call(self) -> None:
        with TestClient(app) as client:
            response = client.post("/api/v1/dashboard/scenarios/env_then_http/run")
            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertTrue(payload["success"])

            data = payload["data"]
            self.assertEqual(data["scenario"]["scenario_id"], "env_then_http")
            self.assertIn("run_id", data)
            self.assertIn("/api/v1/ui/runs/", data["report_url"])
            self.assertIn(data["final_disposition"], {"deny", "warn", "allow"})

            report_page = client.get(data["report_url"])
            self.assertEqual(report_page.status_code, 200)

            report_api = client.get(f"/api/v1/runs/{data['run_id']}/report")
            self.assertEqual(report_api.status_code, 200)
            report_payload = report_api.json()["data"]
            self.assertIn("risk_hits", report_payload)
            self.assertGreater(len(report_payload["risk_hits"]), 0)

    def test_dashboard_run_unknown_scenario_uses_standard_error_contract(self) -> None:
        with TestClient(app) as client:
            response = client.post("/api/v1/dashboard/scenarios/not_exists/run")
            self.assertEqual(response.status_code, 404)
            payload = response.json()
            self.assertFalse(payload["success"])
            self.assertEqual(payload["error"]["error_code"], "SCENARIO_NOT_FOUND")
            self.assertEqual(payload["error"]["details"]["scenario_id"], "not_exists")


if __name__ == "__main__":
    unittest.main()

