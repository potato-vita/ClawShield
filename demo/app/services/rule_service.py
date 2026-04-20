from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from app.models.db_models import RuleDB
from app.models.schemas_rule import RuleCreate


class RuleService:
    def __init__(self, db: Session):
        self.db = db

    def list_rules(self) -> list[RuleDB]:
        return self.db.query(RuleDB).order_by(RuleDB.rule_id.asc()).all()

    def upsert_rule(self, payload: RuleCreate) -> RuleDB:
        existing = self.db.query(RuleDB).filter(RuleDB.rule_id == payload.rule_id).first()
        if existing:
            existing.name = payload.name
            existing.category = payload.category
            existing.severity = payload.severity
            existing.decision = payload.decision
            existing.enabled = payload.enabled
            existing.definition_json = payload.definition_json
            existing.description = payload.description
            self.db.commit()
            self.db.refresh(existing)
            return existing

        rule = RuleDB(**payload.model_dump())
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def seed_from_risk_yaml(self, risk_rules_path: str) -> int:
        path = Path(risk_rules_path)
        if not path.exists():
            return 0
        with path.open("r", encoding="utf-8") as f:
            content = yaml.safe_load(f) or {}
        count = 0
        for item in content.get("rules", []):
            self.upsert_rule(
                RuleCreate(
                    rule_id=item.get("rule_id", ""),
                    name=item.get("name", ""),
                    category=item.get("category", "general"),
                    severity=item.get("severity", "medium"),
                    decision=item.get("decision", "alert"),
                    enabled=item.get("enabled", True),
                    definition_json=item,
                    description=item.get("description", ""),
                )
            )
            count += 1
        return count
