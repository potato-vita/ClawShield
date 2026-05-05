from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AlignmentEvaluation(TimestampMixin, Base):
    __tablename__ = "alignment_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    eval_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), index=True, nullable=False)
    tool_call_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    goal_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    step_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    goal_relevance: Mapped[float] = mapped_column(Float, nullable=False)
    state_legality: Mapped[float] = mapped_column(Float, nullable=False)
    resource_necessity: Mapped[float] = mapped_column(Float, nullable=False)
    effect_safety: Mapped[float] = mapped_column(Float, nullable=False)
    reason_support: Mapped[float] = mapped_column(Float, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    decision: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    reasons_json: Mapped[list[str]] = mapped_column("reasons", JSON, nullable=False)
    matched_rules_json: Mapped[list[dict]] = mapped_column("matched_rules", JSON, nullable=False)
