from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db import get_db
from app.schemas.common import APIResponse, success_response
from app.services.run_service import run_service

router = APIRouter(prefix="/runs")


@router.get("", response_model=APIResponse)
def list_runs(limit: int = 50, db: Session = Depends(get_db)) -> APIResponse:
    runs = run_service.list_runs(db=db, limit=limit)
    return success_response(data={"runs": [item.model_dump() for item in runs]})


@router.get("/{run_id}", response_model=APIResponse)
def get_run(run_id: str, db: Session = Depends(get_db)) -> APIResponse:
    item = run_service.get_run(db=db, run_id=run_id)
    if item is None:
        raise NotFoundError(
            message="run not found",
            details={"run_id": run_id},
            error_code="RUN_NOT_FOUND",
        )

    return success_response(data=item.model_dump())
