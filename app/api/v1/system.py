from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.errors import RuntimePipelineError
from app.schemas.common import APIResponse, success_response
from app.schemas.system import SystemStartRequest, SystemStartResponse, SystemStatusResponse, SystemStopResponse
from app.services.guardrails_service import guardrails_service
from app.services.opencaw_service import opencaw_service

router = APIRouter(prefix="/system")
logger = logging.getLogger(__name__)


@router.post("/start", response_model=APIResponse)
def start_system(payload: SystemStartRequest) -> APIResponse:
    started_at = datetime.now(timezone.utc)

    try:
        logger.info("system.start.requested mode=%s auto_launch=%s", payload.mode, payload.auto_launch_opencaw)
        opencaw_state = (
            opencaw_service.start(mode=payload.mode)
            if payload.auto_launch_opencaw
            else opencaw_service.status()
        )
        logger.info("system.start.done opencaw_state=%s", opencaw_state.get("state"))
    except RuntimeError as exc:
        raise RuntimePipelineError(
            message="failed to start system",
            error_code="SYSTEM_START_FAILED",
            details=str(exc),
        ) from exc

    response_data = SystemStartResponse(
        system_status="running",
        opencaw_status=str(opencaw_state.get("state", "unknown")),
        opencaw_pid=opencaw_state.get("pid"),
        started_at=started_at,
        mode=payload.mode,
    )
    return success_response(data=response_data.model_dump())


@router.post("/stop", response_model=APIResponse)
def stop_system() -> APIResponse:
    stopped_at = datetime.now(timezone.utc)

    try:
        logger.info("system.stop.requested")
        opencaw_state = opencaw_service.stop()
        logger.info("system.stop.done opencaw_state=%s", opencaw_state.get("state"))
    except RuntimeError as exc:
        raise RuntimePipelineError(
            message="failed to stop system",
            error_code="SYSTEM_STOP_FAILED",
            details=str(exc),
        ) from exc

    response_data = SystemStopResponse(
        system_status="running",
        opencaw_status=str(opencaw_state.get("state", "unknown")),
        opencaw_pid=opencaw_state.get("pid"),
        stopped_at=stopped_at,
    )
    return success_response(data=response_data.model_dump())


@router.get("/status", response_model=APIResponse)
def get_system_status() -> APIResponse:
    opencaw_state = opencaw_service.status()
    guardrails_state = guardrails_service.status()

    response_data = SystemStatusResponse(
        system_status="running",
        opencaw_status=str(opencaw_state.get("state", "unknown")),
        opencaw_pid=opencaw_state.get("pid"),
        guardrails_status=str(guardrails_state.get("state", "unknown")),
        guardrails_detail=guardrails_state.get("detail"),
        checked_at=datetime.now(timezone.utc),
    )
    return success_response(data=response_data.model_dump())
