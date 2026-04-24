from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, NotFoundError
from app.repositories.run_repo import run_repository
from app.schemas.task import TaskIngestRequest
from app.schemas.tool_call import ToolCallRequest, ToolResultPayload
from app.services.audit_service import AuditService, audit_service
from app.services.bridge_service import BridgeService, bridge_service
from app.services.task_service import TaskService, task_service


def _pick_first(mapping: dict[str, Any], keys: tuple[str, ...]) -> Any | None:
    for key in keys:
        value = mapping.get(key)
        if value is not None and value != "":
            return value
    return None


class OpenClawCallbackService:
    """Adapt external OpenClaw callback payloads into ClawShield bridge contracts."""

    def __init__(
        self,
        task_service_instance: TaskService,
        bridge_service_instance: BridgeService,
        audit_service_instance: AuditService,
    ) -> None:
        self._task_service = task_service_instance
        self._bridge_service = bridge_service_instance
        self._audit_service = audit_service_instance

    @staticmethod
    def _normalize_arguments(raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                return {"raw_text": raw}
            if isinstance(parsed, dict):
                return parsed
            return {"raw_value": parsed}
        if raw is None:
            return {}
        return {"raw_value": raw}

    @staticmethod
    def _extract_user_input(payload: dict[str, Any]) -> str:
        user_input = _pick_first(payload, ("user_input", "prompt", "input", "task", "query"))
        if isinstance(user_input, str) and user_input.strip():
            return user_input.strip()

        message = payload.get("message")
        if isinstance(message, dict):
            content = _pick_first(message, ("content", "text", "input"))
            if isinstance(content, str) and content.strip():
                return content.strip()

        if isinstance(message, str) and message.strip():
            return message.strip()

        messages = payload.get("messages")
        if isinstance(messages, list):
            for item in messages:
                if isinstance(item, str) and item.strip():
                    return item.strip()
                if isinstance(item, dict):
                    content = _pick_first(item, ("content", "text", "input", "message"))
                    if isinstance(content, str) and content.strip():
                        return content.strip()

        return "OpenClaw external session task"

    @staticmethod
    def _extract_session_id(payload: dict[str, Any]) -> str | None:
        value = _pick_first(payload, ("session_id", "sessionId", "conversation_id", "conversationId"))
        return str(value) if value else None

    @staticmethod
    def _extract_run_id(payload: dict[str, Any]) -> str | None:
        value = _pick_first(payload, ("run_id", "runId"))
        return str(value) if value else None

    def _resolve_or_create_run_id(
        self,
        db: Session,
        payload: dict[str, Any],
        allow_create: bool,
    ) -> tuple[str, str | None]:
        run_id = self._extract_run_id(payload)
        if run_id:
            run = run_repository.get_by_run_id(db=db, run_id=run_id)
            if run is None:
                raise NotFoundError(
                    message="run not found",
                    details={"run_id": run_id},
                    error_code="RUN_NOT_FOUND",
                )
            return run.run_id, run.session_id

        session_id = self._extract_session_id(payload)
        if not session_id:
            raise BadRequestError(
                message="session_id or run_id is required",
                error_code="MISSING_RUN_CONTEXT",
                details={"required_any_of": ["run_id", "session_id"]},
            )

        latest_run = run_repository.get_latest_by_session_id(db=db, session_id=session_id)
        if latest_run is not None:
            return latest_run.run_id, session_id

        if not allow_create:
            raise NotFoundError(
                message="run not found for session",
                error_code="RUN_NOT_FOUND_FOR_SESSION",
                details={"session_id": session_id},
            )

        created = self._task_service.ingest_task(
            db=db,
            payload=TaskIngestRequest(
                session_id=session_id,
                user_input=self._extract_user_input(payload),
                source="opencaw-callback",
                metadata={"external_bridge": True},
            ),
        )
        return created.run_id, session_id

    @staticmethod
    def _collect_tool_call_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        if isinstance(payload.get("tool_calls"), list):
            return [item for item in payload["tool_calls"] if isinstance(item, dict)]
        if isinstance(payload.get("calls"), list):
            return [item for item in payload["calls"] if isinstance(item, dict)]
        if isinstance(payload.get("tool_call"), dict):
            return [payload["tool_call"]]

        message = payload.get("message")
        if isinstance(message, dict) and isinstance(message.get("tool_calls"), list):
            return [item for item in message["tool_calls"] if isinstance(item, dict)]

        if any(key in payload for key in ("tool_id", "tool", "name", "function")):
            return [payload]
        return []

    @staticmethod
    def _collect_tool_result_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        if isinstance(payload.get("tool_results"), list):
            return [item for item in payload["tool_results"] if isinstance(item, dict)]
        if isinstance(payload.get("results"), list):
            return [item for item in payload["results"] if isinstance(item, dict)]
        if isinstance(payload.get("tool_result"), dict):
            return [payload["tool_result"]]
        return [payload]

    @staticmethod
    def _collect_message_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []

        messages = payload.get("messages")
        if isinstance(messages, list):
            for item in messages:
                if isinstance(item, dict):
                    items.append(item)
                elif isinstance(item, str):
                    items.append({"content": item})
            if items:
                return items

        message = payload.get("message")
        if isinstance(message, dict):
            return [message]
        if isinstance(message, str):
            return [{"content": message, "role": payload.get("role")}]

        if any(key in payload for key in ("content", "text", "input", "message_text")):
            return [payload]
        return []

    @staticmethod
    def _extract_message_text(item: dict[str, Any]) -> str:
        content = _pick_first(item, ("content", "text", "input", "message", "message_text"))
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, dict):
            text = _pick_first(content, ("text", "content", "value"))
            if isinstance(text, str):
                return text.strip()
        if isinstance(content, list):
            pieces: list[str] = []
            for part in content:
                if isinstance(part, str) and part.strip():
                    pieces.append(part.strip())
                    continue
                if isinstance(part, dict):
                    text = _pick_first(part, ("text", "content", "value"))
                    if isinstance(text, str) and text.strip():
                        pieces.append(text.strip())
            return " ".join(pieces).strip()
        return ""

    @staticmethod
    def _role_to_actor_type(role: str) -> str:
        normalized = role.lower()
        if normalized in {"assistant", "model", "ai"}:
            return "model"
        if normalized in {"user", "human"}:
            return "user"
        return "system"

    def _parse_message_item(
        self,
        item: dict[str, Any],
        payload: dict[str, Any],
        fallback_idx: int,
    ) -> tuple[str, str, str]:
        role_value = _pick_first(item, ("role", "speaker", "actor"))
        if role_value is None:
            role_value = _pick_first(payload, ("role", "speaker", "actor"))
        role = str(role_value).strip() if role_value else "user"

        content = self._extract_message_text(item)
        if not content:
            raise BadRequestError(
                message="message content is required in callback payload",
                error_code="MESSAGE_PAYLOAD_INVALID",
                details={"missing": f"content[{fallback_idx}]"},
            )

        actor_type = self._role_to_actor_type(role)
        return role, actor_type, content

    @staticmethod
    def _parse_tool_call_item(item: dict[str, Any], fallback_idx: int) -> tuple[str, str, dict[str, Any], str | None]:
        function_obj = item.get("function")
        function = function_obj if isinstance(function_obj, dict) else {}

        tool_call_id = _pick_first(item, ("tool_call_id", "toolCallId", "call_id", "id"))
        if tool_call_id is None:
            tool_call_id = f"oc_call_{uuid4().hex[:10]}_{fallback_idx}"

        tool_id = _pick_first(item, ("tool_id", "tool", "tool_name", "name"))
        if tool_id is None:
            tool_id = _pick_first(function, ("name",))
        if tool_id is None:
            raise BadRequestError(
                message="tool_id is required in callback payload",
                error_code="TOOL_CALL_PAYLOAD_INVALID",
                details={"missing": "tool_id"},
            )

        raw_arguments = _pick_first(item, ("arguments", "args", "input"))
        if raw_arguments is None:
            raw_arguments = _pick_first(function, ("arguments",))

        model_reason_value = _pick_first(item, ("model_reason", "reason", "justification"))
        model_reason = str(model_reason_value) if model_reason_value is not None else None
        return str(tool_call_id), str(tool_id), OpenClawCallbackService._normalize_arguments(raw_arguments), model_reason

    @staticmethod
    def _parse_tool_result_item(item: dict[str, Any], fallback_idx: int) -> tuple[str, str, str, str | None, dict[str, Any]]:
        function_obj = item.get("function")
        function = function_obj if isinstance(function_obj, dict) else {}

        tool_call_id = _pick_first(item, ("tool_call_id", "toolCallId", "call_id", "id"))
        if tool_call_id is None:
            tool_call_id = f"oc_result_{uuid4().hex[:10]}_{fallback_idx}"

        tool_id = _pick_first(item, ("tool_id", "tool", "tool_name", "name"))
        if tool_id is None:
            tool_id = _pick_first(function, ("name",))
        if tool_id is None:
            raise BadRequestError(
                message="tool_id is required in callback result payload",
                error_code="TOOL_RESULT_PAYLOAD_INVALID",
                details={"missing": "tool_id"},
            )

        status_value = _pick_first(item, ("execution_status", "status"))
        execution_status = str(status_value) if status_value is not None else "unknown"

        result_summary_value = _pick_first(item, ("result_summary", "output_summary", "summary", "content"))
        result_summary = str(result_summary_value) if result_summary_value is not None else None

        raw_result = _pick_first(item, ("raw_result", "result", "output"))
        normalized_raw = raw_result if isinstance(raw_result, dict) else {"raw_value": raw_result}
        return str(tool_call_id), str(tool_id), execution_status, result_summary, normalized_raw

    def bootstrap_session(self, db: Session, session_id: str, user_input: str) -> dict[str, str]:
        latest_run = run_repository.get_latest_by_session_id(db=db, session_id=session_id)
        if latest_run is not None:
            return {"run_id": latest_run.run_id, "session_id": session_id}

        created = self._task_service.ingest_task(
            db=db,
            payload=TaskIngestRequest(
                session_id=session_id,
                user_input=user_input,
                source="opencaw-callback",
                metadata={"external_bridge": True, "bootstrap": True},
            ),
        )
        return {"run_id": created.run_id, "session_id": session_id}

    def process_tool_call_callback(self, db: Session, payload: dict[str, Any]) -> dict[str, Any]:
        run_id, session_id = self._resolve_or_create_run_id(db=db, payload=payload, allow_create=True)
        items = self._collect_tool_call_items(payload)
        if not items:
            raise BadRequestError(
                message="tool call payload is empty",
                error_code="TOOL_CALL_PAYLOAD_INVALID",
                details={"expected_any_of": ["tool_calls", "tool_call", "tool_id"]},
            )

        results: list[dict[str, Any]] = []
        for index, item in enumerate(items, start=1):
            tool_call_id, tool_id, arguments, model_reason = self._parse_tool_call_item(item=item, fallback_idx=index)
            decision = self._bridge_service.process_tool_call(
                db=db,
                payload=ToolCallRequest(
                    run_id=run_id,
                    tool_call_id=tool_call_id,
                    tool_id=tool_id,
                    arguments=arguments,
                    model_reason=model_reason,
                ),
            )
            results.append(decision)

        return {
            "run_id": run_id,
            "session_id": session_id,
            "processed_count": len(results),
            "results": results,
        }

    def process_tool_result_callback(self, db: Session, payload: dict[str, Any]) -> dict[str, Any]:
        run_id, session_id = self._resolve_or_create_run_id(db=db, payload=payload, allow_create=False)
        items = self._collect_tool_result_items(payload)
        if not items:
            raise BadRequestError(
                message="tool result payload is empty",
                error_code="TOOL_RESULT_PAYLOAD_INVALID",
                details={"expected_any_of": ["tool_results", "tool_result"]},
            )

        results: list[dict[str, Any]] = []
        for index, item in enumerate(items, start=1):
            tool_call_id, tool_id, execution_status, result_summary, raw_result = self._parse_tool_result_item(
                item=item,
                fallback_idx=index,
            )
            result = self._bridge_service.process_tool_result(
                db=db,
                payload=ToolResultPayload(
                    run_id=run_id,
                    tool_call_id=tool_call_id,
                    tool_id=tool_id,
                    execution_status=execution_status,
                    result_summary=result_summary,
                    raw_result=raw_result,
                ),
            )
            results.append(result)

        return {
            "run_id": run_id,
            "session_id": session_id,
            "processed_count": len(results),
            "results": results,
        }

    def process_message_callback(self, db: Session, payload: dict[str, Any]) -> dict[str, Any]:
        run_id, session_id = self._resolve_or_create_run_id(db=db, payload=payload, allow_create=True)
        items = self._collect_message_items(payload)
        if not items:
            raise BadRequestError(
                message="message payload is empty",
                error_code="MESSAGE_PAYLOAD_INVALID",
                details={"expected_any_of": ["message", "messages", "content"]},
            )

        results: list[dict[str, Any]] = []
        for index, item in enumerate(items, start=1):
            role, actor_type, content = self._parse_message_item(item=item, payload=payload, fallback_idx=index)

            event = self._audit_service.record_event(
                db=db,
                run_id=run_id,
                session_id=session_id,
                event_type="chat_message_received",
                event_stage="conversation",
                actor_type=actor_type,
                input_summary=content if actor_type == "user" else None,
                output_summary=content if actor_type in {"model", "system"} else None,
                status="recorded",
            )
            results.append(
                {
                    "event_id": event.event_id,
                    "role": role,
                    "actor_type": actor_type,
                    "event_type": "chat_message_received",
                    "content_preview": content[:200],
                }
            )

        return {
            "run_id": run_id,
            "session_id": session_id,
            "processed_count": len(results),
            "results": results,
        }


opencaw_callback_service = OpenClawCallbackService(
    task_service_instance=task_service,
    bridge_service_instance=bridge_service,
    audit_service_instance=audit_service,
)
