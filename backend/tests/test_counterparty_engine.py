"""Tests for the Counterparty intelligence engine."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent, BankAccount, Counterparty, Transaction, ActionProposal
from app.models.enums import TransactionStatus, ActionType, ProposalStatus
from app.services.engines.base import EvaluationContext, EngineStatus
from app.services.engines.counterparty import CounterpartyService

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


def _add_txn(db: Session, src: BankAccount, dst: BankAccount, amount: str) -> None:
    db.add(
        Transaction(
            source_account_id=src.id,
            destination_account_id=dst.id,
            amount=Decimal(amount),
            currency="INR",
            status=TransactionStatus.COMPLETED,
            timestamp=NOW,
        )
    )


def _context(db: Session, recipient_name: str, recipient_number: str | None) -> EvaluationContext:
    agent = db.query(Agent).filter_by(name="Treasury Agent").one()
    proposal = ActionProposal(
        agent_id=agent.id,
        action_type=ActionType.TRANSFER,
        amount=Decimal("50000.00"),
        currency="INR",
        recipient_name=recipient_name,
        recipient_account_number=recipient_number,
        purpose="Vendor payment",
        source_account_id=agent.source_account_id,
        status=ProposalStatus.PROPOSED,
    )
    counterparty = None
    if recipient_number:
        counterparty = db.execute(
            select(Counterparty).where(Counterparty.account_number == recipient_number)
        ).scalar_one_or_none()
    return EvaluationContext(
        db=db,
        proposal=proposal,
        agent=agent,
        source_account=agent.source_account,
        counterparty=counterparty,
        now=NOW,
    )


def test_trusted_vendor_passes(db: Session):
    ctx = _context(db, "ABC Technologies", "ACC2000000001")
    result = CounterpartyService().evaluate(ctx)

    assert result.status == EngineStatus.PASS
    assert result.risk_score < 40.0
    assert result.flags == []


def test_unresolved_recipient_fails(db: Session):
    # Account number that maps to no bank account at all.
    ctx = _context(db, "Offshore Shell", "ACC-DOES-NOT-EXIST")
    result = CounterpartyService().evaluate(ctx)

    assert result.status == EngineStatus.FAIL
    assert "UNRESOLVED_RECIPIENT" in result.flags


def test_untrusted_counterparty_fails(db: Session):
    ctx = _context(db, "Unknown Account", "ACC9000000001")
    result = CounterpartyService().evaluate(ctx)

    assert result.status == EngineStatus.FAIL
    assert "UNTRUSTED_COUNTERPARTY" in result.flags


def test_resolved_but_unverified_warns(db: Session, accounts):
    # A real account that is not on the approved-counterparty allow-list.
    ctx = _context(db, "Procurement Budget", "ACC1000000002")
    result = CounterpartyService().evaluate(ctx)

    assert result.status == EngineStatus.WARN
    assert "UNVERIFIED_COUNTERPARTY" in result.flags


def test_no_recipient_number_is_noop(db: Session):
    ctx = _context(db, "Someone", None)
    result = CounterpartyService().evaluate(ctx)

    assert result.status == EngineStatus.PASS
    assert result.risk_score == 0.0


def test_pass_through_entity_flagged(db: Session, accounts):
    # XYZ Cloud collects from two sources and forwards on to three distinct
    # destinations: mule/pass-through behaviour, even though it is trusted.
    xyz = accounts["xyz"]
    _add_txn(db, accounts["company"], xyz, "100000")
    _add_txn(db, accounts["abc"], xyz, "100000")
    _add_txn(db, xyz, accounts["company"], "60000")
    _add_txn(db, xyz, accounts["abc"], "60000")
    _add_txn(db, xyz, accounts["unknown"], "60000")
    db.commit()

    ctx = _context(db, "XYZ Cloud", "ACC2000000002")
    result = CounterpartyService().evaluate(ctx)

    assert "PASS_THROUGH_ENTITY" in result.flags
    assert result.status == EngineStatus.FAIL


def test_proximity_to_flagged_node(db: Session, accounts):
    # ABC (trusted) transacts with the untrusted Unknown Account.
    _add_txn(db, accounts["company"], accounts["abc"], "50000")
    # Small onward amount so this reads as proximity, not rapid-forwarding.
    _add_txn(db, accounts["abc"], accounts["unknown"], "5000")
    db.commit()

    ctx = _context(db, "ABC Technologies", "ACC2000000001")
    result = CounterpartyService().evaluate(ctx)

    assert "PROXIMITY_TO_FLAGGED" in result.flags
    assert result.details["graph"]["fan_out"] >= 1
