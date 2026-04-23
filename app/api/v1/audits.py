from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import AppError, RuntimePipelineError
from app.db import get_db
from app.schemas.common import APIResponse, success_response
from app.services.report_service import report_service

router = APIRouter(prefix="/runs")


@router.get("/{run_id}/report", response_model=APIResponse)
def get_report(run_id: str, db: Session = Depends(get_db)) -> APIResponse:
    try:
        report = report_service.get_report(db=db, run_id=run_id)
        db.commit()
    except AppError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise RuntimePipelineError(
            message="report generation failed",
            error_code="REPORT_BUILD_FAILED",
            details={"run_id": run_id, "reason": str(exc)},
        ) from exc

    return success_response(data=report.model_dump())
