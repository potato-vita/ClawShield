from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
import fnmatch

import yaml

from app.utils.enums import Decision


@dataclass
class BoundaryDecision:
    decision: str
    severity: str
    message: str
    rule_id: str | None = None
    tags: list[str] | None = None


class BoundaryEngine:
    def __init__(self, rules_path: str):
        self.rules_path = Path(rules_path)
        self.rules = self.load_rules()

    def load_rules(self) -> dict:
        if not self.rules_path.exists():
            return {}
        with self.rules_path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def workspace_root(self) -> str:
        workspace = self.rules.get("workspace", {})
        return workspace.get("root", "app/data/sample_workspace")

    @property
    def sensitive_patterns(self) -> list[str]:
        workspace = self.rules.get("workspace", {})
        return workspace.get("sensitive_patterns", [])

    def check_file_access(self, path: str, action: str) -> BoundaryDecision:
        workspace = self.rules.get("workspace", {})
        blocked_paths = workspace.get("blocked_paths", [])
        deny_outside = workspace.get("deny_outside", True)
        root = Path(self.workspace_root).expanduser().resolve()
        target = Path(path).expanduser()
        resolved = target.resolve() if target.is_absolute() else (root / target).resolve()

        for blocked in blocked_paths:
            blocked_resolved = Path(blocked).expanduser().resolve()
            if str(resolved).startswith(str(blocked_resolved)):
                return BoundaryDecision(
                    decision=Decision.BLOCK.value,
                    severity="high",
                    message=f"Path blocked by policy: {resolved}",
                    rule_id="R1",
                    tags=["workspace_escape"],
                )

        is_within = False
        try:
            resolved.relative_to(root)
            is_within = True
        except ValueError:
            is_within = False

        if deny_outside and not is_within:
            return BoundaryDecision(
                decision=Decision.BLOCK.value,
                severity="high",
                message=f"Path is outside workspace: {resolved}",
                rule_id="R1",
                tags=["workspace_escape"],
            )

        rel = str(resolved.name)
        for pattern in self.sensitive_patterns:
            rel_path = str(resolved)
            if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(rel_path, pattern):
                return BoundaryDecision(
                    decision=Decision.ALERT.value,
                    severity="medium",
                    message=f"Sensitive file access detected: {resolved}",
                    rule_id="R2",
                    tags=["sensitive"],
                )

        return BoundaryDecision(decision=Decision.ALLOW.value, severity="low", message=f"{action} allowed")

    def check_tool_invocation(self, tool_id: str) -> BoundaryDecision:
        capability = self.rules.get("capability", {})
        allowed_tools = capability.get("allowed_tools", [])
        if tool_id not in allowed_tools:
            return BoundaryDecision(
                decision=Decision.BLOCK.value,
                severity="high",
                message=f"Tool not in whitelist: {tool_id}",
                rule_id="R3",
                tags=["unauthorized_tool"],
            )
        return BoundaryDecision(decision=Decision.ALLOW.value, severity="low", message="Tool allowed")

    def check_http_request(self, url: str) -> BoundaryDecision:
        capability = self.rules.get("capability", {})
        if not capability.get("allow_network", True):
            return BoundaryDecision(
                decision=Decision.BLOCK.value,
                severity="high",
                message="Network disabled by policy",
                rule_id="R4",
                tags=["network_denied"],
            )
        domain = urlparse(url).netloc
        allowed_domains = capability.get("allowed_domains", [])
        if domain not in allowed_domains:
            return BoundaryDecision(
                decision=Decision.BLOCK.value,
                severity="high",
                message=f"Domain not in whitelist: {domain}",
                rule_id="R4",
                tags=["domain_not_allowed"],
            )
        return BoundaryDecision(decision=Decision.ALLOW.value, severity="low", message="HTTP request allowed")

    def check_command_execution(self, command: str) -> BoundaryDecision:
        capability = self.rules.get("capability", {})
        blocked_commands = capability.get("blocked_commands", [])
        for blocked in blocked_commands:
            if blocked in command:
                return BoundaryDecision(
                    decision=Decision.BLOCK.value,
                    severity="critical",
                    message=f"Blocked command pattern detected: {blocked}",
                    rule_id="R6",
                    tags=["dangerous_command"],
                )
        return BoundaryDecision(decision=Decision.ALLOW.value, severity="low", message="Command allowed")

    def check_env_read(self, key: str) -> BoundaryDecision:
        sensitive_keys = {"OPENAI_API_KEY", "AWS_SECRET_ACCESS_KEY", "SECRET_KEY", "TOKEN"}
        upper = key.upper()
        if upper in sensitive_keys or "SECRET" in upper or "TOKEN" in upper:
            return BoundaryDecision(
                decision=Decision.BLOCK.value,
                severity="high",
                message=f"Sensitive env read blocked: {key}",
                rule_id="R5",
                tags=["sensitive_env"],
            )
        return BoundaryDecision(decision=Decision.ALLOW.value, severity="low", message="Env read allowed")

    def check_trust(self, skill_source: str | None, tool_id: str | None = None) -> BoundaryDecision:
        trust = self.rules.get("trust", {})
        allowed_sources = trust.get("allowed_skill_sources", [])
        default_skill_trust = trust.get("default_skill_trust", "unknown")
        tool_trust_map = trust.get("tool_trust", {})

        source = skill_source or default_skill_trust
        if source not in allowed_sources:
            return BoundaryDecision(
                decision=Decision.ALERT.value,
                severity="medium",
                message=f"Skill source not trusted: {source}",
                rule_id="R11",
                tags=["untrusted_skill"],
            )

        if tool_id:
            tool_trust = tool_trust_map.get(tool_id, "unknown")
            if tool_trust == "risky":
                return BoundaryDecision(
                    decision=Decision.ALERT.value,
                    severity="high",
                    message=f"Risky tool used: {tool_id}",
                    rule_id="R11",
                    tags=["risky_tool"],
                )

        return BoundaryDecision(decision=Decision.ALLOW.value, severity="low", message="Trust boundary passed")


class ResourceBoundaryChecker:
    def __init__(self, engine: BoundaryEngine):
        self.engine = engine

    def check_file_access(self, path: str, action: str) -> BoundaryDecision:
        return self.engine.check_file_access(path=path, action=action)


class CapabilityBoundaryChecker:
    def __init__(self, engine: BoundaryEngine):
        self.engine = engine

    def check_tool_invocation(self, tool_id: str) -> BoundaryDecision:
        return self.engine.check_tool_invocation(tool_id=tool_id)

    def check_http_request(self, url: str) -> BoundaryDecision:
        return self.engine.check_http_request(url=url)

    def check_command_execution(self, command: str) -> BoundaryDecision:
        return self.engine.check_command_execution(command=command)

    def check_env_read(self, key: str) -> BoundaryDecision:
        return self.engine.check_env_read(key=key)


class TrustBoundaryChecker:
    def __init__(self, engine: BoundaryEngine):
        self.engine = engine

    def check_trust(self, skill_source: str | None, tool_id: str | None = None) -> BoundaryDecision:
        return self.engine.check_trust(skill_source=skill_source, tool_id=tool_id)
