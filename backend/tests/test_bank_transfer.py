"""Bank simulator tests.

The three cases the phase requires -- success, insufficient balance, invalid
destination -- plus the invariants that make those results trustworthy:
atomicity on failure and conservation of money across the ledger.
"""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, BankAccount, Transaction

NONEXISTENT_ACCOUNT_ID = 999_999


def balance_of(db: Session, account_id: int) -> Decimal:
    """Read a balance straight from the database, ignoring identity-map state."""
    db.expire_all()
    account = db.get(BankAccount, account_id)
    assert account is not None
    return account.balance


def total_money(db: Session) -> Decimal:
    db.expire_all()
    return db.execute(select(func.sum(BankAccount.balance))).scalar_one()


# --------------------------------------------------------------------------- #
# Seed data
# --------------------------------------------------------------------------- #

def test_seed_creates_expected_banking_environment(
    db: Session, accounts: dict[str, BankAccount]
) -> None:
    assert accounts["company"].balance == Decimal("500000000.00")
    assert accounts["company"].currency == "INR"
    assert accounts["company"].owner_type == "COMPANY"

    # Ids are sequential and stable, which the documented sample requests rely on.
    assert [accounts[k].id for k in ("company", "abc", "xyz", "unknown")] == [1, 2, 3, 4]

    from app.models import Agent, Counterparty

    agent = db.execute(select(Agent)).scalar_one()
    assert agent.name == "Treasury Agent"
    assert agent.objective == "Pay legitimate company vendor invoices."
    assert agent.max_transaction_limit == Decimal("100000.00")
    assert agent.daily_limit == Decimal("500000.00")
    assert agent.source_account_id == accounts["company"].id

    trusted = {
        cp.name: cp.trusted for cp in db.execute(select(Counterparty)).scalars()
    }
    assert trusted == {
        "ABC Technologies": True,
        "XYZ Cloud": True,
        "Unknown Account": False,
    }


# --------------------------------------------------------------------------- #
# Successful transfer
# --------------------------------------------------------------------------- #

def test_successful_transfer(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    source_id = accounts["company"].id
    destination_id = accounts["abc"].id

    response = client.post(
        "/bank/transfer",
        json={
            "source_account_id": source_id,
            "destination_account_id": destination_id,
            "amount": "50000.00",
            "currency": "INR",
            "reference": "INV-204",
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()

    assert Decimal(body["transaction"]["amount"]) == Decimal("50000.00")
    assert body["transaction"]["status"] == "COMPLETED"
    assert body["transaction"]["reference"] == "INV-204"
    # Direct transfers are not agent proposals.
    assert body["transaction"]["proposal_id"] is None

    # Updated balances are returned to the caller...
    assert Decimal(body["source_account"]["balance"]) == Decimal("499950000.00")
    assert Decimal(body["destination_account"]["balance"]) == Decimal("50000.00")

    # ...and actually persisted.
    assert balance_of(db, source_id) == Decimal("499950000.00")
    assert balance_of(db, destination_id) == Decimal("50000.00")

    ledger = db.execute(select(Transaction)).scalars().all()
    assert len(ledger) == 1


def test_transfer_conserves_total_money(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    before = total_money(db)

    client.post(
        "/bank/transfer",
        json={
            "source_account_id": accounts["company"].id,
            "destination_account_id": accounts["xyz"].id,
            "amount": "125000.50",
        },
    )

    # A transfer moves money; it must never create or destroy any.
    assert total_money(db) == before


def test_successful_transfer_writes_audit_entry(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    client.post(
        "/bank/transfer",
        json={
            "source_account_id": accounts["company"].id,
            "destination_account_id": accounts["abc"].id,
            "amount": "1000.00",
        },
    )

    db.expire_all()
    entry = db.execute(
        select(AuditLog).where(AuditLog.event_type == "TRANSFER_EXECUTED")
    ).scalar_one()
    assert entry.payload["amount"] == "1000.00"
    assert entry.payload["source_balance_after"] == "499999000.00"


# --------------------------------------------------------------------------- #
# Insufficient balance
# --------------------------------------------------------------------------- #

def test_insufficient_balance_is_rejected(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    source_id = accounts["company"].id
    destination_id = accounts["abc"].id

    response = client.post(
        "/bank/transfer",
        json={
            "source_account_id": source_id,
            "destination_account_id": destination_id,
            # One rupee more than the account holds.
            "amount": "500000001.00",
        },
    )

    assert response.status_code == 422, response.text
    assert response.json()["detail"]["code"] == "insufficient_funds"

    # Nothing moved: neither a partial debit nor a phantom credit.
    assert balance_of(db, source_id) == Decimal("500000000.00")
    assert balance_of(db, destination_id) == Decimal("0.00")
    assert db.execute(select(func.count()).select_from(Transaction)).scalar_one() == 0


def test_rejected_transfer_is_audited(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    client.post(
        "/bank/transfer",
        json={
            "source_account_id": accounts["company"].id,
            "destination_account_id": accounts["abc"].id,
            "amount": "999999999.00",
        },
    )

    db.expire_all()
    entry = db.execute(
        select(AuditLog).where(AuditLog.event_type == "TRANSFER_REJECTED")
    ).scalar_one()
    assert entry.payload["code"] == "insufficient_funds"
    # The refusal is logged even though no transaction row exists.
    assert db.execute(select(func.count()).select_from(Transaction)).scalar_one() == 0


def test_exact_balance_transfer_succeeds(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    """Boundary: spending the entire balance is allowed, leaving exactly zero."""
    response = client.post(
        "/bank/transfer",
        json={
            "source_account_id": accounts["company"].id,
            "destination_account_id": accounts["abc"].id,
            "amount": "500000000.00",
        },
    )

    assert response.status_code == 201, response.text
    assert balance_of(db, accounts["company"].id) == Decimal("0.00")


# --------------------------------------------------------------------------- #
# Invalid destination account
# --------------------------------------------------------------------------- #

def test_invalid_destination_account_is_rejected(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    source_id = accounts["company"].id

    response = client.post(
        "/bank/transfer",
        json={
            "source_account_id": source_id,
            "destination_account_id": NONEXISTENT_ACCOUNT_ID,
            "amount": "50000.00",
        },
    )

    assert response.status_code == 404, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "account_not_found"
    assert "destination" in detail["message"]

    # The source account must be untouched.
    assert balance_of(db, source_id) == Decimal("500000000.00")
    assert db.execute(select(func.count()).select_from(Transaction)).scalar_one() == 0


def test_invalid_source_account_is_rejected(
    client: TestClient, accounts: dict[str, BankAccount]
) -> None:
    response = client.post(
        "/bank/transfer",
        json={
            "source_account_id": NONEXISTENT_ACCOUNT_ID,
            "destination_account_id": accounts["abc"].id,
            "amount": "50000.00",
        },
    )

    assert response.status_code == 404
    assert "source" in response.json()["detail"]["message"]


# --------------------------------------------------------------------------- #
# Request validation
# --------------------------------------------------------------------------- #

def test_non_positive_amounts_are_rejected(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    for amount in ("0.00", "-100.00"):
        response = client.post(
            "/bank/transfer",
            json={
                "source_account_id": accounts["company"].id,
                "destination_account_id": accounts["abc"].id,
                "amount": amount,
            },
        )
        # A negative transfer would be a withdrawal wearing a disguise.
        assert response.status_code == 422, f"amount={amount}: {response.text}"

    assert balance_of(db, accounts["company"].id) == Decimal("500000000.00")


def test_transfer_to_same_account_is_rejected(
    client: TestClient, accounts: dict[str, BankAccount]
) -> None:
    response = client.post(
        "/bank/transfer",
        json={
            "source_account_id": accounts["company"].id,
            "destination_account_id": accounts["company"].id,
            "amount": "1000.00",
        },
    )
    assert response.status_code == 422


def test_currency_mismatch_is_rejected(
    client: TestClient, db: Session, accounts: dict[str, BankAccount]
) -> None:
    usd_account = BankAccount(
        account_name="US Subsidiary",
        account_number="ACC3000000001",
        balance=Decimal("1000.00"),
        currency="USD",
        owner_type="COMPANY",
    )
    db.add(usd_account)
    db.commit()

    response = client.post(
        "/bank/transfer",
        json={
            "source_account_id": accounts["company"].id,
            "destination_account_id": usd_account.id,
            "amount": "1000.00",
            "currency": "INR",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "currency_mismatch"


# --------------------------------------------------------------------------- #
# Read endpoints
# --------------------------------------------------------------------------- #

def test_list_accounts(client: TestClient) -> None:
    response = client.get("/accounts")
    assert response.status_code == 200

    body = response.json()
    assert len(body) == 4
    assert [a["account_name"] for a in body] == [
        "Main Company Account",
        "ABC Technologies",
        "XYZ Cloud",
        "Unknown Account",
    ]


def test_get_account(client: TestClient, accounts: dict[str, BankAccount]) -> None:
    response = client.get(f"/accounts/{accounts['company'].id}")
    assert response.status_code == 200
    assert response.json()["account_number"] == "ACC1000000001"


def test_get_unknown_account_returns_404(client: TestClient) -> None:
    response = client.get(f"/accounts/{NONEXISTENT_ACCOUNT_ID}")
    assert response.status_code == 404


def test_account_transactions_lists_both_directions(
    client: TestClient, accounts: dict[str, BankAccount]
) -> None:
    client.post(
        "/bank/transfer",
        json={
            "source_account_id": accounts["company"].id,
            "destination_account_id": accounts["abc"].id,
            "amount": "20000.00",
            "reference": "INV-1",
        },
    )
    client.post(
        "/bank/transfer",
        json={
            "source_account_id": accounts["abc"].id,
            "destination_account_id": accounts["xyz"].id,
            "amount": "5000.00",
            "reference": "INV-2",
        },
    )

    # ABC was the destination of the first transfer and the source of the
    # second, so its ledger must contain both.
    response = client.get(f"/accounts/{accounts['abc'].id}/transactions")
    assert response.status_code == 200
    references = {t["reference"] for t in response.json()}
    assert references == {"INV-1", "INV-2"}

    # XYZ only ever received money.
    response = client.get(f"/accounts/{accounts['xyz'].id}/transactions")
    assert [t["reference"] for t in response.json()] == ["INV-2"]


def test_transactions_for_unknown_account_returns_404(client: TestClient) -> None:
    response = client.get(f"/accounts/{NONEXISTENT_ACCOUNT_ID}/transactions")
    assert response.status_code == 404
