from __future__ import annotations

from fnmatch import fnmatch

from app.policy.models import MatchedRule, SensitiveResourceRule, ToolResourceRule


def match_resource_rules(
    tool_id: str,
    resource_type: str,
    resource_id: str,
    tool_resource_rules: list[ToolResourceRule],
    sensitive_rules: list[SensitiveResourceRule],
) -> list[MatchedRule]:
    matches: list[MatchedRule] = []
    normalized_tool = tool_id.lower()
    normalized_resource_type = resource_type.lower()

    for rule in tool_resource_rules:
        if not rule.enabled:
            continue
        if rule.tool_id.lower() != normalized_tool:
            continue
        if rule.resource_type.lower() != normalized_resource_type:
            continue

        if any(fnmatch(resource_id, pattern) for pattern in rule.denied_patterns):
            matches.append(
                MatchedRule(
                    rule_id=rule.rule_id,
                    rule_type="ToolResourceRule",
                    decision="deny",
                    risk_level="high",
                    reason=rule.reason or "resource path matches denied pattern",
                )
            )
            continue

        if rule.allowed_patterns and not any(fnmatch(resource_id, pattern) for pattern in rule.allowed_patterns):
            matches.append(
                MatchedRule(
                    rule_id=rule.rule_id,
                    rule_type="ToolResourceRule",
                    decision="warn",
                    risk_level="medium",
                    reason="resource path is outside configured allow patterns",
                )
            )
        else:
            matches.append(
                MatchedRule(
                    rule_id=rule.rule_id,
                    rule_type="ToolResourceRule",
                    decision="allow",
                    risk_level="low",
                    reason=rule.reason or "resource access is allowed",
                )
            )

    for rule in sensitive_rules:
        if not rule.enabled:
            continue
        if rule.resource_type.lower() != normalized_resource_type:
            continue
        if not any(fnmatch(resource_id, pattern) for pattern in rule.patterns):
            continue

        matches.append(
            MatchedRule(
                rule_id=rule.rule_id,
                rule_type="SensitiveResourceRule",
                decision="warn",
                risk_level=rule.sensitivity_level,
                reason=f"sensitive resource matched labels={','.join(rule.labels)}",
            )
        )

    return matches
