from __future__ import annotations

from app.policy.models import MatchedRule


def _risk_rank(level: str) -> int:
    ranking = {
        "critical": 5,
        "severe": 5,
        "high": 4,
        "medium": 3,
        "low": 2,
        "none": 1,
    }
    return ranking.get((level or "none").lower(), 0)


def _decision_rank(decision: str) -> int:
    ranking = {
        "deny": 3,
        "warn": 2,
        "allow": 1,
    }
    return ranking.get((decision or "").lower(), 0)


def render_explanations(matched_rules: list[MatchedRule]) -> list[str]:
    if not matched_rules:
        return ["No policy rule matched; default allow."]

    seen: set[tuple[str, str, str]] = set()
    unique_rules: list[MatchedRule] = []
    for rule in matched_rules:
        key = (rule.rule_id, rule.decision.lower(), rule.reason.strip())
        if key in seen:
            continue
        seen.add(key)
        unique_rules.append(rule)

    ranked = sorted(
        unique_rules,
        key=lambda rule: (_decision_rank(rule.decision), _risk_rank(rule.risk_level)),
        reverse=True,
    )
    non_allow = [rule for rule in ranked if rule.decision.lower() != "allow"]
    focus = non_allow if non_allow else ranked[:1]

    return [
        (
            f"[{rule.decision.upper()}|risk={rule.risk_level}] "
            f"{rule.rule_id}: {rule.reason}"
        )
        for rule in focus
    ]
