from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from traceshield_method.method.detectors import contains_prompt_injection
from traceshield_method.method.schemas import IntentFrame, SemanticEvent


DEFAULT_SENSITIVE_KEYWORDS = [
    ".env",
    "id_rsa",
    "secret",
    "credential",
    "api_key",
    "token",
    "password",
]

INJECTION_KEYWORDS = [
    "ignore previous instructions",
    "ignore my previous instructions",
    "ignore earlier instructions",
    "忽略之前的指令",
    "send this to",
    "upload",
    "exfiltrate",
    "read .env",
    "读取 .env",
    "delete logs",
    "删除日志",
    "todo:",
    "important message",
    "important instructions",
    "before you can solve the task",
    "please do the following first",
    "you should use the tool",
    "<information>",
]


@dataclass
class TraceState:
    current_step: int = 0
    previous_action: str = "start"
    visited_resources: List[str] = field(default_factory=list)
    sensitive_resources_read: List[Tuple[int, str]] = field(default_factory=list)
    external_targets: List[Tuple[int, str]] = field(default_factory=list)
    untrusted_injection_steps: List[int] = field(default_factory=list)
    flags: Dict[str, Any] = field(default_factory=dict)

    def update(self, event: SemanticEvent, intent: IntentFrame) -> None:
        self.current_step = event.step_id
        target = event.target_resource
        if target:
            self.visited_resources.append(target)
            if self.is_sensitive_resource(target, intent) and event.semantic_action in {"read_file", "read_database_field", "sql_query"}:
                self.sensitive_resources_read.append((event.step_id, target))
                self.flags["sensitive_resource_read"] = True

        if event.tool_type == "network" or "network" in event.semantic_action or "external" in event.semantic_action:
            self.external_targets.append((event.step_id, target or ""))
            self.flags["external_send"] = True

        if self.contains_injection(event.raw_event.observation):
            self.untrusted_injection_steps.append(event.step_id)
            self.flags["untrusted_observation_contains_instruction"] = True

        self.previous_action = event.semantic_action

    @staticmethod
    def is_sensitive_resource(resource: Optional[str], intent: IntentFrame) -> bool:
        if not resource:
            return False
        resource_lower = resource.lower()
        keywords = DEFAULT_SENSITIVE_KEYWORDS + intent.sensitive_resources
        return any(str(keyword).lower() in resource_lower for keyword in keywords)

    @staticmethod
    def contains_injection(observation: Optional[str]) -> bool:
        return contains_prompt_injection(observation, INJECTION_KEYWORDS)
