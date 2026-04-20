import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.db_models import EventDB
from app.models.schemas_event import EventCreate
from app.utils.ids import new_id
from app.utils.jsonlog import configure_logger
from app.utils.time import utc_now


class RuntimeMonitor:
    def __init__(self, db: Session, log_file: str):
        self.db = db
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = configure_logger("clawshield.runtime", str(log_path))

    def record_event(self, event: EventCreate) -> EventDB:
        event_db = EventDB(
            event_id=new_id("evt"),
            run_id=event.run_id,
            task_id=event.task_id,
            parent_event_id=event.parent_event_id,
            event_type=event.event_type,
            action=event.action,
            resource_type=event.resource_type,
            resource=event.resource,
            params_summary=event.params_summary,
            decision=event.decision,
            result_status=event.result_status,
            severity=event.severity,
            message=event.message,
            created_at=utc_now(),
            trace_id=event.trace_id,
            metadata_json=event.metadata,
        )
        self.db.add(event_db)
        self.db.commit()
        self.db.refresh(event_db)

        self.logger.info(
            "runtime_event",
            extra={
                "run_id": event_db.run_id,
                "event_id": event_db.event_id,
                "action": event_db.action,
                "resource": event_db.resource,
                "decision": event_db.decision,
                "result": event_db.result_status,
                "metadata": json.dumps(event_db.metadata_json, ensure_ascii=True),
            },
        )
        return event_db

    def list_events(self, run_id: str) -> list[EventDB]:
        return (
            self.db.query(EventDB)
            .filter(EventDB.run_id == run_id)
            .order_by(EventDB.created_at.asc())
            .all()
        )
