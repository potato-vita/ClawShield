from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


class AlignmentDemoTestCase(unittest.TestCase):
    def test_dashboard_overview_includes_alignment_scenarios(self) -> None:
        with TestClient(app) as client:
            overview = client.get("/api/v1/dashboard/overview")
            self.assertEqual(overview.status_code, 200)
            scenarios = overview.json()["data"]["standard_scenarios"]
            scenario_ids = {item["scenario_id"] for item in scenarios}
            self.assertIn("goal_consistent_summary_read", scenario_ids)
            self.assertIn("goal_mismatch_external_upload", scenario_ids)


if __name__ == "__main__":
    unittest.main()
