from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


class OpenClawBlockModeApiTestCase(unittest.TestCase):
    def test_block_mode_get_and_set_endpoints(self) -> None:
        with (
            patch(
                "app.api.v1.system.opencaw_block_mode_service.status",
                return_value={
                    "enforce_block": False,
                    "fail_closed": False,
                    "config_path": "/tmp/openclaw.json",
                    "checked_at": "2026-05-04T00:00:00+00:00",
                },
            ),
            patch(
                "app.api.v1.system.opencaw_block_mode_service.set_mode",
                return_value={
                    "enforce_block": True,
                    "fail_closed": True,
                    "config_path": "/tmp/openclaw.json",
                    "applied_at": "2026-05-04T00:00:01+00:00",
                },
            ) as set_mode_mock,
            TestClient(app) as client,
        ):
            status_resp = client.get("/api/v1/system/opencaw/block-mode")
            self.assertEqual(status_resp.status_code, 200)
            status_payload = status_resp.json()
            self.assertTrue(status_payload["success"])
            self.assertFalse(status_payload["data"]["enforce_block"])
            self.assertFalse(status_payload["data"]["fail_closed"])

            set_resp = client.post(
                "/api/v1/system/opencaw/block-mode",
                json={"enforce_block": True, "fail_closed": True},
            )
            self.assertEqual(set_resp.status_code, 200)
            set_payload = set_resp.json()
            self.assertTrue(set_payload["success"])
            self.assertTrue(set_payload["data"]["enforce_block"])
            self.assertTrue(set_payload["data"]["fail_closed"])
            set_mode_mock.assert_called_once_with(enforce_block=True, fail_closed=True)

    def test_system_status_includes_block_mode_fields(self) -> None:
        with (
            patch(
                "app.api.v1.system.opencaw_block_mode_service.status",
                return_value={
                    "enforce_block": True,
                    "fail_closed": True,
                    "config_path": "/tmp/openclaw.json",
                    "checked_at": "2026-05-04T00:00:00+00:00",
                },
            ),
            TestClient(app) as client,
        ):
            resp = client.get("/api/v1/system/status")
            self.assertEqual(resp.status_code, 200)
            payload = resp.json()
            self.assertTrue(payload["success"])
            self.assertTrue(payload["data"]["opencaw_enforce_block"])
            self.assertTrue(payload["data"]["opencaw_fail_closed"])


if __name__ == "__main__":
    unittest.main()

