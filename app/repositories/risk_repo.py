from __future__ import annotations

from sqlalchemy import Select, delete, select
from sqlalchemy.orm import Session

from app.models.risk_hit import RiskHit


class RiskRepository:
    """Persistence access for risk findings."""

    def replace_for_run(self, db: Session, run_id: str, findings: list[RiskHit]) -> list[RiskHit]:
        db.execute(delete(RiskHit).where(RiskHit.run_id == run_id))
        for item in findings:
            db.add(item)
        db.flush()
        return findings

    def list_by_run_id(self, db: Session, run_id: str) -> list[RiskHit]:
        stmt: Select[tuple[RiskHit]] = select(RiskHit).where(RiskHit.run_id == run_id).order_by(RiskHit.created_at.asc())
        return db.execute(stmt).scalars().all()


risk_repository = RiskRepository()
