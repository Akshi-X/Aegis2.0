"""Generate synthetic historical transactions for the Treasury Agent."""

import argparse
import logging
import random
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_session_factory
from app.models import Agent, BankAccount, Transaction
from app.models.enums import TransactionStatus

logger = logging.getLogger(__name__)

def seed_historical_transactions(db: Session, days: int = 365) -> bool:
    """Generate ~5000 historical transactions."""
    agent = db.scalar(select(Agent).where(Agent.name == "Treasury Agent"))
    if not agent:
        logger.error("Treasury Agent not found. Run seed.py first.")
        return False
        
    source_account = db.scalar(select(BankAccount).where(BankAccount.id == agent.source_account_id))
    if not source_account:
        logger.error("Source account not found.")
        return False

    # Get trusted vendors
    vendors = db.scalars(
        select(BankAccount).where(BankAccount.account_name.in_(["ABC Technologies", "XYZ Cloud"]))
    ).all()
    
    if not vendors:
        logger.error("Vendors not found. Run seed.py first.")
        return False

    # Check if already seeded
    count = db.scalar(
        select(func.count()).select_from(Transaction).where(Transaction.source_account_id == source_account.id)
    )
    if count and count > 100:
        logger.info(f"Seed skipped: {count} transactions already present.")
        return False

    now = datetime.now()
    transactions_to_add = []
    
    # 5 to 10 transactions per day
    for day_offset in range(days):
        current_date = now - timedelta(days=days - day_offset)
        
        # Skip weekends mostly
        if current_date.weekday() >= 5 and random.random() < 0.9:
            continue
            
        num_transactions = random.randint(5, 10)
        
        for _ in range(num_transactions):
            # Typical hours 09:00 to 18:00
            hour = random.randint(9, 17)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            tx_time = current_date.replace(hour=hour, minute=minute, second=second)
            
            # Amount: 20000 to 80000 INR
            amount_val = random.uniform(20000, 80000)
            amount = Decimal(str(amount_val)).quantize(Decimal("0.01"))
            
            vendor = random.choice(vendors)
            
            tx = Transaction(
                source_account_id=source_account.id,
                destination_account_id=vendor.id,
                amount=amount,
                currency="INR",
                status=TransactionStatus.COMPLETED,
                reference=f"INV-{day_offset}-{random.randint(1000, 9999)}",
                description="Vendor payment",
                proposal_id=None,
                timestamp=tx_time,
            )
            transactions_to_add.append(tx)
            
            # Update balances (we do this in memory then commit)
            source_account.balance -= amount
            vendor.balance += amount

    # Sort chronologically just in case
    transactions_to_add.sort(key=lambda t: t.timestamp)
    
    db.add_all(transactions_to_add)
    db.commit()
    
    logger.info(f"Seeded {len(transactions_to_add)} historical transactions.")
    return True

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")
    parser = argparse.ArgumentParser(description="Seed historical transactions for Financial DNA.")
    parser.parse_args()
    
    session_factory = get_session_factory()
    with session_factory() as db:
        seed_historical_transactions(db)

if __name__ == "__main__":
    main()
