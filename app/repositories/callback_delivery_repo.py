from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.callback_delivery import CallbackDelivery


class CallbackDeliveryRepository:
    def get_by_request_key(self, db: Session, request_key: str) -> CallbackDelivery | None:
        stmt = select(CallbackDelivery).where(CallbackDelivery.request_key == request_key).limit(1)
        return db.execute(stmt).scalars().first()

    def create(self, db: Session, record: CallbackDelivery) -> CallbackDelivery:
        db.add(record)
        db.flush()
        return record

    def mark_completed(self, db: Session, record: CallbackDelivery, response_json: dict) -> CallbackDelivery:
        record.status = "completed"
        record.response_json = response_json
        record.last_error = None
        db.add(record)
        db.flush()
        return record

    def mark_failed(self, db: Session, record: CallbackDelivery, error_message: str) -> CallbackDelivery:
        record.status = "failed"
        record.last_error = error_message
        db.add(record)
        db.flush()
        return record

    def delete_older_than(self, db: Session, *, cutoff: datetime) -> int:
        stmt = delete(CallbackDelivery).where(CallbackDelivery.created_at < cutoff)
        result = db.execute(stmt)
        return int(result.rowcount or 0)


callback_delivery_repository = CallbackDeliveryRepository()
