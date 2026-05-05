from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import AppError, RuntimePipelineError
from app.db import get_db
from app.schemas.common import APIResponse, success_response
from app.schemas.task import TaskIngestRequest
from app.services.task_service import task_service

router = APIRouter(prefix="/tasks")
logger = logging.getLogger(__name__)


@router.post("/ingest", response_model=APIResponse)
def ingest_task(payload: TaskIngestRequest, db: Session = Depends(get_db)) -> APIResponse:
    try:
        logger.info("tasks.ingest.start session_id=%s source=%s", payload.session_id, payload.source)
        result = task_service.ingest_task(db, payload)
        logger.info("tasks.ingest.done run_id=%s session_id=%s", result.run_id, result.session_id)
        return success_response(data=result.model_dump())
    except AppError:
        raise
    except Exception as exc:
        logger.exception("tasks.ingest.failed session_id=%s", payload.session_id, exc_info=exc)
        raise RuntimePipelineError(
            message="failed to ingest task",
            error_code="TASK_INGEST_FAILED",
            details=str(exc),
        ) from exc
