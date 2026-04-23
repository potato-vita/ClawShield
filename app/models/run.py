from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Run(TimestampMixin, Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    session_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    task_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_type: Mapped[str] = mapped_column(String(64), default="unknown", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="created", nullable=False)
    final_risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    disposition: Mapped[str | None] = mapped_column(String(32), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
