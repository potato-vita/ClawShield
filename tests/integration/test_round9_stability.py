from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


class RoundNineStabilityTestCase(unittest.TestCase):
    def test_run_not_found_uses_standard_error_contract(self) -> None:
        with TestClient(app) as client:
            missing_run_id = "run_missing_round9"
            response = client.get(f"/api/v1/runs/{missing_run_id}")
            self.assertEqual(response.status_code, 404)

            payload = response.json()
            self.assertFalse(payload["success"])
            self.assertEqual(payload["message"], "run not found")
            self.assertEqual(payload["error"]["error_code"], "RUN_NOT_FOUND")
            self.assertEqual(payload["error"]["details"]["run_id"], missing_run_id)

    def test_report_not_found_uses_standard_error_contract(self) -> None:
        with TestClient(app) as client:
            missing_run_id = "run_missing_report_round9"
            response = client.get(f"/api/v1/runs/{missing_run_id}/report")
            self.assertEqual(response.status_code, 404)

            payload = response.json()
            self.assertFalse(payload["success"])
            self.assertEqual(payload["message"], "run not found")
            self.assertEqual(payload["error"]["error_code"], "RUN_NOT_FOUND")
            self.assertEqual(payload["error"]["details"]["run_id"], missing_run_id)

    def test_validation_error_uses_standard_error_contract(self) -> None:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/tasks/ingest",
                json={
                    "session_id": "round9_validation",
                    "user_input": "",
                    "source": "test",
                },
            )
            self.assertEqual(response.status_code, 422)

            payload = response.json()
            self.assertFalse(payload["success"])
            self.assertEqual(payload["message"], "request validation failed")
            self.assertEqual(payload["error"]["error_code"], "VALIDATION_ERROR")
            self.assertIsInstance(payload["error"]["details"], list)


if __name__ == "__main__":
    unittest.main()
