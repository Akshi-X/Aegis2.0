"""Tests for the Financial DNA engine."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.models import Agent, BankAccount, Transaction, ActionProposal
from app.models.enums import TransactionStatus, ActionType, ProposalStatus
from app.services.engines.financial_dna import FinancialDNAService
from app.services.engines.base import EvaluationContext

def setup_historical_data(db: Session, agent: Agent, vendor: BankAccount):
    """Insert controlled historical transactions for predictable test outcomes."""
    amounts = [40000, 45000, 50000, 55000, 60000]
    hours = [10, 11, 12, 13, 14]
    base_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    
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
        amount=Decimal("50000.00"),
        currency="INR",
        recipient_name="ABC Technologies",
        recipient_account_number=vendor.account_number,
        purpose="Vendor payment",
        source_account_id=agent.source_account_id,
        status=ProposalStatus.PROPOSED,
    )
    
    return EvaluationContext(
        db=db,
        proposal=proposal,
        agent=agent,
        source_account=agent.source_account,
        now=datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc) # 12:00 PM is normal
    )

def test_financial_dna_normal_transaction(test_context: EvaluationContext):
    engine = FinancialDNAService()
    result = engine.evaluate(test_context)
    
    assert result.status == "PASS"
    assert result.risk_score == 0.0
    assert not result.flags

def test_financial_dna_large_transaction(test_context: EvaluationContext):
    test_context.proposal.amount = Decimal("90000.00") # Normal range max is ~65811
    engine = FinancialDNAService()
    result = engine.evaluate(test_context)
    
    assert result.status == "WARN" or result.status == "FAIL"
    assert "AMOUNT_OUTSIDE_NORMAL_RANGE" in result.flags
    assert result.risk_score >= 50.0

def test_financial_dna_unusual_time(test_context: EvaluationContext):
    # Change current time to 2 AM
    test_context.now = test_context.now.replace(hour=2)
    engine = FinancialDNAService()
    result = engine.evaluate(test_context)
    
    assert result.status == "WARN" or result.status == "FAIL"
    assert "UNUSUAL_TRANSACTION_TIME" in result.flags
    assert result.risk_score >= 50.0

def test_financial_dna_unknown_recipient(test_context: EvaluationContext):
    # Completely unknown recipient
    test_context.proposal.recipient_name = "Unknown Hacker"
    test_context.proposal.recipient_account_number = None
    engine = FinancialDNAService()
    result = engine.evaluate(test_context)
    
    assert result.status == "FAIL"
    assert "UNKNOWN_RECIPIENT" in result.flags
    assert result.risk_score >= 80.0

def test_financial_dna_multiple_anomalies(test_context: EvaluationContext):
    # Large transaction + 2 AM
    test_context.proposal.amount = Decimal("150000.00")
    test_context.now = test_context.now.replace(hour=2)
    
    engine = FinancialDNAService()
    result = engine.evaluate(test_context)
    
    assert "AMOUNT_OUTSIDE_NORMAL_RANGE" in result.flags
    assert "UNUSUAL_TRANSACTION_TIME" in result.flags
    assert result.risk_score > 60.0

def test_financial_dna_api_endpoint(client, agent, db, vendor):
    setup_historical_data(db, agent, vendor)
    
    response = client.get(f"/agent/{agent.id}/financial-dna")
    assert response.status_code == 200
    
    data = response.json()
    assert data["agent_id"] == agent.id
    assert len(data["known_recipients"]) == 1
    assert data["known_recipients"][0] == "ABC Technologies"
    
    min_amt, max_amt = data["normal_amount_range"]
    assert min_amt > 30000 and max_amt < 70000
