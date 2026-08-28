"""Append-only audit log.

Every consequential event lands here, including rejected transfer attempts --
a refusal is exactly the kind of thing an auditor needs to see.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.types import PortableJSON


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    event_type: Mapped[str] = mapped_column(String(48), index=True)
    # Loose references rather than foreign keys: audit rows must survive the
    # deletion of whatever they describe.
    entity_type: Mapped[str | None] = mapped_column(String(48), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    agent_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Who or what triggered this: "system", "api", an agent name, a reviewer.
    actor: Mapped[str] = mapped_column(String(128), default="system")
    message: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<AuditLog {self.event_type} entity={self.entity_type}:{self.entity_id}>"
