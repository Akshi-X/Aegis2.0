"""Bank account: the ledger balance that transfers move money between."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.enums import OwnerType
from app.models.types import MoneyType


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    account_name: Mapped[str] = mapped_column(String(160), index=True)
    account_number: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    balance: Mapped[Decimal] = mapped_column(MoneyType, default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    owner_type: Mapped[str] = mapped_column(String(16), default=OwnerType.EXTERNAL)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        # Last line of defence: even a logic bug cannot drive an account
        # negative, because the database itself refuses the write.
        CheckConstraint("balance >= 0", name="ck_bank_accounts_balance_non_negative"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<BankAccount {self.account_number} {self.currency} {self.balance}>"
