"""Tests for the Cascade and sequence engine."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models import Agent, BankAccount, Transaction, ActionProposal
from app.models.enums import TransactionStatus, ActionType, ProposalStatus
from app.services.engines.base import EvaluationContext, EngineStatus
from app.services.engines.cascade import CascadeService

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


def _add_txn(
    db: Session,
    src: BankAccount,
    dst: BankAccount,
    amount: str,
    *,
    minutes_ago: float,
) -> None:
    db.add(
        Transaction(
            source_account_id=src.id,
            destination_account_id=dst.id,
            amount=Decimal(amount),
            currency="INR",
            status=TransactionStatus.COMPLETED,
            timestamp=NOW - timedelta(minutes=minutes_ago),
        )
    )


def _context(
    db: Session,
    *,
    amount: str = "50000.00",
    recipient_number: str = "ACC2000000001",
    agent_name: str = "Treasury Agent",
) -> EvaluationContext:
    agent = db.query(Agent).filter_by(name=agent_name).one()
    proposal = ActionProposal(
        agent_id=agent.id,
        action_type=ActionType.TRANSFER,
        amount=Decimal(amount),
        currency="INR",
        recipient_name="ABC Technologies",
        recipient_account_number=recipient_number,
        purpose="Vendor payment",
        source_account_id=agent.source_account_id,
        status=ProposalStatus.PROPOSED,
    )
    return EvaluationContext(
        db=db,
        proposal=proposal,
        agent=agent,
        source_account=agent.source_account,
        counterparty=None,
        now=NOW,
    )


def test_quiet_ledger_single_proposal_passes(db: Session):
    # One action against an empty ledger is not a cascade.
    result = CascadeService().evaluate(_context(db))

    assert result.status == EngineStatus.PASS
    assert result.risk_score == 0.0
    assert result.flags == []


def test_rapid_repeated_transfers_flagged(db: Session, accounts):
    company, abc = accounts["company"], accounts["abc"]
    # Three transfers in the last few minutes; the proposal makes four.
    for m in (1, 3, 5):
        _add_txn(db, company, abc, "1000", minutes_ago=m)
    db.commit()

    result = CascadeService().evaluate(_context(db))

    assert "RAPID_REPEATED_TRANSFERS" in result.flags
    assert result.details["burst_count"] >= 4


def test_transaction_structuring_flagged(db: Session, accounts):
    # Treasury per-transaction limit is 100k. Several transfers just under it,
    # inside the burst window, that together far exceed it: smurfing.
    company, abc = accounts["company"], accounts["abc"]
    _add_txn(db, company, abc, "90000", minutes_ago=2)
    _add_txn(db, company, abc, "95000", minutes_ago=4)
    db.commit()

    # Proposal is the third just-under-limit slice.
    result = CascadeService().evaluate(_context(db, amount="92000.00"))

    assert "TRANSACTION_STRUCTURING" in result.flags
    assert result.status == EngineStatus.FAIL


def test_velocity_spike_flagged(db: Session, accounts):
    company, abc = accounts["company"], accounts["abc"]
    # A thin historical baseline spread over weeks...
    for d in range(1, 4):
        _add_txn(db, company, abc, "1000", minutes_ago=d * 60 * 24 * 7)
    # ...then a sudden burst of activity within the last hour.
    for m in (10, 20, 30, 40):
        _add_txn(db, company, abc, "1000", minutes_ago=m)
    db.commit()

    result = CascadeService().evaluate(_context(db))

    assert "VELOCITY_SPIKE" in result.flags


def test_coordinated_cascade_flagged(db: Session, accounts):
    # Three distinct source accounts funnel into the same recipient (ABC)
    # within the coordination window; the proposal is a fourth mover.
    abc = accounts["abc"]
    _add_txn(db, accounts["company"], abc, "10000", minutes_ago=2)
    _add_txn(db, accounts["xyz"], abc, "10000", minutes_ago=3)
    _add_txn(db, accounts["unknown"], abc, "10000", minutes_ago=4)
    db.commit()

    # Proposal source is the Marketing agent -> a different source again.
    result = CascadeService().evaluate(
        _context(db, agent_name="Marketing Agent", recipient_number="ACC2000000001")
    )

    assert "COORDINATED_CASCADE" in result.flags
    assert result.status == EngineStatus.FAIL
