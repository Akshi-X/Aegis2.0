"""Autonomous agent registry and its authority envelope.

The limits stored here are enforced server-side by AEGIS-X. An agent is never
trusted to respect its own limits.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import AgentStatus
from app.models.types import MoneyType, PortableJSON


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    objective: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default=AgentStatus.ACTIVE)

    # Authority envelope. Enforced server-side by the Authority engine; an
    # agent is never trusted to respect its own limits.
    max_transaction_limit: Mapped[Decimal] = mapped_column(
        MoneyType, default=Decimal("100000.00")
    )
    daily_limit: Mapped[Decimal] = mapped_column(
        MoneyType, default=Decimal("500000.00")
    )
    # Allow-lists, not deny-lists: anything absent is refused by default.
    allowed_actions: Mapped[list] = mapped_column(PortableJSON, default=list)
    allowed_currencies: Mapped[list] = mapped_column(PortableJSON, default=list)
    # Accounts delegated to this agent in addition to source_account_id.
    # Spending from anything outside this set plus the primary is unauthorised.
    authorized_account_ids: Mapped[list] = mapped_column(PortableJSON, default=list)

    # 0-100. Drives autonomy tier from Phase 6 onward.
    trust_score: Mapped[float] = mapped_column(Numeric(5, 2), default=Decimal("85.00"))

    # The account this agent is authorised to spend from.
    source_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("bank_accounts.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source_account = relationship("BankAccount", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Agent {self.name} status={self.status}>"
