from sqlalchemy.orm import Session

from app.db.models import TraceEvent as TraceEventModel
from app.schemas.plugin import EventBatchResponse, TraceEvent
from app.services.event_projector import project_event
from app.services.sanitizer import json_text, stable_hash
from app.services.timeutil import parse_timestamp


def ingest_events(db: Session, raw_events: list[dict]) -> EventBatchResponse:
    accepted = duplicated = failed = 0
    for raw in raw_events:
        try:
            event = TraceEvent.model_validate(raw)
            if db.get(TraceEventModel, event.event_id):
                duplicated += 1
                continue
            db.add(TraceEventModel(
                id=event.event_id,
                schema_version=event.schema_version,
                event_type=event.event_type,
                session_id=event.session_id,
                run_id=event.run_id,
                trace_id=event.trace_id,
                source=event.plugin_id or "openclaw-plugin",
                severity="info",
                payload_json=json_text(event.payload),
                payload_hash=stable_hash(event.payload),
                created_at=parse_timestamp(event.timestamp),
            ))
            project_event(db, event)
            db.commit()
            accepted += 1
        except Exception:
            db.rollback()
            failed += 1
    return EventBatchResponse(success=failed == 0, accepted=accepted, duplicated=duplicated, failed=failed)
