"""ActionProposal: what an agent *wants* to do.

Nothing here is executed. AEGIS-X evaluates proposals in a later phase and only
then may a transaction be created.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.enums import ActionType, ProposalStatus
from app.models.types import MoneyType, PortableJSON


def _new_action_id() -> str:
    return f"act_{uuid.uuid4().hex[:16]}"


class ActionProposal(Base):
    __tablename__ = "action_proposals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Public, non-guessable handle. Sequential integers leak volume and invite
    # enumeration, so external references use this instead.
    action_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, default=_new_action_id
    )

    agent_id: Mapped[int] = mapped_column(ForeignKey("agents.id"), index=True)

    # Resolved from the agent's authority envelope, never from the instruction:
    # an instruction must not be able to choose which account it drains.
    source_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("bank_accounts.id"), nullable=True
    )

    action_type: Mapped[str] = mapped_column(String(16), default=ActionType.TRANSFER)
    amount: Mapped[Decimal] = mapped_column(MoneyType, default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    recipient_name: Mapped[str] = mapped_column(String(160), default="")
    recipient_account_number: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    purpose: Mapped[str] = mapped_column(Text, default="")

    # The untrusted surface: the original natural-language instruction, any
    # retrieved documents the agent consumed, and its own reasoning.
    #
    # This field exists from day one deliberately. Once an instruction has been
    # flattened into the structured fields above, a successful prompt injection
    # is indistinguishable from a legitimate request -- the manipulation engine
    # can only ever detect an attack by inspecting what the agent *read*.
    provenance: Mapped[dict[str, Any]] = mapped_column(PortableJSON, default=dict)

    status: Mapped[str] = mapped_column(
        String(24), default=ProposalStatus.PROPOSED, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    agent = relationship("Agent", lazy="joined", foreign_keys=[agent_id])
    source_account = relationship("BankAccount", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ActionProposal {self.id} {self.action_type} {self.amount}>"
