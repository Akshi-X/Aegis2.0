from app.database.session import get_session_factory
from app.models import ActionProposal, Agent
from app.models.enums import ActionType, ProposalStatus
from decimal import Decimal

def seed():
    with get_session_factory()() as db:
        agent = db.query(Agent).filter_by(name="Marketing Agent").first()

        malicious_p = ActionProposal(
            agent_id=agent.id,
            action_type=ActionType.TRANSFER,
            amount=Decimal("5000000"), # 5 Million (Anomalous amount spike)
            currency="INR",
            recipient_name="Unknown Crypto Exchange", # Anomalous new recipient
            recipient_account_number="ACC-HACKED-999",
            purpose="Urgent untracked offshore payment",
            source_account_id=agent.source_account_id,
            status=ProposalStatus.PROPOSED
        )

        db.add(malicious_p)
        db.commit()
        print("Malicious Proposal seeded!")

if __name__ == "__main__":
    seed()
