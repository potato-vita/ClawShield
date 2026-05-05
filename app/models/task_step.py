from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TaskStep(TimestampMixin, Base):
    __tablename__ = "task_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    step_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), index=True, nullable=False)
    goal_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    state: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    step_goal: Mapped[str] = mapped_column(Text, nullable=False)
    allowed_action_types_json: Mapped[list[str]] = mapped_column("allowed_action_types", JSON, nullable=False)
    allowed_tools_json: Mapped[list[str]] = mapped_column("allowed_tools", JSON, nullable=False)
    allowed_effects_json: Mapped[list[str]] = mapped_column("allowed_effects", JSON, nullable=False)
    parent_step_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    @property
    def causal_anchor(self) -> str:
        summary = (self.step_goal or "").strip()
        if len(summary) > 120:
            summary = summary[:117] + "..."
        return f"{self.step_id}:{summary}"
