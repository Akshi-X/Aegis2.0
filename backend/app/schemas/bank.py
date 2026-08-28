"""Request/response contracts for the bank simulator."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import OwnerType, TransactionStatus


class BankAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_name: str
    account_number: str
    balance: Decimal
    currency: str
    owner_type: OwnerType
    created_at: datetime


class AccountBalance(BaseModel):
    """Compact balance view returned alongside a completed transfer."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_number: str
    balance: Decimal
    currency: str


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_account_id: int
    destination_account_id: int
    amount: Decimal
    currency: str
    status: TransactionStatus
    reference: str
    description: str
    proposal_id: int | None
    timestamp: datetime


class TransferRequest(BaseModel):
    source_account_id: int
    destination_account_id: int

    # gt=0 rejects zero and negative amounts before any handler runs; a
    # negative "transfer" would otherwise be a withdrawal in disguise.
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2, examples=["50000.00"])
    currency: str = Field(default="INR", min_length=3, max_length=3)
    reference: str = Field(default="", max_length=128, examples=["INV-204"])
    description: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def _distinct_accounts(self) -> TransferRequest:
        if self.source_account_id == self.destination_account_id:
            raise ValueError("source_account_id and destination_account_id must differ")
        return self


class TransferResponse(BaseModel):
    transaction: TransactionRead
    source_account: AccountBalance
    destination_account: AccountBalance
