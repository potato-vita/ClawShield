from __future__ import annotations

import re
from typing import Any

from app.schemas.intent import ToolCallIntent
from app.schemas.tool_call import ActionType

# Match URLs in shell commands and markdown-like snippets.
_URL_PATTERN = re.compile(r"https?://[^\s'\"`<>]+", re.IGNORECASE)
# Match shell-style environment variable references like $OPENAI_API_KEY or ${OPENAI_API_KEY}.
_ENV_KEY_PATTERN = re.compile(r"\$\{?([A-Z][A-Z0-9_]{2,})\}?", re.IGNORECASE)
# Match simple file-read commands. This is intentionally narrow to avoid over-classification.
_FILE_READ_PATTERN = re.compile(
    r"\b(?:cat|less|more|head|tail|sed|awk)\b(?:\s+-[^\s]+)*\s+([^\s]+)",
    re.IGNORECASE,
)
_HTTP_METHOD_FLAG_PATTERN = re.compile(r"(?:-X|--request)\s+([A-Za-z]+)")
_HTTP_PAYLOAD_FLAG_PATTERN = re.compile(r"\s(?:-d|--data|--data-raw|--data-binary|-F|--form|-T|--upload-file)\b")


def _pick_str(arguments: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = arguments.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_command_text(arguments: dict[str, Any]) -> str | None:
    return _pick_str(
        arguments,
        (
            "command",
            "cmd",
            "shell_command",
            "script",
            "code",
            "statement",
            "input",
            "text",
        ),
    )


def _extract_url_from_text(command_text: str) -> str | None:
    match = _URL_PATTERN.search(command_text)
    if match is None:
        return None
    return match.group(0)


def _extract_env_key_from_text(command_text: str) -> str | None:
    match = _ENV_KEY_PATTERN.search(command_text)
    if match is None:
        return None
    return match.group(1).upper()


def _extract_file_from_text(command_text: str) -> str | None:
    match = _FILE_READ_PATTERN.search(command_text)
    if match is None:
        return None
    return match.group(1).strip()


def _is_network_command(command_text: str) -> bool:
    lowered = command_text.lower()
    return any(
        token in lowered
        for token in (
            "curl ",
            "wget ",
            "http ",
            "fetch(",
            "invoke-webrequest",
            "requests.",
        )
    )


def _extract_http_method(arguments: dict[str, Any], command_text: str) -> str | None:
    value = _pick_str(arguments, ("method", "http_method", "verb"))
    if value:
        return value.upper()

    if not command_text:
        return None

    match = _HTTP_METHOD_FLAG_PATTERN.search(command_text)
    if match is not None:
        return match.group(1).upper()

    lowered = command_text.lower()
    if "wget " in lowered:
        return "GET"
    if "curl " in lowered:
        return "GET"
    return None


def _detect_http_payload(arguments: dict[str, Any], command_text: str) -> bool:
    payload_keys = ("body", "data", "payload", "content", "json", "form", "files")
    if any(arguments.get(key) not in (None, "", {}, []) for key in payload_keys):
        return True
    if not command_text:
        return False
    return _HTTP_PAYLOAD_FLAG_PATTERN.search(command_text) is not None


def infer_action_intent(tool_id: str, arguments: dict[str, Any]) -> tuple[ActionType, dict[str, Any]]:
    """
    Infer canonical action type and normalized arguments from a raw tool call payload.

    The returned arguments keep original fields and may include inferred keys
    (`url`, `env_key`, `file_path`) so downstream interceptors can stay simple.
    """
    normalized_arguments = dict(arguments)
    tool_lower = (tool_id or "").lower()

    structured_url = _pick_str(normalized_arguments, ("url", "target_url", "uri", "endpoint"))
    structured_env_key = _pick_str(normalized_arguments, ("env_key", "env_name", "env_var"))
    structured_file = _pick_str(normalized_arguments, ("file_path", "path", "target_file", "filepath"))

    command_text = _extract_command_text(normalized_arguments) or ""
    inferred_url = _extract_url_from_text(command_text) if command_text else None
    inferred_env_key = _extract_env_key_from_text(command_text) if command_text else None
    inferred_file = _extract_file_from_text(command_text) if command_text else None
    inferred_http_method = _extract_http_method(normalized_arguments, command_text)
    has_http_payload = _detect_http_payload(normalized_arguments, command_text)

    if structured_url:
        normalized_arguments.setdefault("url", structured_url)
        if inferred_http_method:
            normalized_arguments.setdefault("http_method", inferred_http_method)
        if has_http_payload:
            normalized_arguments.setdefault("payload_present", True)
        return "http", normalized_arguments

    if structured_env_key:
        normalized_arguments.setdefault("env_key", structured_env_key.upper())
        return "env_read", normalized_arguments

    if structured_file:
        normalized_arguments.setdefault("file_path", structured_file)
        return "file_read", normalized_arguments

    if inferred_url and (tool_lower.startswith("http") or _is_network_command(command_text)):
        normalized_arguments.setdefault("url", inferred_url)
        if inferred_http_method:
            normalized_arguments.setdefault("http_method", inferred_http_method)
        if has_http_payload:
            normalized_arguments.setdefault("payload_present", True)
        return "http", normalized_arguments

    if inferred_env_key:
        normalized_arguments.setdefault("env_key", inferred_env_key)
        return "env_read", normalized_arguments

    if inferred_file:
        normalized_arguments.setdefault("file_path", inferred_file)
        return "file_read", normalized_arguments

    if "http" in tool_lower:
        if inferred_http_method:
            normalized_arguments.setdefault("http_method", inferred_http_method)
        if has_http_payload:
            normalized_arguments.setdefault("payload_present", True)
        return "http", normalized_arguments
    if "env" in tool_lower:
        return "env_read", normalized_arguments
    if "file" in tool_lower:
        return "file_read", normalized_arguments

    if inferred_url:
        normalized_arguments.setdefault("url", inferred_url)
        if inferred_http_method:
            normalized_arguments.setdefault("http_method", inferred_http_method)
        if has_http_payload:
            normalized_arguments.setdefault("payload_present", True)
        return "http", normalized_arguments

    return "tool_call", normalized_arguments


def infer_tool_call_intent(
    run_id: str,
    tool_call_id: str,
    tool_id: str,
    arguments: dict[str, Any],
    step_id: str | None = None,
    model_reason: str | None = None,
) -> ToolCallIntent:
    action_type, normalized_arguments = infer_action_intent(tool_id=tool_id, arguments=arguments)

    target_resource_type = "tool"
    target_resource_id = tool_id
    operation = "execute"
    intended_effect = "tool_execute"
    data_direction = "internal"
    confidence = 0.7
    inferred_purpose = "general_tool_usage"

    if action_type == "file_read":
        target_resource_type = "file"
        target_resource_id = str(
            normalized_arguments.get("file_path")
            or normalized_arguments.get("path")
            or normalized_arguments.get("target_file")
            or "unknown_file"
        )
        operation = "read"
        intended_effect = "read"
        data_direction = "inbound"
        confidence = 0.9
        inferred_purpose = "read_file_context"
    elif action_type == "http":
        target_resource_type = "http"
        target_resource_id = str(
            normalized_arguments.get("url")
            or normalized_arguments.get("target_url")
            or normalized_arguments.get("endpoint")
            or "unknown_url"
        )
        operation = "request"
        intended_effect = "http_request"
        data_direction = "outbound"
        confidence = 0.88
        inferred_purpose = "external_request"
    elif action_type == "env_read":
        target_resource_type = "env"
        target_resource_id = str(
            normalized_arguments.get("env_key")
            or normalized_arguments.get("env_var")
            or normalized_arguments.get("env_name")
            or "unknown_env_key"
        )
        operation = "read"
        intended_effect = "env_read"
        data_direction = "inbound"
        confidence = 0.9
        inferred_purpose = "read_runtime_env"

    return ToolCallIntent(
        run_id=run_id,
        tool_call_id=tool_call_id,
        tool_id=tool_id,
        step_id=step_id,
        action_type=action_type,
        operation=operation,
        inferred_purpose=inferred_purpose,
        target_resource_type=target_resource_type,
        target_resource_id=target_resource_id,
        intended_effect=intended_effect,
        data_direction=data_direction,
        model_reason=model_reason,
        confidence=confidence,
    )
