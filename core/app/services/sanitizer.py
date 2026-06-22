import hashlib
import json
import re
from typing import Any

SECRET_PATTERNS = [
    re.compile(r"(?i)(password|passwd|token|api[_-]?key|secret)\s*[:=]\s*([^\s,;]+)"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
]


def redact_text(value: Any, limit: int = 500) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    for pattern in SECRET_PATTERNS:
        text = pattern.sub(lambda match: f"{match.group(1)}=[REDACTED]" if match.lastindex == 2 else "[REDACTED_PRIVATE_KEY]", text)
    return text[:limit]


def sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if re.search(r"(?i)password|token|secret|api[_-]?key|cookie", key) else sanitize_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_value(item) for item in value[:100]]
    if isinstance(value, str):
        return redact_text(value)
    return value


def stable_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def json_text(value: Any) -> str:
    return json.dumps(sanitize_value(value), ensure_ascii=False, sort_keys=True, default=str)
