from pathlib import Path
from typing import Any, Dict, Optional

from traceshield_method.method.config import load_yaml, resolve_config_path
from traceshield_method.method.schemas import SemanticEvent, ToolEvent


class ToolSemanticMapper:
    def __init__(self, registry_path: Optional[str | Path] = None):
        self.registry_path = resolve_config_path(registry_path, "tool_registry.yaml")
        data = load_yaml(self.registry_path)
        self.tools: Dict[str, Dict[str, Any]] = data.get("tools", {})
        self._case_index = {name.lower(): name for name in self.tools}

    def map_event(self, event: ToolEvent) -> SemanticEvent:
        tool_config = self._get_tool_config(event.tool_name)
        if tool_config is None:
            return SemanticEvent(
                step_id=event.step_id,
                tool_name=event.tool_name,
                tool_type="unknown",
                semantic_action="unknown_tool_call",
                target_resource=None,
                risk_level="high",
                raw_event=event,
            )

        resource_arg = tool_config.get("resource_arg")
        return SemanticEvent(
            step_id=event.step_id,
            tool_name=event.tool_name,
            tool_type=str(tool_config.get("tool_type", "unknown")),
            semantic_action=str(tool_config.get("semantic_action", "unknown_tool_call")),
            target_resource=self._extract_resource(event, resource_arg),
            risk_level=str(tool_config.get("risk_level", "low")),
            raw_event=event,
        )

    def _get_tool_config(self, tool_name: str) -> Optional[Dict[str, Any]]:
        if tool_name in self.tools:
            return self.tools[tool_name]
        canonical = self._case_index.get(tool_name.lower())
        if canonical:
            return self.tools[canonical]
        return None

    def _extract_resource(self, event: ToolEvent, resource_arg: Optional[str]) -> Optional[str]:
        if not resource_arg:
            return None
        value = self._get_resource_arg_value(event, resource_arg)
        if value is None:
            return None
        tool_name = event.tool_name.lower()
        if tool_name == "delete_file":
            return self._stringify_resource(
                self._get_arg_case_insensitive(event.args, "file_id")
                or self._get_arg_case_insensitive(event.args, "path")
                or value
            )
        if tool_name == "filterdb":
            database = self._get_arg_case_insensitive(event.args, "DATABASE")
            columns = self._get_arg_case_insensitive(event.args, "COLUMNS")
            if database and columns:
                resources = [str(database)]
                if isinstance(columns, list):
                    resources.extend(f"{database}.{column}" for column in columns if column)
                else:
                    resources.append(f"{database}.{columns}")
                return ";".join(resources)
        if tool_name == "getvalue":
            database = self._get_arg_case_insensitive(event.args, "DATABASE")
            column = self._get_arg_case_insensitive(event.args, "COLUMN")
            if database and column:
                return f"{database}.{column}"
            if isinstance(value, str):
                field = value.split(",", 1)[0].strip()
                if database:
                    return f"{database}.{field}"
                return field
        if tool_name == "sqlinterpreter" and isinstance(value, list):
            return ";".join(str(item) for item in value)
        return self._stringify_resource(value)

    def _get_resource_arg_value(self, event: ToolEvent, resource_arg: str) -> Any:
        value = self._get_arg_case_insensitive(event.args, resource_arg)
        if value is not None:
            return value
        aliases = {
            "read_file": ["file_path", "path", "filename", "file_id"],
            "get_file_by_id": ["file_id", "file_path", "path"],
            "delete_file": ["file_id", "file_path", "path"],
            "append_to_file": ["file_id", "filename", "file_path", "path"],
            "send_email": ["recipients", "recipient", "to"],
            "send_money": ["recipient", "iban", "account"],
            "schedule_transaction": ["recipient", "iban", "account"],
            "update_scheduled_transaction": ["id", "transaction_id", "recipient"],
        }
        for alias in aliases.get(event.tool_name.lower(), []):
            value = self._get_arg_case_insensitive(event.args, alias)
            if value is not None:
                return value
        return None

    @staticmethod
    def _stringify_resource(value: Any) -> str:
        if isinstance(value, list):
            return ";".join(str(item) for item in value)
        if isinstance(value, dict):
            return ";".join(f"{key}={item}" for key, item in value.items())
        return str(value)

    @staticmethod
    def _get_arg_case_insensitive(args: Dict[str, Any], key: str) -> Any:
        if key in args:
            return args[key]
        lower_key = key.lower()
        for arg_key, value in args.items():
            if arg_key.lower() == lower_key:
                return value
        return None
