from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.ids import generate_task_id
from app.models.task import Task
from app.repositories.task_repo import TaskRepository, task_repository
from app.schemas.task import TaskIngestRequest, TaskIngestResponse
from app.services.audit_service import AuditService, audit_service
from app.services.run_service import RunService, run_service


class TaskService:
    """Handle task ingestion orchestration and transactional persistence."""

    def __init__(
        self,
        run_service_instance: RunService,
        task_repository: TaskRepository,
        audit_service_instance: AuditService,
    ) -> None:
        self._run_service = run_service_instance
        self._task_repository = task_repository
        self._audit_service = audit_service_instance

    def ingest_task(self, db: Session, payload: TaskIngestRequest) -> TaskIngestResponse:
        summary = payload.user_input[:200]

        run = self._run_service.initialize_run(
            db=db,
            session_id=payload.session_id,
            task_summary=summary,
            task_type="unknown",
        )
        task = Task(
            task_id=generate_task_id(),
            run_id=run.run_id,
            user_input=payload.user_input,
            source=payload.source,
            metadata_json=payload.metadata or None,
        )

        try:
            self._task_repository.create(db=db, task=task)

            self._audit_service.record_event(
                db=db,
                run_id=run.run_id,
                session_id=payload.session_id,
                event_type="task_received",
                event_stage="ingest",
                actor_type="user",
                input_summary=summary,
                status="recorded",
            )
            self._audit_service.record_event(
                db=db,
                run_id=run.run_id,
                session_id=payload.session_id,
                event_type="run_created",
                event_stage="ingest",
                actor_type="system",
                status="recorded",
            )

            db.commit()
        except Exception:
            db.rollback()
            raise

        return TaskIngestResponse(
            run_id=run.run_id,
            session_id=payload.session_id,
            task_type=run.task_type,
            status=run.status,
            created_at=run.created_at or datetime.now(timezone.utc),
        )


task_service = TaskService(
    run_service_instance=run_service,
    task_repository=task_repository,
    audit_service_instance=audit_service,
)
