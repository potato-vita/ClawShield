from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import BadRequestError
from app.models.callback_delivery import CallbackDelivery
from app.repositories.callback_delivery_repo import CallbackDeliveryRepository, callback_delivery_repository
from app.settings import get_settings


@dataclass(frozen=True)
class IdempotencyLookupResult:
    state: str
    record: CallbackDelivery | None = None
    cached_response: dict[str, Any] | None = None


class CallbackIdempotencyService:
    """Persist callback request de-dup keys and cached responses."""

    def __init__(self, repository: CallbackDeliveryRepository) -> None:
        self._repository = repository
        self._cleanup_lock = threading.Lock()
        self._next_cleanup_epoch: float = 0.0

    @staticmethod
    def build_request_digest(payload: dict[str, Any]) -> str:
        try:
            canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        except TypeError:
            canonical = str(payload)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def build_tool_call_key(*, run_id: str, tool_call_id: str) -> str:
        return f"tool_call::{run_id}::{tool_call_id}"

    @staticmethod
    def build_tool_result_key(*, run_id: str, tool_call_id: str) -> str:
        return f"tool_result::{run_id}::{tool_call_id}"

    def begin(
        self,
        db: Session,
        *,
        request_key: str,
        callback_type: str,
        run_id: str | None,
        session_id: str | None,
        tool_call_id: str | None,
        request_payload: dict[str, Any],
    ) -> IdempotencyLookupResult:
        existing = self._repository.get_by_request_key(db=db, request_key=request_key)
        if existing is not None:
            if existing.status == "completed" and isinstance(existing.response_json, dict):
                return IdempotencyLookupResult(
                    state="replay",
                    record=existing,
                    cached_response=dict(existing.response_json),
                )
            if existing.status == "processing":
                raise BadRequestError(
                    message="duplicate callback is still in processing",
                    error_code="CALLBACK_DUPLICATE_IN_FLIGHT",
                    details={"request_key": request_key, "callback_type": callback_type},
                )
            return IdempotencyLookupResult(state="retry", record=existing)

        record = CallbackDelivery(
            request_key=request_key,
            callback_type=callback_type,
            run_id=run_id,
            session_id=session_id,
            tool_call_id=tool_call_id,
            request_digest=self.build_request_digest(request_payload),
            status="processing",
        )
        created = self._repository.create(db=db, record=record)
        return IdempotencyLookupResult(state="new", record=created)

    def complete(self, db: Session, *, record: CallbackDelivery, response_payload: dict[str, Any]) -> None:
        self._repository.mark_completed(db=db, record=record, response_json=response_payload)

    def fail(self, db: Session, *, record: CallbackDelivery, error_message: str) -> None:
        self._repository.mark_failed(db=db, record=record, error_message=error_message)

    def periodic_cleanup(self, db: Session) -> int:
        settings = get_settings()
        interval = max(int(settings.callback_delivery_cleanup_interval_seconds or 0), 60)
        retention_days = max(int(settings.callback_delivery_retention_days or 0), 1)
        now_epoch = time.time()

        with self._cleanup_lock:
            if now_epoch < self._next_cleanup_epoch:
                return 0
            self._next_cleanup_epoch = now_epoch + interval

        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        return self._repository.delete_older_than(db=db, cutoff=cutoff)


callback_idempotency_service = CallbackIdempotencyService(repository=callback_delivery_repository)
