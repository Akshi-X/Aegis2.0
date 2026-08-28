"""Generate synthetic historical transactions for all Agents."""

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
    """Generate historical transactions for multiple agents."""
    agents = db.scalars(select(Agent)).all()
    if not agents:
        logger.error("No agents found. Run seed.py first.")
        return False

    vendors = db.scalars(
        select(BankAccount).where(BankAccount.account_name.in_(["ABC Technologies", "XYZ Cloud"]))
    ).all()
    
    if not vendors:
        logger.error("Vendors not found. Run seed.py first.")
        return False

    # Check if already seeded
    count = db.scalar(select(func.count()).select_from(Transaction))
    if count and count > 100:
        logger.info(f"Seed skipped: {count} transactions already present.")
        return False

    now = datetime.now()
    transactions_to_add = []
    
    # Configuration for different agents to give them distinct Financial DNA profiles
    profiles = {
        "Treasury Agent": {
            "min_amt": 20000, "max_amt": 80000,
            "min_hour": 9, "max_hour": 17,
            "freq_min": 5, "freq_max": 10,
            "desc": "Vendor payment"
        },
        "Procurement Agent": {
            "min_amt": 5000, "max_amt": 150000,
            "min_hour": 10, "max_hour": 16,
            "freq_min": 2, "freq_max": 5,
            "desc": "Hardware purchase"
        },
        "Marketing Agent": {
            "min_amt": 1000, "max_amt": 8000,
            "min_hour": 7, "max_hour": 22,
            "freq_min": 10, "freq_max": 25,
            "desc": "Ad spend funding"
        },
        "HR Agent": {
            "min_amt": 100000, "max_amt": 400000,
            "min_hour": 8, "max_hour": 11, # strict morning hours
            "freq_min": 1, "freq_max": 3,
            "desc": "Payroll processing"
        }
    }

    for agent in agents:
        prof = profiles.get(agent.name)
        if not prof:
            continue
            
        source_account = db.scalar(select(BankAccount).where(BankAccount.id == agent.source_account_id))
        if not source_account:
            continue

        for day_offset in range(days):
            current_date = now - timedelta(days=days - day_offset)
            
            # Skip weekends mostly
            if current_date.weekday() >= 5 and random.random() < 0.9:
                continue
                
            num_transactions = random.randint(prof["freq_min"], prof["freq_max"])
            
            for _ in range(num_transactions):
                hour = random.randint(prof["min_hour"], prof["max_hour"])
                minute = random.randint(0, 59)
                second = random.randint(0, 59)
                tx_time = current_date.replace(hour=hour, minute=minute, second=second)
                
                amount_val = random.uniform(prof["min_amt"], prof["max_amt"])
                amount = Decimal(str(amount_val)).quantize(Decimal("0.01"))
                
                vendor = random.choice(vendors)
                
                tx = Transaction(
                    source_account_id=source_account.id,
                    destination_account_id=vendor.id,
                    amount=amount,
                    currency="INR",
                    status=TransactionStatus.COMPLETED,
                    reference=f"INV-{day_offset}-{random.randint(1000, 9999)}",
                    description=prof["desc"],
                    proposal_id=None,
                    timestamp=tx_time,
                )
                transactions_to_add.append(tx)
                
                # Update balances
                source_account.balance -= amount
                vendor.balance += amount

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
