"""Bank simulator: the only code permitted to move money.

Atomicity
---------
``execute_transfer`` deliberately does **not** commit. It performs the debit,
the credit, and the ledger insert inside the caller's session so all three are
one database transaction -- a partial transfer is therefore impossible: either
the whole unit commits or none of it does.

Concurrency
-----------
Balance checks are read-modify-write, so two concurrent transfers from the same
account could each see a sufficient balance and jointly overdraw it. Both rows
are therefore locked with ``SELECT ... FOR UPDATE`` before being read, and the
locks are always taken in ascending id order so two transfers moving money in
opposite directions cannot deadlock against each other.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AccountNotFoundError,
    CurrencyMismatchError,
    InsufficientFundsError,
    SameAccountTransferError,
)
from app.models import BankAccount, Transaction, TransactionStatus


def _lock_accounts(db: Session, account_ids: set[int]) -> dict[int, BankAccount]:
    """Fetch accounts, row-locked, in a deterministic order."""
    statement = (
        select(BankAccount)
        .where(BankAccount.id.in_(account_ids))
        # Ascending id is the global lock ordering. Every writer must take
        # locks in this order or deadlocks become possible.
        .order_by(BankAccount.id)
    )

    # SQLite has no row-level locking -- it serialises writers with a
    # database-level write lock, which gives the same safety property. Emitting
    # FOR UPDATE there is a no-op at best, so it is skipped explicitly.
    if db.get_bind().dialect.name != "sqlite":
        statement = statement.with_for_update()

    return {account.id: account for account in db.execute(statement).scalars()}


def execute_transfer(
    db: Session,
    *,
    source_account_id: int,
    destination_account_id: int,
    amount: Decimal,
    currency: str = "INR",
    reference: str = "",
    description: str = "",
    proposal_id: int | None = None,
) -> tuple[Transaction, BankAccount, BankAccount]:
    """Move ``amount`` from one account to another.

    Returns the ledger entry plus both accounts with updated balances. Raises a
    subclass of ``AegisError`` if the transfer is not permissible; the caller is
    responsible for rolling back.
    """
    if source_account_id == destination_account_id:
        raise SameAccountTransferError(source_account_id)

    accounts = _lock_accounts(db, {source_account_id, destination_account_id})

    source = accounts.get(source_account_id)
    if source is None:
        raise AccountNotFoundError(source_account_id, role="source")

    destination = accounts.get(destination_account_id)
    if destination is None:
        raise AccountNotFoundError(destination_account_id, role="destination")

    # No FX in the simulator: every leg must share one currency.
    if source.currency != currency:
        raise CurrencyMismatchError(currency, source.currency, source.id)
    if destination.currency != currency:
        raise CurrencyMismatchError(currency, destination.currency, destination.id)

    if source.balance < amount:
        raise InsufficientFundsError(source.id, source.balance, amount)

    source.balance = source.balance - amount
    destination.balance = destination.balance + amount

    transaction = Transaction(
        source_account_id=source.id,
        destination_account_id=destination.id,
        amount=amount,
        currency=currency,
        status=TransactionStatus.COMPLETED,
        reference=reference,
        description=description,
        proposal_id=proposal_id,
    )
    db.add(transaction)

    # Flush (not commit) so the row gets its id and the CHECK constraints fire
    # now, while the caller can still roll the whole unit back.
    db.flush()

    return transaction, source, destination


def get_account(db: Session, account_id: int) -> BankAccount:
    account = db.get(BankAccount, account_id)
    if account is None:
        raise AccountNotFoundError(account_id)
    return account


def list_accounts(db: Session) -> list[BankAccount]:
    statement = select(BankAccount).order_by(BankAccount.id)
    return list(db.execute(statement).scalars())


def list_account_transactions(
    db: Session, account_id: int, *, limit: int = 100, offset: int = 0
) -> list[Transaction]:
    """Both sides of the ledger: money in and money out."""
    statement = (
        select(Transaction)
        .where(
            (Transaction.source_account_id == account_id)
            | (Transaction.destination_account_id == account_id)
        )
        .order_by(Transaction.timestamp.desc(), Transaction.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(statement).scalars())
