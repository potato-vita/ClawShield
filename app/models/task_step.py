from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TaskStep(TimestampMixin, Base):
    __tablename__ = "task_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    step_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.run_id"), index=True, nullable=False)
    goal_id: Mapped[str | None] = mapped_column(ForeignKey("task_goals.goal_id"), index=True, nullable=True)

    step_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    step_name: Mapped[str] = mapped_column(String(128), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    allowed_action_types_json: Mapped[list[str]] = mapped_column("allowed_action_types", JSON, default=list, nullable=False)
    allowed_tools_json: Mapped[list[str]] = mapped_column("allowed_tools", JSON, default=list, nullable=False)
