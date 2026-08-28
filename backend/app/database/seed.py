"""Deterministic seed data for the simulated banking environment.

Run standalone:

    python -m app.database.seed            # idempotent: skips if already seeded
    python -m app.database.seed --reset     # drop everything and re-seed

Seeding is idempotent by design so it can run unattended on every container
start without duplicating rows.
"""

from __future__ import annotations

import argparse
import logging
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_session_factory
from app.models import (
    Agent,
    AgentStatus,
    AuditEventType,
    AuditLog,
    BankAccount,
    Counterparty,
    OwnerType,
)

logger = logging.getLogger(__name__)

MAIN_COMPANY_ACCOUNT = "ACC1000000001"

# (account_name, account_number, balance, owner_type)
ACCOUNTS: list[tuple[str, str, Decimal, OwnerType]] = [
    ("Main Company Account", MAIN_COMPANY_ACCOUNT, Decimal("500000000.00"), OwnerType.COMPANY),
    ("Procurement Budget", "ACC1000000002", Decimal("500000000.00"), OwnerType.COMPANY),
    ("Marketing Budget", "ACC1000000003", Decimal("500000000.00"), OwnerType.COMPANY),
    ("HR Budget", "ACC1000000004", Decimal("500000000.00"), OwnerType.COMPANY),
    ("ABC Technologies", "ACC2000000001", Decimal("0.00"), OwnerType.VENDOR),
    ("XYZ Cloud", "ACC2000000002", Decimal("0.00"), OwnerType.VENDOR),
    ("Unknown Account", "ACC9000000001", Decimal("0.00"), OwnerType.EXTERNAL),
]

# (name, account_number, trusted, risk_score)
COUNTERPARTIES: list[tuple[str, str, bool, Decimal]] = [
    ("ABC Technologies", "ACC2000000001", True, Decimal("10.00")),
    ("XYZ Cloud", "ACC2000000002", True, Decimal("15.00")),
    ("Unknown Account", "ACC9000000001", False, Decimal("85.00")),
]


def _already_seeded(db: Session) -> bool:
    count = db.execute(select(func.count()).select_from(BankAccount)).scalar_one()
    return count > 0


def seed_database(*, force: bool = False) -> bool:
    """Populate the simulated bank. Returns True if rows were written."""
    session_factory = get_session_factory()

    with session_factory() as db:
        if _already_seeded(db) and not force:
            logger.info("Seed skipped: bank accounts already present")
            return False

        accounts: dict[str, BankAccount] = {}
        for account_name, account_number, balance, owner_type in ACCOUNTS:
            account = BankAccount(
                account_name=account_name,
                account_number=account_number,
                balance=balance,
                currency="INR",
                owner_type=owner_type,
            )
            db.add(account)
            accounts[account_number] = account

        # Flush so counterparties can reference account numbers that now exist,
        # and so the agent can be given a real source_account_id.
        db.flush()

        for name, account_number, trusted, risk_score in COUNTERPARTIES:
            db.add(
                Counterparty(
                    name=name,
                    account_number=account_number,
                    trusted=trusted,
                    risk_score=risk_score,
                )
            )

        treasury_agent = Agent(
            name="Treasury Agent",
            description=(
                "Autonomous treasury agent responsible for settling approved "
                "vendor invoices from the main company account."
            ),
            objective="Pay legitimate company vendor invoices.",
            status=AgentStatus.ACTIVE,
            max_transaction_limit=Decimal("100000.00"),
            daily_limit=Decimal("500000.00"),
            allowed_actions=["TRANSFER"],
            allowed_currencies=["INR"],
            # No delegated accounts: the agent may spend only from its own.
            authorized_account_ids=[],
            trust_score=Decimal("85.00"),
            source_account_id=accounts[MAIN_COMPANY_ACCOUNT].id,
        )
        
        procurement_agent = Agent(
            name="Procurement Agent",
            description="Purchases hardware and software supplies for internal teams.",
            objective="Purchase hardware and software supplies.",
            status=AgentStatus.ACTIVE,
            max_transaction_limit=Decimal("200000.00"),
            daily_limit=Decimal("1000000.00"),
            allowed_actions=["TRANSFER"],
            allowed_currencies=["INR", "USD"],
            authorized_account_ids=[],
            trust_score=Decimal("75.00"),
            source_account_id=accounts["ACC1000000002"].id,
        )

        marketing_agent = Agent(
            name="Marketing Agent",
            description="Manages digital ad spend across platforms.",
            objective="Fund digital advertising campaigns.",
            status=AgentStatus.ACTIVE,
            max_transaction_limit=Decimal("10000.00"),
            daily_limit=Decimal("50000.00"),
            allowed_actions=["TRANSFER"],
            allowed_currencies=["INR", "USD"],
            authorized_account_ids=[],
            trust_score=Decimal("60.00"),
            source_account_id=accounts["ACC1000000003"].id,
        )

        hr_agent = Agent(
            name="HR Agent",
            description="Manages employee reimbursements and payroll funding.",
            objective="Process employee reimbursements and payroll.",
            status=AgentStatus.ACTIVE,
            max_transaction_limit=Decimal("500000.00"),
            daily_limit=Decimal("2000000.00"),
            allowed_actions=["TRANSFER"],
            allowed_currencies=["INR"],
            authorized_account_ids=[],
            trust_score=Decimal("95.00"),
            source_account_id=accounts["ACC1000000004"].id,
        )

        db.add_all([treasury_agent, procurement_agent, marketing_agent, hr_agent])

        db.add(
            AuditLog(
                event_type=AuditEventType.SEED_APPLIED,
                actor="seed",
                message="Simulated banking environment seeded.",
                payload={
                    "accounts": len(ACCOUNTS),
                    "counterparties": len(COUNTERPARTIES),
                    "agents": 4,
                },
            )
        )

        db.commit()
        logger.info(
            "Seeded %d accounts, %d counterparties, 4 agents",
            len(ACCOUNTS),
            len(COUNTERPARTIES),
        )
        return True


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")

    parser = argparse.ArgumentParser(description="Seed the AEGIS-X bank simulator.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all tables and re-create them before seeding (destructive).",
    )
    args = parser.parse_args()

    from app.database.init_db import create_tables, drop_tables

    if args.reset:
        drop_tables()
    create_tables()

    written = seed_database(force=args.reset)
    print("Seed data written." if written else "Already seeded; nothing to do.")


if __name__ == "__main__":
    main()
