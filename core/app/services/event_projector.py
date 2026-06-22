from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import OpenClawRun, ToolCall, ToolResult
from app.db.repositories import get_or_create_run
from app.schemas.plugin import TraceEvent
from app.services.idgen import new_id
from app.services.sanitizer import json_text, redact_text, stable_hash
from app.services.timeutil import parse_timestamp


def project_event(db: Session, event: TraceEvent) -> None:
    payload = event.payload
    if event.run_id:
        get_or_create_run(db, event.run_id, event.session_id)

    if event.event_type == "before_tool_call":
        tool_id = str(payload.get("tool_call_id") or new_id("tool"))
        call = db.get(ToolCall, tool_id)
        if call is None:
            call = ToolCall(
                id=tool_id,
                run_id=event.run_id,
                session_id=event.session_id,
                trace_id=event.trace_id,
                tool_name=str(payload.get("tool_name") or "unknown"),
                tool_kind=str(payload.get("tool_kind") or "unknown"),
                status="pending",
                raw_params_json=json_text(payload.get("params") or payload.get("raw_params") or {}),
                sanitized_params_json=json_text(payload.get("params") or payload.get("raw_params") or {}),
                param_summary=json_text(payload.get("param_summary") or {}),
                resource_value=redact_text(payload.get("resource_hint") or "", 300),
                started_at=parse_timestamp(event.timestamp),
            )
            db.add(call)
    elif event.event_type == "after_tool_call":
        tool_id = str(payload.get("tool_call_id") or new_id("tool"))
        call = db.get(ToolCall, tool_id)
        if call is None:
            call = ToolCall(
                id=tool_id,
                run_id=event.run_id,
                session_id=event.session_id,
                trace_id=event.trace_id,
                tool_name=str(payload.get("tool_name") or "unknown"),
                tool_kind=str(payload.get("tool_kind") or "unknown"),
                status="completed",
                started_at=parse_timestamp(event.timestamp),
            )
            db.add(call)
            db.flush()
        call.status = "failed" if payload.get("error") else "completed"
        call.ended_at = parse_timestamp(event.timestamp)
        call.latency_ms = payload.get("duration_ms") if isinstance(payload.get("duration_ms"), int) else None
        result = ToolResult(
            id=new_id("result"),
            tool_call_id=tool_id,
            success=not bool(payload.get("error")),
            exit_code=payload.get("exit_code") if isinstance(payload.get("exit_code"), int) else None,
            result_preview=redact_text(payload.get("result_preview") or ""),
            result_hash=str(payload.get("result_hash") or stable_hash(payload.get("result_preview") or "")),
            result_size=int(payload.get("result_size") or len(str(payload.get("result_preview") or ""))),
            error_message=redact_text(payload.get("error") or "") or None,
        )
        db.add(result)
    elif event.event_type == "agent_end" and event.run_id:
        run = db.get(OpenClawRun, event.run_id)
        if run:
            run.status = str(payload.get("status") or "completed")
            run.ended_at = datetime.now(timezone.utc)
