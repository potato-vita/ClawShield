from __future__ import annotations

import hashlib
import hmac
import json
import sys
import time
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.errors import UnauthorizedError
from app.security.webhook_auth import WebhookAuthService
from app.settings import Settings


class WebhookAuthTestCase(unittest.TestCase):
    def test_disabled_mode_allows_requests(self) -> None:
        service = WebhookAuthService(settings=Settings(webhook_auth_enabled=False))
        service.verify(headers={}, payload={"x": 1})

    def test_bearer_mode_accepts_valid_token(self) -> None:
        service = WebhookAuthService(
            settings=Settings(
                webhook_auth_enabled=True,
                webhook_auth_mode="bearer",
                webhook_bearer_token="secret-token",
            )
        )
        service.verify(headers={"authorization": "Bearer secret-token"}, payload={"x": 1})

    def test_hmac_mode_rejects_replay_nonce(self) -> None:
        service = WebhookAuthService(
            settings=Settings(
                webhook_auth_enabled=True,
                webhook_auth_mode="hmac",
                webhook_hmac_secret="hmac-secret",
                webhook_hmac_tolerance_seconds=300,
            )
        )
        payload = {"session_id": "s1", "tool_id": "http_fetcher"}
        ts = int(time.time())
        nonce = "nonce-001"
        signature = self._sign(secret="hmac-secret", timestamp=ts, nonce=nonce, payload=payload)
        headers = {
            "x-clawshield-timestamp": str(ts),
            "x-clawshield-nonce": nonce,
            "x-clawshield-signature": signature,
        }
        service.verify(headers=headers, payload=payload)
        with self.assertRaises(UnauthorizedError):
            service.verify(headers=headers, payload=payload)

    def test_hmac_mode_rejects_expired_timestamp(self) -> None:
        service = WebhookAuthService(
            settings=Settings(
                webhook_auth_enabled=True,
                webhook_auth_mode="hmac",
                webhook_hmac_secret="hmac-secret",
                webhook_hmac_tolerance_seconds=3,
            )
        )
        payload = {"session_id": "s1"}
        ts = int(time.time()) - 60
        nonce = "nonce-002"
        signature = self._sign(secret="hmac-secret", timestamp=ts, nonce=nonce, payload=payload)
        headers = {
            "x-clawshield-timestamp": str(ts),
            "x-clawshield-nonce": nonce,
            "x-clawshield-signature": signature,
        }
        with self.assertRaises(UnauthorizedError):
            service.verify(headers=headers, payload=payload)

    @staticmethod
    def _sign(*, secret: str, timestamp: int, nonce: str, payload: dict) -> str:
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        message = str(timestamp).encode("utf-8") + b"." + nonce.encode("utf-8") + b"." + payload_json
        return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


if __name__ == "__main__":
    unittest.main()
