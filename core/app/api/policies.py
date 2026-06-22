import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Policy
from app.db.session import get_db
from app.services.idgen import new_id

router = APIRouter(prefix="/api/module4/policies", tags=["policies"])


class PolicyCreate(BaseModel):
    name: str
    description: str | None = None
    target: str = "tool_call"
    condition: dict[str, Any]
    action: str = Field(pattern="^(ALLOW|WARN|ASK|BLOCK)$")
    enabled: bool = True
    priority: int = 100


class PolicyPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    condition: dict[str, Any] | None = None
    action: str | None = Field(default=None, pattern="^(ALLOW|WARN|ASK|BLOCK)$")
    enabled: bool | None = None
    priority: int | None = None


@router.get("")
def list_policies(db: Session = Depends(get_db)) -> list[dict]:
    policies = db.scalars(select(Policy).order_by(Policy.priority.desc())).all()
    return [_serialize(item) for item in policies]


@router.post("")
def create_policy(request: PolicyCreate, db: Session = Depends(get_db)) -> dict:
    policy = Policy(
        id=new_id("policy"), name=request.name, description=request.description, target=request.target,
        condition_json=json.dumps(request.condition, ensure_ascii=False), action=request.action,
        enabled=request.enabled, priority=request.priority,
    )
    db.add(policy)
    db.commit()
    return _serialize(policy)


@router.patch("/{policy_id}")
def update_policy(policy_id: str, request: PolicyPatch, db: Session = Depends(get_db)) -> dict:
    policy = db.get(Policy, policy_id)
    if policy is None:
        raise HTTPException(status_code=404, detail="Policy not found")
    for field in ("name", "description", "action", "enabled", "priority"):
        value = getattr(request, field)
        if value is not None:
            setattr(policy, field, value)
    if request.condition is not None:
        policy.condition_json = json.dumps(request.condition, ensure_ascii=False)
    policy.updated_at = datetime.now(timezone.utc)
    db.commit()
    return _serialize(policy)


def _serialize(policy: Policy) -> dict:
    return {
        "id": policy.id, "name": policy.name, "description": policy.description,
        "target": policy.target, "condition": json.loads(policy.condition_json),
        "action": policy.action, "enabled": policy.enabled, "priority": policy.priority,
    }
