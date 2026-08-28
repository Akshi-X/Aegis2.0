"""Bank simulator write endpoint.

Phase 1 note: this executes a transfer directly. From Phase 2, agent-initiated
transfers must instead travel through the AEGIS-X orchestrator, and this route
becomes the internal execution sink that only the governance engine may call.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AccountNotFoundError,
    AegisError,
    CurrencyMismatchError,
    InsufficientFundsError,
    SameAccountTransferError,
)
from app.database.session import get_db
from app.models import AuditEventType
from app.schemas.bank import AccountBalance, TransactionRead, TransferRequest, TransferResponse
from app.services import audit, bank

router = APIRouter(prefix="/bank", tags=["bank"])

# 404 when the resource does not exist; 422 when it exists but the request is
# not a permissible operation on it.
_STATUS_BY_ERROR: dict[type[AegisError], int] = {
    AccountNotFoundError: status.HTTP_404_NOT_FOUND,
    InsufficientFundsError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    CurrencyMismatchError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    SameAccountTransferError: status.HTTP_422_UNPROCESSABLE_ENTITY,
}


@router.post(
    "/transfer",
    response_model=TransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute a simulated transfer",
    responses={
        404: {"description": "Source or destination account does not exist"},
        422: {"description": "Insufficient funds, currency mismatch, or invalid amount"},
    },
)
def transfer(
    payload: TransferRequest, db: Session = Depends(get_db)
) -> TransferResponse:
    try:
        transaction, source, destination = bank.execute_transfer(
            db,
            source_account_id=payload.source_account_id,
            destination_account_id=payload.destination_account_id,
            amount=payload.amount,
            currency=payload.currency,
            reference=payload.reference,
            description=payload.description,
        )
    except AegisError as exc:
        # Discard the partial unit of work, then record the refusal on its own.
        # A rejected transfer is not a ledger entry, but it is very much an
        # auditable event.
        db.rollback()
        audit.record(
            db,
            event_type=AuditEventType.TRANSFER_REJECTED,
            actor="api",
            message=exc.message,
            entity_type="bank_account",
            entity_id=payload.source_account_id,
            payload={
                "code": exc.code,
                "source_account_id": payload.source_account_id,
                "destination_account_id": payload.destination_account_id,
                "amount": str(payload.amount),
                "currency": payload.currency,
                "reference": payload.reference,
            },
        )
        db.commit()

        raise HTTPException(
            status_code=_STATUS_BY_ERROR.get(
                type(exc), status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail={"code": exc.code, "message": exc.message},
        ) from exc

    # Same transaction as the money movement: the log cannot claim a transfer
    # that was ultimately rolled back.
    audit.record(
        db,
        event_type=AuditEventType.TRANSFER_EXECUTED,
        actor="api",
        message=(
            f"Transferred {payload.amount} {payload.currency} from "
            f"{source.account_number} to {destination.account_number}."
        ),
        entity_type="transaction",
        entity_id=transaction.id,
        payload={
            "transaction_id": transaction.id,
            "amount": str(transaction.amount),
            "currency": transaction.currency,
            "source_account_id": source.id,
            "destination_account_id": destination.id,
            "source_balance_after": str(source.balance),
            "destination_balance_after": str(destination.balance),
            "reference": transaction.reference,
        },
    )
    db.commit()

    return TransferResponse(
        transaction=TransactionRead.model_validate(transaction),
        source_account=AccountBalance.model_validate(source),
        destination_account=AccountBalance.model_validate(destination),
    )
