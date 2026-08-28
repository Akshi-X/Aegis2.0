"""Counterparties: known payees and their standing.

``account_number`` is a foreign key onto ``bank_accounts.account_number``
rather than a loose string copy, so a counterparty can never reference an
account that does not exist.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Counterparty(Base):
    __tablename__ = "counterparties"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    account_number: Mapped[str] = mapped_column(
        ForeignKey("bank_accounts.account_number"), unique=True, index=True
    )

    # Sits on the organisation's approved-vendor allow-list.
    trusted: Mapped[bool] = mapped_column(Boolean, default=False)
    # 0-100, higher is riskier. Phase 5 recomputes this from graph analysis.
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("50.00"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    bank_account = relationship(
        "BankAccount",
        primaryjoin="Counterparty.account_number == BankAccount.account_number",
        foreign_keys=[account_number],
        lazy="joined",
        viewonly=True,
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Counterparty {self.name} trusted={self.trusted}>"
