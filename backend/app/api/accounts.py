"""Read-only views onto the simulated bank."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import AccountNotFoundError
from app.database.session import get_db
from app.schemas.bank import BankAccountRead, TransactionRead
from app.services import bank

router = APIRouter(tags=["accounts"])


@router.get("/accounts", response_model=list[BankAccountRead], summary="List accounts")
def list_accounts(db: Session = Depends(get_db)) -> list[BankAccountRead]:
    return bank.list_accounts(db)


@router.get(
    "/accounts/{account_id}",
    response_model=BankAccountRead,
    summary="Fetch one account",
)
def get_account(account_id: int, db: Session = Depends(get_db)) -> BankAccountRead:
    try:
        return bank.get_account(db, account_id)
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc


@router.get(
    "/accounts/{account_id}/transactions",
    response_model=list[TransactionRead],
    summary="Ledger history for an account",
)
def list_account_transactions(
    account_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[TransactionRead]:
    # Confirm the account exists so an unknown id 404s rather than returning a
    # misleading empty list.
    try:
        bank.get_account(db, account_id)
    except AccountNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    return bank.list_account_transactions(db, account_id, limit=limit, offset=offset)
