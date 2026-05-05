from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class AuditReport(TimestampMixin, Base):
    __tablename__ = "audit_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    run_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    task_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    semantic_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    final_disposition: Mapped[str | None] = mapped_column(String(32), nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
