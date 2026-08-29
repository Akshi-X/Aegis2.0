"""Tests for the Blast Radius engine."""

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent, Counterparty, ActionProposal
from app.models.enums import ActionType, ProposalStatus
from app.services.engines.base import EvaluationContext, EngineStatus
from app.services.engines.blast_radius import BlastRadiusService

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


def _context(db: Session, amount: str, recipient_number: str) -> EvaluationContext:
    agent = db.query(Agent).filter_by(name="Treasury Agent").one()  # daily limit 500k
    proposal = ActionProposal(
        agent_id=agent.id,
        action_type=ActionType.TRANSFER,
        amount=Decimal(amount),
        currency="INR",
        recipient_name="Recipient",
        recipient_account_number=recipient_number,
        purpose="x",
        source_account_id=agent.source_account_id,
        status=ProposalStatus.PROPOSED,
    )
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


def test_small_payment_to_trusted_vendor_passes(db: Session):
    result = BlastRadiusService().evaluate(_context(db, "50000", "ACC2000000001"))
    assert result.status == EngineStatus.PASS
    assert result.risk_score < 40.0
    assert result.details["recoverability"] == "recoverable"


def test_exceeding_daily_authority_is_flagged(db: Session):
    # 600k > Treasury's 500k daily limit, but to a trusted (recoverable) vendor.
    result = BlastRadiusService().evaluate(_context(db, "600000", "ACC2000000001"))
    assert "EXCEEDS_DAILY_AUTHORITY" in result.flags
    # Recoverable destination keeps a large-but-clawback-able transfer out of FAIL.
    assert result.status == EngineStatus.WARN


def test_unresolved_destination_is_critical(db: Session):
    result = BlastRadiusService().evaluate(_context(db, "600000", "ACC-DOES-NOT-EXIST"))
    assert result.status == EngineStatus.FAIL
    assert "CRITICAL_BLAST_RADIUS" in result.flags
    assert "UNRECOVERABLE_DESTINATION" in result.flags
    assert result.details["recoverability"] == "unresolved"


def test_untrusted_counterparty_amplifies(db: Session):
    # 400k = 0.8 of the daily limit, to the untrusted Unknown Account.
    result = BlastRadiusService().evaluate(_context(db, "400000", "ACC9000000001"))
    assert result.status == EngineStatus.FAIL
    assert "UNRECOVERABLE_DESTINATION" in result.flags
    assert result.details["recoverability"] == "untrusted"


def test_recoverability_dampens_identical_amount(db: Session):
    trusted = BlastRadiusService().evaluate(_context(db, "600000", "ACC2000000001"))
    unresolved = BlastRadiusService().evaluate(_context(db, "600000", "ACC-GONE"))
    assert trusted.risk_score is not None and unresolved.risk_score is not None
    assert trusted.risk_score < unresolved.risk_score


def test_non_positive_amount_carries_no_exposure(db: Session):
    result = BlastRadiusService().evaluate(_context(db, "0", "ACC2000000001"))
    assert result.status == EngineStatus.PASS
    assert result.risk_score == 0.0
