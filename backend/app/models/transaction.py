"""Transaction: an actual movement of money on the ledger.

A row here means money moved. Rejected attempts are not recorded as
transactions -- they are recorded in the audit log, because a failed transfer
is an event, not a ledger entry.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.types import MoneyType
from app.models.enums import TransactionStatus


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    source_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id"), index=True
    )
    destination_account_id: Mapped[int] = mapped_column(
        ForeignKey("bank_accounts.id"), index=True
    )

    amount: Mapped[Decimal] = mapped_column(MoneyType)
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    status: Mapped[str] = mapped_column(
        String(16), default=TransactionStatus.COMPLETED, index=True
    )

    reference: Mapped[str] = mapped_column(String(128), default="")
    description: Mapped[str] = mapped_column(Text, default="")

    # Set once an execution originates from an evaluated agent proposal.
    # Always NULL for direct transfers via POST /bank/transfer.
    proposal_id: Mapped[int | None] = mapped_column(
        ForeignKey("action_proposals.id"), nullable=True, index=True
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    source_account = relationship("BankAccount", foreign_keys=[source_account_id])
    destination_account = relationship(
        "BankAccount", foreign_keys=[destination_account_id]
    )

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_transactions_amount_positive"),
        CheckConstraint(
            "source_account_id <> destination_account_id",
            name="ck_transactions_distinct_accounts",
        ),
        Index("ix_transactions_source_time", "source_account_id", "timestamp"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"<Transaction {self.id} {self.amount} {self.currency} "
            f"{self.source_account_id}->{self.destination_account_id}>"
        )
