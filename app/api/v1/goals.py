from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db import get_db
from app.schemas.common import APIResponse, success_response
from app.services.goal_service import goal_service

router = APIRouter(prefix="/runs")


@router.get("/{run_id}/goal", response_model=APIResponse)
def get_goal(run_id: str, db: Session = Depends(get_db)) -> APIResponse:
    goal = goal_service.get_goal_summary_by_run_id(db=db, run_id=run_id)
    if goal is None:
        raise NotFoundError(
            message="goal not found",
            details={"run_id": run_id},
            error_code="GOAL_NOT_FOUND",
        )

    return success_response(data=goal.model_dump())
