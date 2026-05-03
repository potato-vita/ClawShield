from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from typing import Any, Mapping

from app.core.errors import ConfigError, UnauthorizedError
from app.settings import Settings, get_settings


class _ReplayNonceCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seen: dict[str, int] = {}

    def check_and_mark(self, nonce: str, ts: int, ttl_seconds: int) -> None:
        threshold = int(time.time()) - max(ttl_seconds, 1)
        with self._lock:
            expired = [key for key, value in self._seen.items() if value < threshold]
            for key in expired:
                self._seen.pop(key, None)

            previous = self._seen.get(nonce)
            if previous is not None and previous >= threshold:
                raise UnauthorizedError(
                    message="webhook nonce replay detected",
                    error_code="WEBHOOK_REPLAY_DETECTED",
                    details={"nonce": nonce},
                )
            self._seen[nonce] = ts


class WebhookAuthService:
    """Validate callback authentication and replay protection."""

    _HEADER_TIMESTAMP = "x-clawshield-timestamp"
    _HEADER_NONCE = "x-clawshield-nonce"
    _HEADER_SIGNATURE = "x-clawshield-signature"
    _HEADER_AUTHORIZATION = "authorization"

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._replay_cache = _ReplayNonceCache()

    def verify(self, *, headers: Mapping[str, str], payload: dict[str, Any]) -> None:
        if not self._settings.webhook_auth_enabled:
            return

        mode = (self._settings.webhook_auth_mode or "either").strip().lower()
        if mode not in {"bearer", "hmac", "either"}:
            raise ConfigError(
                message="invalid webhook_auth_mode",
                details={"webhook_auth_mode": self._settings.webhook_auth_mode},
            )

        bearer_ok = self._verify_bearer(headers=headers) if mode in {"bearer", "either"} else False
        hmac_ok = self._verify_hmac(headers=headers, payload=payload) if mode in {"hmac", "either"} else False

        if mode == "bearer" and not bearer_ok:
            raise UnauthorizedError(
                message="webhook bearer token validation failed",
                error_code="WEBHOOK_BEARER_AUTH_FAILED",
            )
        if mode == "hmac" and not hmac_ok:
            raise UnauthorizedError(
                message="webhook hmac validation failed",
                error_code="WEBHOOK_HMAC_AUTH_FAILED",
            )
        if mode == "either" and not (bearer_ok or hmac_ok):
            raise UnauthorizedError(
                message="webhook authentication failed",
                error_code="WEBHOOK_AUTH_FAILED",
            )

    def _verify_bearer(self, *, headers: Mapping[str, str]) -> bool:
        token = (self._settings.webhook_bearer_token or "").strip()
        if not token:
            return False

        auth_header = (headers.get(self._HEADER_AUTHORIZATION) or "").strip()
        if not auth_header.lower().startswith("bearer "):
            return False
        provided = auth_header[7:].strip()
        return bool(provided) and hmac.compare_digest(provided, token)

    def _verify_hmac(self, *, headers: Mapping[str, str], payload: dict[str, Any]) -> bool:
        secret = (self._settings.webhook_hmac_secret or "").strip()
        if not secret:
            return False

        timestamp_raw = (headers.get(self._HEADER_TIMESTAMP) or "").strip()
        nonce = (headers.get(self._HEADER_NONCE) or "").strip()
        signature_raw = (headers.get(self._HEADER_SIGNATURE) or "").strip()
        if not timestamp_raw or not nonce or not signature_raw:
            return False

        try:
            timestamp = int(timestamp_raw)
        except ValueError:
            raise UnauthorizedError(
                message="invalid webhook timestamp",
                error_code="WEBHOOK_TIMESTAMP_INVALID",
                details={"timestamp": timestamp_raw},
            )

        tolerance = max(int(self._settings.webhook_hmac_tolerance_seconds or 0), 1)
        now = int(time.time())
        if abs(now - timestamp) > tolerance:
            raise UnauthorizedError(
                message="webhook timestamp outside tolerance window",
                error_code="WEBHOOK_TIMESTAMP_EXPIRED",
                details={"timestamp": timestamp, "now": now, "tolerance_seconds": tolerance},
            )

        signature = signature_raw
        if signature.lower().startswith("sha256="):
            signature = signature.split("=", 1)[1].strip()

        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        signed_payload = timestamp_raw.encode("utf-8") + b"." + nonce.encode("utf-8") + b"." + payload_json
        expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise UnauthorizedError(
                message="invalid webhook signature",
                error_code="WEBHOOK_SIGNATURE_INVALID",
            )

        self._replay_cache.check_and_mark(nonce=nonce, ts=timestamp, ttl_seconds=tolerance)
        return True


webhook_auth_service = WebhookAuthService()
