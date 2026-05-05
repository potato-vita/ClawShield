from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.alignment_evaluation import AlignmentEvaluation


class AlignmentRepository:
    def create(self, db: Session, evaluation: AlignmentEvaluation) -> AlignmentEvaluation:
        db.add(evaluation)
        db.flush()
        return evaluation

    def list_by_run_id(self, db: Session, run_id: str) -> list[AlignmentEvaluation]:
        stmt: Select[tuple[AlignmentEvaluation]] = (
            select(AlignmentEvaluation)
            .where(AlignmentEvaluation.run_id == run_id)
            .order_by(AlignmentEvaluation.created_at.asc())
        )
        return db.execute(stmt).scalars().all()


alignment_repository = AlignmentRepository()
