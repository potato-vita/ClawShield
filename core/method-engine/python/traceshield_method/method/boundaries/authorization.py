from typing import Any, List

from traceshield_method.method.schemas import IntentFrame, SemanticEvent


def is_authorized_risky_call(intent: IntentFrame, event: SemanticEvent) -> bool:
    authorized_calls = intent.constraints.get("authorized_risky_calls")
    if not isinstance(authorized_calls, list):
        return False
    current = {
        "tool_name": event.tool_name,
        "semantic_action": event.semantic_action,
        "args": canonical_args(event.raw_event.args),
    }
    return any(authorized_call_matches(current, call) for call in authorized_calls if isinstance(call, dict))


def authorized_call_matches(current: dict, authorized: dict) -> bool:
    if current.get("tool_name") != authorized.get("tool_name"):
        return False
    if not semantic_action_matches(str(current.get("semantic_action") or ""), str(authorized.get("semantic_action") or "")):
        return False
    current_args = current.get("args") or {}
    authorized_args = canonical_args(authorized.get("args") or {})
    critical_keys = critical_arg_keys(
        str(current.get("tool_name") or ""),
        str(current.get("semantic_action") or ""),
        current_args=current_args,
        authorized_args=authorized_args,
    )
    if not critical_keys:
        return current_args == authorized_args
    return all(arg_value_matches(current_args.get(key), authorized_args.get(key)) for key in critical_keys)


def semantic_action_matches(current: str, authorized: str) -> bool:
    if current == authorized:
        return True
    action_aliases = {
        "external_send": {"send_email", "network_post", "web_submit", "external_send"},
    }
    return current in action_aliases.get(authorized, set())


def critical_arg_keys(
    tool_name: str,
    semantic_action: str,
    current_args: dict | None = None,
    authorized_args: dict | None = None,
) -> List[str]:
    tool_key = tool_name.lower()
    if tool_key in {"send_money", "schedule_transaction"}:
        return ["recipient", "amount"]
    if tool_key == "update_scheduled_transaction":
        return _present_critical_keys(
            ["id", "recipient", "amount", "date", "recurring"],
            current_args or {},
            authorized_args or {},
            fallback=["id"],
        )
    if tool_key == "send_email":
        return ["recipients", "subject"]
    if tool_key == "send_channel_message":
        return ["channel"]
    if tool_key == "send_direct_message":
        return ["recipient"]
    if tool_key == "reserve_hotel":
        return ["hotel"]
    if tool_key == "reserve_restaurant":
        return ["restaurant"]
    if tool_key == "reserve_car_rental":
        return ["company"]
    if tool_key == "share_file":
        return ["file_id"]
    if tool_key in {"post_webpage", "web_submit"}:
        return _present_critical_keys(["url", "target"], current_args or {}, authorized_args or {}, fallback=["target"])
    if semantic_action in {"create_calendar_event", "modify_calendar_event"}:
        return ["title"]
    return []


def _present_critical_keys(keys: List[str], current_args: dict, authorized_args: dict, fallback: List[str]) -> List[str]:
    selected = []
    for key in keys:
        if key in fallback or (key in current_args and key in authorized_args):
            selected.append(key)
    return selected or fallback


def arg_value_matches(current: Any, authorized: Any) -> bool:
    if isinstance(current, (int, float)) and isinstance(authorized, (int, float)):
        return abs(float(current) - float(authorized)) <= 1e-6
    return current == authorized


def canonical_args(args: dict) -> dict:
    return {str(key): canonical_value(value) for key, value in sorted((args or {}).items())}


def canonical_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): canonical_value(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [canonical_value(item) for item in value]
    if isinstance(value, float):
        return round(value, 6)
    return value
