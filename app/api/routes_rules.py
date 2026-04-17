from pathlib import Path

import yaml
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import get_settings
from app.dependencies import get_db
from app.models.schemas_rule import RuleCreate, RuleRead
from app.services.rule_service import RuleService


router = APIRouter(prefix="/api", tags=["rules"])


@router.get("/rules", response_model=list[RuleRead])
def list_rules(db: Session = Depends(get_db)):
    return RuleService(db).list_rules()


@router.post("/rules", response_model=RuleRead)
def create_rule(payload: RuleCreate, db: Session = Depends(get_db)):
    return RuleService(db).upsert_rule(payload)


@router.put("/rules/{rule_id}", response_model=RuleRead)
def update_rule(rule_id: str, payload: RuleCreate, db: Session = Depends(get_db)):
    if rule_id != payload.rule_id:
        raise HTTPException(status_code=400, detail="rule_id mismatch")
    return RuleService(db).upsert_rule(payload)


@router.get("/boundaries")
def get_boundaries():
    settings = get_settings()
    path = settings.resolve_path(settings.rules_path)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@router.put("/boundaries")
def update_boundaries(payload: dict):
    settings = get_settings()
    path = settings.resolve_path(settings.rules_path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, allow_unicode=True, sort_keys=False)
    return {"ok": True}
