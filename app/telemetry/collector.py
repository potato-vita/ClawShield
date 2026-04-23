from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.ids import generate_event_id
from app.models.audit_event import AuditEvent
from app.repositories.event_repo import event_repository
from app.repositories.run_repo import run_repository
from app.telemetry.normalizer import normalize_event


class TelemetryCollector:
    """Collect and persist normalized events with run-status progression."""

    _status_order = {
        "created": 0,
        "analyzing": 1,
        "tool_pending": 2,
        "executing": 3,
        "blocked": 4,
        "finished": 5,
    }

    _event_status_map = {
        "task_received": "created",
        "task_classified": "analyzing",
        "dialog_state_changed": "analyzing",
        "tool_call_requested": "tool_pending",
        "tool_execution_started": "executing",
        "tool_result_received": "finished",
    }

    def _derive_run_status(self, event_type: str, disposition: str | None = None) -> str | None:
        if event_type == "disposition_applied" and disposition == "deny":
            return "blocked"
        return self._event_status_map.get(event_type)

    def _advance_run_status(self, db: Session, run_id: str, candidate_status: str | None) -> None:
        if not candidate_status:
            return

        run = run_repository.get_by_run_id(db=db, run_id=run_id)
        if run is None:
            return

        current = run.status or "created"
        if current == "blocked" and candidate_status != "finished":
            return

        current_order = self._status_order.get(current, 0)
        candidate_order = self._status_order.get(candidate_status, current_order)
        if candidate_order >= current_order:
            run_repository.update_status(db=db, run=run, status=candidate_status)

    def collect(self, db: Session, payload: dict) -> AuditEvent:
        normalized = normalize_event(payload)
        run_id = str(normalized["run_id"])

        event = AuditEvent(
            event_id=generate_event_id(),
            run_id=run_id,
            session_id=normalized["session_id"],
            event_type=str(normalized["event_type"]),
            event_stage=normalized["event_stage"],
            actor_type=normalized["actor_type"],
            actor_id=normalized["actor_id"],
            tool_id=normalized["tool_id"],
            resource_type=normalized["resource_type"],
            resource_id=normalized["resource_id"],
            input_summary=normalized["input_summary"],
            output_summary=normalized["output_summary"],
            semantic_decision=normalized["semantic_decision"],
            policy_decision=normalized["policy_decision"],
            risk_level=normalized["risk_level"],
            disposition=normalized["disposition"],
            status=normalized["status"],
        )
        persisted = event_repository.create(db=db, event=event)

        next_status = self._derive_run_status(
            event_type=str(normalized["event_type"]),
            disposition=normalized["disposition"],
        )
        self._advance_run_status(db=db, run_id=run_id, candidate_status=next_status)

        return persisted


telemetry_collector = TelemetryCollector()
