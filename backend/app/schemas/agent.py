"""Request/response contracts for the autonomous agent."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.enums import ActionType, ProposalStatus


class FinancialDNAProfile(BaseModel):
    agent_id: int
    normal_amount_range: tuple[float, float]
    normal_hours: tuple[int, int]
    known_recipients: list[str]
    typical_daily_transactions: int
    typical_daily_exposure: float
    last_updated: datetime


class AgentTaskRequest(BaseModel):
    # Accepts the numeric id or the agent's name, so the endpoint is usable
    # from a terminal without looking up a primary key first.
    agent_id: int | str = Field(examples=[1, "Treasury Agent"])
    task: str = Field(
        min_length=1,
        max_length=2000,
        examples=["Pay ₹50,000 to ABC Technologies for invoice INV-204"],
    )
    # Untrusted material the agent consumed (email bodies, invoice text).
    # Stored in provenance; Phase 4's manipulation engine is what reads it.
    context: list[dict[str, Any]] | None = Field(default=None)


class SourceAccountRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_number: str
    account_name: str


class ActionProposalRead(BaseModel):
    """A proposal as returned by the API.

    ``status`` is always PROPOSED here. Nothing in the agent service can emit
    any other value.
    """

    model_config = ConfigDict(from_attributes=True)

    action_id: str
    agent_id: int
    action_type: ActionType
    amount: Decimal
    currency: str
    recipient: str = Field(validation_alias="recipient_name")
    # None when the recipient matched no known counterparty.
    recipient_account_number: str | None
    purpose: str
    source_account: SourceAccountRef | None
    status: ProposalStatus
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def recipient_known(self) -> bool:
        """Whether the payee resolved to a registered counterparty.

        A resolution fact, not a risk verdict -- scoring belongs to AEGIS-X.
        """
        return self.recipient_account_number is not None


class AgentTaskResponse(BaseModel):
    """The proposal, plus how it was produced.

    ``parser`` and ``fallback_used`` are surfaced so a demo can show the system
    still working when Gemini is unavailable.
    """

    proposal: ActionProposalRead
    parser: str
    fallback_used: bool
    # Reminder in the payload itself that nothing has been evaluated yet.
    next_step: str = "Awaiting AEGIS-X evaluation. No funds have moved."
