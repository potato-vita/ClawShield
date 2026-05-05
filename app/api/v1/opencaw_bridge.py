from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy.orm import Session

from app.core.errors import AppError, RuntimePipelineError
from app.db import get_db
from app.schemas.common import APIResponse, success_response
from app.schemas.opencaw_bridge import SessionBootstrapRequest
from app.schemas.tool_call import ToolCallRequest, ToolResultPayload
from app.services.bridge_service import bridge_service
from app.services.opencaw_callback_service import opencaw_callback_service

router = APIRouter(prefix="/bridge/opencaw")
logger = logging.getLogger(__name__)


@router.post("/session/bootstrap", response_model=APIResponse)
def bootstrap_session(payload: SessionBootstrapRequest, db: Session = Depends(get_db)) -> APIResponse:
    logger.info("bridge.session.bootstrap.start session_id=%s", payload.session_id)
    try:
        response_payload = opencaw_callback_service.bootstrap_session(
            db=db,
            session_id=payload.session_id,
            user_input=payload.user_input,
        )
        db.commit()
    except AppError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise RuntimePipelineError(
            message=f"session bootstrap failed: {exc}",
            error_code="SESSION_BOOTSTRAP_FAILED",
            details={"session_id": payload.session_id},
        ) from exc

    logger.info(
        "bridge.session.bootstrap.done session_id=%s run_id=%s",
        payload.session_id,
        response_payload["run_id"],
    )
    return success_response(data=response_payload, message="session bootstrapped")


@router.post("/tool-call", response_model=APIResponse)
def handle_tool_call(payload: ToolCallRequest, db: Session = Depends(get_db)) -> APIResponse:
    logger.info(
        "bridge.tool_call.start run_id=%s tool_call_id=%s tool_id=%s",
        payload.run_id,
        payload.tool_call_id,
        payload.tool_id,
    )

    try:
        response_payload = bridge_service.process_tool_call(db=db, payload=payload)
        db.commit()
    except AppError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise RuntimePipelineError(
            message=f"tool-call pipeline failed: {exc}",
            error_code="TOOL_CALL_PIPELINE_ERROR",
            details={"run_id": payload.run_id, "tool_call_id": payload.tool_call_id},
        ) from exc

    logger.info(
        "bridge.tool_call.done run_id=%s tool_call_id=%s decision=%s execution_status=%s",
        payload.run_id,
        payload.tool_call_id,
        response_payload["decision"],
        response_payload["execution_status"],
    )

    return success_response(data=response_payload)


@router.post("/callback/tool-call", response_model=APIResponse)
def handle_tool_call_callback(payload: dict[str, Any] = Body(...), db: Session = Depends(get_db)) -> APIResponse:
    logger.info(
        "bridge.callback.tool_call.start run_id=%s session_id=%s",
        payload.get("run_id"),
        payload.get("session_id"),
    )
    try:
        response_payload = opencaw_callback_service.process_tool_call_callback(db=db, payload=payload)
        db.commit()
    except AppError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise RuntimePipelineError(
            message=f"callback tool-call failed: {exc}",
            error_code="CALLBACK_TOOL_CALL_FAILED",
            details={"run_id": payload.get("run_id"), "session_id": payload.get("session_id")},
        ) from exc

    logger.info(
        "bridge.callback.tool_call.done run_id=%s processed_count=%s",
        response_payload["run_id"],
        response_payload["processed_count"],
    )
    return success_response(data=response_payload)


@router.post("/tool-result", response_model=APIResponse)
def handle_tool_result(payload: ToolResultPayload, db: Session = Depends(get_db)) -> APIResponse:
    logger.info(
        "bridge.tool_result.start run_id=%s tool_call_id=%s tool_id=%s status=%s",
        payload.run_id,
        payload.tool_call_id,
        payload.tool_id,
        payload.execution_status,
    )

    try:
        response_payload = bridge_service.process_tool_result(db=db, payload=payload)
        db.commit()
    except AppError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise RuntimePipelineError(
            message=f"tool-result persistence failed: {exc}",
            error_code="TOOL_RESULT_FAILED",
            details={"run_id": payload.run_id, "tool_call_id": payload.tool_call_id},
        ) from exc

    logger.info(
        "bridge.tool_result.done run_id=%s tool_call_id=%s status=%s",
        payload.run_id,
        payload.tool_call_id,
        payload.execution_status,
    )

    return success_response(data=response_payload)


@router.post("/callback/tool-result", response_model=APIResponse)
def handle_tool_result_callback(payload: dict[str, Any] = Body(...), db: Session = Depends(get_db)) -> APIResponse:
    logger.info(
        "bridge.callback.tool_result.start run_id=%s session_id=%s",
        payload.get("run_id"),
        payload.get("session_id"),
    )
    try:
        response_payload = opencaw_callback_service.process_tool_result_callback(db=db, payload=payload)
        db.commit()
    except AppError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise RuntimePipelineError(
            message=f"callback tool-result failed: {exc}",
            error_code="CALLBACK_TOOL_RESULT_FAILED",
            details={"run_id": payload.get("run_id"), "session_id": payload.get("session_id")},
        ) from exc

    logger.info(
        "bridge.callback.tool_result.done run_id=%s processed_count=%s",
        response_payload["run_id"],
        response_payload["processed_count"],
    )
    return success_response(data=response_payload)


@router.post("/callback/message", response_model=APIResponse)
def handle_message_callback(payload: dict[str, Any] = Body(...), db: Session = Depends(get_db)) -> APIResponse:
    logger.info(
        "bridge.callback.message.start run_id=%s session_id=%s",
        payload.get("run_id"),
        payload.get("session_id"),
    )
    try:
        response_payload = opencaw_callback_service.process_message_callback(db=db, payload=payload)
        db.commit()
    except AppError:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise RuntimePipelineError(
            message=f"callback message failed: {exc}",
            error_code="CALLBACK_MESSAGE_FAILED",
            details={"run_id": payload.get("run_id"), "session_id": payload.get("session_id")},
        ) from exc

    logger.info(
        "bridge.callback.message.done run_id=%s processed_count=%s",
        response_payload["run_id"],
        response_payload["processed_count"],
    )
    return success_response(data=response_payload)
