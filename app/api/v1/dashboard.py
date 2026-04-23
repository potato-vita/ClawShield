from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import AppError, RuntimePipelineError
from app.db import get_db
from app.schemas.common import APIResponse, success_response
from app.services.demo_service import demo_service
from app.services.run_service import run_service

router = APIRouter(prefix="/dashboard")


@router.get("/overview", response_model=APIResponse)
def get_overview(db: Session = Depends(get_db)) -> APIResponse:
    runs = run_service.list_runs(db=db, limit=100)

    high_risk_count = sum(1 for item in runs if (item.final_risk_level or "").lower() in {"high", "critical", "severe"})
    blocked_count = sum(1 for item in runs if (item.disposition or "").lower() in {"deny", "block"})

    return success_response(
        data={
            "recent_runs": [item.model_dump() for item in runs[:10]],
            "high_risk_count": high_risk_count,
            "blocked_count": blocked_count,
            "standard_scenarios": demo_service.list_standard_scenarios(),
            "free_input_examples": demo_service.free_input_examples(),
        }
    )


@router.post("/scenarios/{scenario_id}/run", response_model=APIResponse)
def run_standard_scenario(scenario_id: str, db: Session = Depends(get_db)) -> APIResponse:
    try:
        result = demo_service.run_standard_scenario(db=db, scenario_id=scenario_id)
        db.commit()
    except AppError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise RuntimePipelineError(
            message="failed to run dashboard scenario",
            error_code="DASHBOARD_SCENARIO_RUN_FAILED",
            details={"scenario_id": scenario_id, "reason": str(exc)},
        ) from exc

    return success_response(data=result, message="standard scenario executed")
