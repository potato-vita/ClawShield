from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TaskGoal(TimestampMixin, Base):
    __tablename__ = "task_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    goal_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), index=True, nullable=False)
    task_intent: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    objective_summary: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_action_types_json: Mapped[list[str]] = mapped_column("allowed_action_types", JSON, nullable=False)
    allowed_tools_json: Mapped[list[str]] = mapped_column("allowed_tools", JSON, nullable=False)
    allowed_resource_scopes_json: Mapped[list[str]] = mapped_column("allowed_resource_scopes", JSON, nullable=False)
    expected_outputs_json: Mapped[list[str]] = mapped_column("expected_outputs", JSON, nullable=False)
    forbidden_actions_json: Mapped[list[str]] = mapped_column("forbidden_actions", JSON, nullable=False)
    forbidden_effects_json: Mapped[list[str]] = mapped_column("forbidden_effects", JSON, nullable=False)
    risk_constraints_json: Mapped[list[str]] = mapped_column("risk_constraints", JSON, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
