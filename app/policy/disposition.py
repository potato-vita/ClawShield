from __future__ import annotations


def decision_to_disposition(decision: str) -> str:
    mapping = {
        "allow": "allow",
        "warn": "warn",
        "deny": "deny",
        "degrade": "degrade",
    }
    return mapping.get(decision, "warn")


def decision_risk_level(decision: str) -> str:
    mapping = {
        "allow": "low",
        "warn": "medium",
        "deny": "high",
        "degrade": "medium",
    }
    return mapping.get(decision, "medium")
