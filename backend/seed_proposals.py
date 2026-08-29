from app.database.session import get_session_factory
from app.models import ActionProposal, Agent, BankAccount
from app.models.enums import ActionType, ProposalStatus
from decimal import Decimal

def seed():
    with get_session_factory()() as db:
        agent1 = db.query(Agent).filter_by(name="Treasury Agent").first()
        agent3 = db.query(Agent).filter_by(name="Marketing Agent").first()
        agent4 = db.query(Agent).filter_by(name="HR Agent").first()

        p1 = ActionProposal(
            agent_id=agent1.id,
            action_type=ActionType.TRANSFER,
            amount=Decimal("50000"),
            currency="INR",
            recipient_name="ABC Technologies",
            recipient_account_number="ACC-12345",
            purpose="Pay invoice INV-204 for cloud hosting",
            source_account_id=agent1.source_account_id,
            status=ProposalStatus.PROPOSED
        )

        p2 = ActionProposal(
            agent_id=agent3.id,
            action_type=ActionType.TRANSFER,
            amount=Decimal("2500"),
            currency="INR",
            recipient_name="Google Ads",
            recipient_account_number="ACC-99999",
            purpose="Fund Q4 marketing campaign",
            source_account_id=agent3.source_account_id,
            status=ProposalStatus.PROPOSED
        )

        p3 = ActionProposal(
            agent_id=agent4.id,
            action_type=ActionType.TRANSFER,
            amount=Decimal("250000"),
            currency="INR",
            recipient_name="Global Payroll Partners",
            recipient_account_number="ACC-55555",
            purpose="Process September 2026 payroll",
            source_account_id=agent4.source_account_id,
            status=ProposalStatus.PROPOSED
        )

        db.add_all([p1, p2, p3])
        db.commit()
        print("Proposals seeded!")

if __name__ == "__main__":
    seed()
