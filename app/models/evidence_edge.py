from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class EvidenceEdge(TimestampMixin, Base):
    __tablename__ = "evidence_edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    from_node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    to_node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    edge_type: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str | None] = mapped_column(String(256), nullable=True)
