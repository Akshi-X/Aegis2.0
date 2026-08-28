"""Tests for the Behavioural Anomaly engine."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models import Agent, BankAccount, Transaction, ActionProposal
from app.models.enums import TransactionStatus, ActionType, ProposalStatus
from app.services.engines.anomaly import AnomalyService
from app.services.engines.base import EvaluationContext, EngineStatus

def setup_historical_data(db: Session, agent: Agent, vendor: BankAccount):
    """Insert controlled historical transactions."""
    amounts = [250.0, 250.0, 250.0, 250.0, 250.0]
    hours = [10, 11, 12, 13, 14]
    base_time = datetime(2026, 8, 1, tzinfo=timezone.utc)

    for i, amount in enumerate(amounts):
        tx = Transaction(
            source_account_id=agent.source_account_id,
            destination_account_id=vendor.id,
            amount=Decimal(str(amount)),
            currency="INR",
            status=TransactionStatus.COMPLETED,
            timestamp=base_time.replace(hour=hours[i]) + timedelta(days=i),
        )
        db.add(tx)
    db.commit()

@pytest.fixture
def agent(db: Session) -> Agent:
    return db.query(Agent).filter_by(name="Treasury Agent").one()

@pytest.fixture
def vendor(db: Session) -> BankAccount:
    return db.query(BankAccount).filter_by(account_name="ABC Technologies").one()

@pytest.fixture
def test_context(db: Session, agent: Agent, vendor: BankAccount) -> EvaluationContext:
    setup_historical_data(db, agent, vendor)

    # Normal proposal
    proposal = ActionProposal(
        agent_id=agent.id,
        action_type=ActionType.TRANSFER,
        amount=Decimal("250.00"),
        currency="INR",
        recipient_name="ABC Technologies",
        recipient_account_number=vendor.account_number,
        purpose="Vendor payment",
        source_account_id=agent.source_account_id,
        status=ProposalStatus.PROPOSED,
    )

    from app.models import Counterparty
    from sqlalchemy import select
    counterparty = db.execute(
        select(Counterparty).where(Counterparty.account_number == vendor.account_number)
    ).scalar_one_or_none()

    return EvaluationContext(
        db=db,
        proposal=proposal,
        agent=agent,
        source_account=agent.source_account,
        counterparty=counterparty,
        now=datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)  # Business hours
    )

def test_anomaly_model_initialization():
    engine = AnomalyService()
    # Check that model is not initialized yet
    assert not engine._initialized

    # Initialize it manually to test loading
    engine._initialize_model()
    assert engine._initialized
    assert engine._model is not None
    assert engine._scaler is not None
    assert engine._raw_min is not None
    assert engine._raw_max is not None

def test_anomaly_normal_transaction(test_context: EvaluationContext):
    engine = AnomalyService()
    result = engine.evaluate(test_context)

    assert result.status == EngineStatus.PASS
    assert result.risk_score < 40.0
    assert "HIGH_BEHAVIOURAL_ANOMALY" not in result.flags

def test_anomaly_large_amount_spike(test_context: EvaluationContext):
    # Make amount extremely large (10x role average)
    test_context.proposal.amount = Decimal("3000.00")
    engine = AnomalyService()
    result = engine.evaluate(test_context)

    assert result.status == EngineStatus.FAIL or result.status == EngineStatus.WARN
    assert result.risk_score >= 40.0
    assert "ANOMALOUS_AMOUNT_SPIKE" in result.flags

def test_anomaly_odd_hours(test_context: EvaluationContext):
    # Change time to 3 AM
    test_context.now = test_context.now.replace(hour=3)
    engine = AnomalyService()
    result = engine.evaluate(test_context)

    assert "ANOMALOUS_OFF_HOURS_ACTIVITY" in result.flags

def test_anomaly_new_recipient(test_context: EvaluationContext):
    # Unknown recipient name
    test_context.proposal.recipient_name = "New Unknown Recipient"
    test_context.proposal.recipient_account_number = "99999999"
    engine = AnomalyService()
    result = engine.evaluate(test_context)

    assert "ANOMALOUS_NEW_RECIPIENT" in result.flags

def test_anomaly_high_frequency_burst(db: Session, test_context: EvaluationContext):
    # Add several transactions in the last 2 minutes to trigger burst anomaly
    agent = test_context.agent
    vendor = db.query(BankAccount).filter_by(account_name="ABC Technologies").one()
    base_time = test_context.now

    for i in range(5):
        tx = Transaction(
            source_account_id=agent.source_account_id,
            destination_account_id=vendor.id,
            amount=Decimal("100.00"),
            currency="INR",
            status=TransactionStatus.COMPLETED,
            timestamp=base_time - timedelta(minutes=1) - timedelta(seconds=i * 10),
        )
        db.add(tx)
    db.commit()

    engine = AnomalyService()
    result = engine.evaluate(test_context)

    assert "ANOMALOUS_HIGH_FREQUENCY" in result.flags
    assert result.details["txns_last_5min"] == 5
