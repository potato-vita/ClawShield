from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db import get_db
from app.schemas.common import APIResponse, success_response
from app.services.goal_service import goal_service

router = APIRouter(prefix="/runs")
logger = logging.getLogger(__name__)


@router.get("/{run_id}/goal", response_model=APIResponse)
def get_run_goal(run_id: str, db: Session = Depends(get_db)) -> APIResponse:
    goal = goal_service.get_latest_by_run_id(db=db, run_id=run_id)
    if goal is None:
        raise NotFoundError(message=f"goal not found for run_id={run_id}", error_code="GOAL_NOT_FOUND")
    logger.info("goals.get run_id=%s goal_id=%s", run_id, goal.goal_id)
    return success_response(data=goal.model_dump())
