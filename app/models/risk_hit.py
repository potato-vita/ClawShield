from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RiskHit(TimestampMixin, Base):
    __tablename__ = "risk_hits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(64), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
