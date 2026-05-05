from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.common import APIResponse, success_response
from app.services.task_state_service import task_state_service

router = APIRouter(prefix="/runs")


@router.get("/{run_id}/steps", response_model=APIResponse)
def list_run_steps(run_id: str, db: Session = Depends(get_db)) -> APIResponse:
    steps = task_state_service.list_steps(db=db, run_id=run_id)
    return success_response(data={"run_id": run_id, "steps": [item.model_dump() for item in steps]})
