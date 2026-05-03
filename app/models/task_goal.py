from __future__ import annotations

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

    allowed_action_types_json: Mapped[list[str]] = mapped_column(
        "allowed_action_types",
        JSON,
        default=list,
        nullable=False,
    )
    allowed_tools_json: Mapped[list[str]] = mapped_column(
        "allowed_tools",
        JSON,
        default=list,
        nullable=False,
    )
    allowed_resource_scopes_json: Mapped[list[str]] = mapped_column(
        "allowed_resource_scopes",
        JSON,
        default=list,
        nullable=False,
    )
    forbidden_actions_json: Mapped[list[str]] = mapped_column(
        "forbidden_actions",
        JSON,
        default=list,
        nullable=False,
    )
    forbidden_effects_json: Mapped[list[str]] = mapped_column(
        "forbidden_effects",
        JSON,
        default=list,
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
