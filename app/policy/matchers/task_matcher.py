from __future__ import annotations

from app.policy.models import MatchedRule, TaskToolRule


def match_task_rules(task_type: str, tool_id: str, rules: list[TaskToolRule]) -> list[MatchedRule]:
    matches: list[MatchedRule] = []
    normalized_task = task_type.lower()
    normalized_tool = tool_id.lower()

    for rule in rules:
        if not rule.enabled:
            continue
        if rule.task_type.lower() != normalized_task:
            continue

        denied = {item.lower() for item in rule.denied_tools}
        allowed = {item.lower() for item in rule.allowed_tools}

        if normalized_tool in denied:
            matches.append(
                MatchedRule(
                    rule_id=rule.rule_id,
                    rule_type="TaskToolRule",
                    decision="deny",
                    risk_level="high",
                    reason=rule.reason or "tool is denied for current task type",
                )
            )
            continue

        if allowed and normalized_tool not in allowed:
            matches.append(
                MatchedRule(
                    rule_id=rule.rule_id,
                    rule_type="TaskToolRule",
                    decision="warn",
                    risk_level="medium",
                    reason="tool is outside configured allow-list for this task type",
                )
            )
            continue

        matches.append(
            MatchedRule(
                rule_id=rule.rule_id,
                rule_type="TaskToolRule",
                decision="allow",
                risk_level="low",
                reason=rule.reason or "tool allowed for current task type",
            )
        )

    return matches
