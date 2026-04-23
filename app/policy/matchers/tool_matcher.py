from __future__ import annotations

import re

from app.policy.models import MatchedRule

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_DESTRUCTIVE_TOKENS = {"delete", "drop", "truncate", "rm", "danger"}
_EXTERNAL_TOKENS = {"plugin", "http", "https", "remote", "webhook"}


def _tool_tokens(tool_id: str) -> set[str]:
    return set(_TOKEN_PATTERN.findall(tool_id.lower()))


def match_tool_rules(tool_id: str) -> list[MatchedRule]:
    matches: list[MatchedRule] = []
    tokens = _tool_tokens(tool_id)

    # Token-level matching avoids false positives from partial substrings.
    # Example: "dropdown_formatter" should not be treated as destructive.
    if tokens & _DESTRUCTIVE_TOKENS:
        matches.append(
            MatchedRule(
                rule_id="tool-keyword-destructive",
                rule_type="ToolKeywordRule",
                decision="deny",
                risk_level="high",
                reason="destructive tool keyword detected",
            )
        )
    elif tokens & _EXTERNAL_TOKENS:
        matches.append(
            MatchedRule(
                rule_id="tool-keyword-external",
                rule_type="ToolKeywordRule",
                decision="warn",
                risk_level="medium",
                reason="external interaction tool keyword detected",
            )
        )

    return matches
