from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter

from app.schemas.common import APIResponse, success_response

router = APIRouter(prefix="/rules")


def _count_rules(path: Path) -> int:
    if not path.exists():
        return 0

    with path.open("r", encoding="utf-8") as handle:
        loaded: dict[str, Any] | None = yaml.safe_load(handle)

    if not loaded or not isinstance(loaded, dict):
        return 0

    rules = loaded.get("rules", [])
    if isinstance(rules, list):
        return len(rules)
    return 0


@router.get("/summary", response_model=APIResponse)
def get_rules_summary() -> APIResponse:
    base = Path("configs/rules")
    return success_response(
        data={
            "task_tool_rule_count": _count_rules(base / "task_tool_map.yaml"),
            "tool_resource_rule_count": _count_rules(base / "tool_resource_map.yaml"),
            "sensitive_resource_count": _count_rules(base / "sensitive_resources.yaml"),
            "risk_chain_rule_count": _count_rules(base / "risk_chains.yaml"),
            "version": "v1",
        }
    )
