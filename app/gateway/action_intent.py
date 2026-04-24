from __future__ import annotations

import re
from typing import Any

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

    if structured_url:
        normalized_arguments.setdefault("url", structured_url)
        return "http", normalized_arguments

    if structured_env_key:
        normalized_arguments.setdefault("env_key", structured_env_key.upper())
        return "env_read", normalized_arguments

    if structured_file:
        normalized_arguments.setdefault("file_path", structured_file)
        return "file_read", normalized_arguments

    if inferred_url and (tool_lower.startswith("http") or _is_network_command(command_text)):
        normalized_arguments.setdefault("url", inferred_url)
        return "http", normalized_arguments

    if inferred_env_key:
        normalized_arguments.setdefault("env_key", inferred_env_key)
        return "env_read", normalized_arguments

    if inferred_file:
        normalized_arguments.setdefault("file_path", inferred_file)
        return "file_read", normalized_arguments

    if "http" in tool_lower:
        return "http", normalized_arguments
    if "env" in tool_lower:
        return "env_read", normalized_arguments
    if "file" in tool_lower:
        return "file_read", normalized_arguments

    if inferred_url:
        normalized_arguments.setdefault("url", inferred_url)
        return "http", normalized_arguments

    return "tool_call", normalized_arguments
