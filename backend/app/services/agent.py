"""Autonomous agent service.

The agent's entire job is: understand an instruction, emit a structured
proposal. It has no code path to the bank simulator -- ``app.services.bank`` is
deliberately not imported here, and the only status this module can produce is
PROPOSED.

Pipeline
--------
1. Resolve the agent (and therefore the source account it may spend from).
2. Parse the instruction into a ``ParsedAction`` (Gemini, or the deterministic
   fallback).
3. Resolve the recipient name against known counterparties -- deterministic
   backend logic, never the model's job.
4. Persist an ActionProposal with full provenance, plus an audit entry.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AgentNotFoundError,
    InstructionParseError,
    NoSourceAccountError,
)
from app.models import (
    ActionProposal,
    Agent,
    AuditEventType,
    Counterparty,
    ProposalStatus,
)
from app.services import audit
from app.services.llm import ParserError, parse_instruction

logger = logging.getLogger(__name__)


def resolve_agent(db: Session, agent_ref: str | int) -> Agent:
    """Look up an agent by primary key or by name.

    Accepting both keeps the API usable from a terminal ("Treasury Agent")
    without giving up stable numeric identifiers.
    """
    reference = str(agent_ref).strip()

    if reference.isdigit():
        agent = db.get(Agent, int(reference))
        if agent is not None:
            return agent

    agent = db.execute(
        select(Agent).where(func.lower(Agent.name) == reference.lower())
    ).scalar_one_or_none()

    if agent is None:
        raise AgentNotFoundError(reference)
    return agent


def _normalise(name: str) -> str:
    """Casefold and strip punctuation for counterparty comparison."""
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def resolve_counterparty(db: Session, recipient: str) -> Counterparty | None:
    """Match a recipient name to a known counterparty.

    Matching is exact, then punctuation/case-insensitive exact -- and stops
    there. Fuzzy matching is deliberately not used: "ABC Technologies Ltd"
    resolving to "ABC Technologies" is precisely the typosquatting behaviour a
    payments system must not have. An unresolved recipient is a useful signal,
    not a problem to paper over.
    """
    exact = db.execute(
        select(Counterparty).where(func.lower(Counterparty.name) == recipient.lower())
    ).scalar_one_or_none()
    if exact is not None:
        return exact

    target = _normalise(recipient)
    for candidate in db.execute(select(Counterparty)).scalars():
        if _normalise(candidate.name) == target:
            return candidate
    return None


def create_proposal(
    db: Session,
    *,
    agent_ref: str | int,
    task: str,
    context: list[dict[str, Any]] | None = None,
) -> ActionProposal:
    """Turn a natural-language task into a persisted ActionProposal.

    Raises ``AgentNotFoundError``, ``NoSourceAccountError``, or
    ``InstructionParseError``. Never executes anything.
    """
    agent = resolve_agent(db, agent_ref)

    if agent.source_account_id is None:
        raise NoSourceAccountError(agent.name)

    try:
        parsed, parser_detail = parse_instruction(task)
    except ParserError as exc:
        # Both providers failed. Record the attempt -- a malformed or hostile
        # instruction is exactly what an auditor wants visibility of.
        audit.record(
            db,
            event_type=AuditEventType.PROPOSAL_REJECTED,
            actor=agent.name,
            agent_id=agent.id,
            message=exc.message,
            payload={"task": task, "provider": exc.provider},
        )
        db.commit()
        raise InstructionParseError(exc.message, provider=exc.provider) from exc

    counterparty = resolve_counterparty(db, parsed.recipient)

    proposal = ActionProposal(
        agent_id=agent.id,
        source_account_id=agent.source_account_id,
        action_type=parsed.action_type,
        amount=parsed.amount,
        currency=parsed.currency,
        recipient_name=parsed.recipient,
        recipient_account_number=(
            counterparty.account_number if counterparty else None
        ),
        purpose=parsed.purpose,
        # The untrusted surface, preserved verbatim. Phase 4's manipulation
        # engine reads this: once an instruction has been flattened into the
        # structured fields above, an injection is invisible.
        provenance={
            "user_instruction": task,
            "retrieved_context": context or [],
            "parser": parser_detail,
            "agent_objective": agent.objective,
            "recipient_resolution": {
                "extracted": parsed.recipient,
                "matched_counterparty": counterparty.name if counterparty else None,
                "known": counterparty is not None,
            },
        },
        # The only status this service can produce. Every transition beyond it
        # belongs to the AEGIS-X governance engine.
        status=ProposalStatus.PROPOSED,
    )

    db.add(proposal)
    db.flush()

    audit.record(
        db,
        event_type=AuditEventType.PROPOSAL_CREATED,
        actor=agent.name,
        agent_id=agent.id,
        entity_type="action_proposal",
        entity_id=proposal.id,
        message=(
            f"{agent.name} proposed a {parsed.action_type} of "
            f"{parsed.amount} {parsed.currency} to {parsed.recipient}."
        ),
        payload={
            "action_id": proposal.action_id,
            "amount": str(parsed.amount),
            "currency": parsed.currency,
            "recipient": parsed.recipient,
            "recipient_known": counterparty is not None,
            "purpose": parsed.purpose,
            "parser": parser_detail.get("provider"),
            "fallback_used": parser_detail.get("fallback_used", False),
            "status": ProposalStatus.PROPOSED,
        },
    )

    db.commit()
    return proposal


def get_proposal(db: Session, reference: str) -> ActionProposal | None:
    """Fetch by public action_id, or by numeric primary key."""
    proposal = db.execute(
        select(ActionProposal).where(ActionProposal.action_id == reference)
    ).scalar_one_or_none()
    if proposal is not None:
        return proposal

    if str(reference).isdigit():
        return db.get(ActionProposal, int(reference))
    return None


def list_proposals(
    db: Session,
    *,
    agent_id: int | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[ActionProposal]:
    statement = select(ActionProposal)

    if agent_id is not None:
        statement = statement.where(ActionProposal.agent_id == agent_id)
    if status is not None:
        statement = statement.where(ActionProposal.status == status)

    statement = (
        statement.order_by(ActionProposal.id.desc()).limit(limit).offset(offset)
    )
    return list(db.execute(statement).scalars())
