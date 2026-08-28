"""Authority engine: may this agent do this, at all?

The first and most fundamental question AEGIS-X asks, and the only engine whose
answer alone can justify a refusal. Every check is deterministic and reads from
stored policy and the agent's authority envelope -- never from the instruction.
An agent cannot argue its way past its own limits.

Checks performed
----------------
1. The agent exists.
2. The agent's status is ACTIVE.
3. The action type is on the agent's allow-list.
4. The amount is within ``max_transaction_limit``.
5. Today's executed spend plus this amount is within ``daily_limit``.
6. The currency is on the agent's allow-list.
7. The source account belongs to, or is explicitly authorised for, the agent.

Balance sufficiency is checked as well: it is not an authority question, but an
unfundable action should not reach the bank regardless.

Scoring
-------
Every risk value comes from ``policy.authority.risk_scores``; none is hardcoded
here. The engine reports the **maximum** of the violations it found, never the
sum -- three simultaneous violations are not "worse than certain", and summing
would let three minor flags outrank one hard limit breach.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select

from app.core.policy import get_policy
from app.models import (
    ActionProposal,
    AgentStatus,
    Transaction,
    TransactionStatus,
)
from app.services.engines.base import (
    EngineResult,
    EngineStatus,
    EvaluationContext,
)


def _start_of_day(context: EvaluationContext) -> datetime:
    """Midnight UTC today, matched to the dialect's timezone handling.

    SQLite stores naive datetimes while PostgreSQL stores aware ones, and
    comparing across the two raises.
    """
    start = context.now.replace(hour=0, minute=0, second=0, microsecond=0)
    if context.db.get_bind().dialect.name == "sqlite":
        return start.replace(tzinfo=None)
    return start


def daily_spend(context: EvaluationContext) -> Decimal:
    """Total already executed by this agent today.

    Counts completed transactions traced back to this agent's proposals. Direct
    ``POST /bank/transfer`` calls carry no proposal and are therefore not
    attributed to any agent -- correct, since no agent initiated them.
    """
    if context.agent is None:
        return Decimal("0.00")

    statement = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .select_from(Transaction)
        .join(ActionProposal, Transaction.proposal_id == ActionProposal.id)
        .where(
            ActionProposal.agent_id == context.agent.id,
            Transaction.status == TransactionStatus.COMPLETED,
            Transaction.timestamp >= _start_of_day(context),
        )
    )
    total = context.db.execute(statement).scalar_one() or 0
    # Quantise: COALESCE returns a bare integer when there are no rows, which
    # would serialise as "0" while every other money field reads "0.00".
    return Decimal(str(total)).quantize(Decimal("0.01"))


def authorized_account_ids(agent) -> set[int]:
    """Accounts this agent may spend from.

    The primary ``source_account_id`` plus any explicitly delegated accounts.
    An allow-list, so an account absent from it is refused by default.
    """
    allowed: set[int] = set()
    if agent.source_account_id is not None:
        allowed.add(agent.source_account_id)
    for account_id in agent.authorized_account_ids or []:
        try:
            allowed.add(int(account_id))
        except (TypeError, ValueError):
            # A malformed entry must not silently widen authority.
            continue
    return allowed


class AuthorityService:
    """Identity and authority checks. Fully implemented, policy-driven."""

    name = "authority"

    def evaluate(self, context: EvaluationContext) -> EngineResult:
        policy = get_policy().authority
        risk = policy.risk_scores

        proposal = context.proposal
        agent = context.agent

        flags: list[str] = []
        violations: list[float] = []
        details: dict = {}

        # --- 1. Does the agent exist? -------------------------------------
        # A proposal referencing a deleted agent is blocked, not errored: the
        # safe outcome for an unattributable action is refusal.
        if agent is None:
            return EngineResult(
                engine=self.name,
                status=EngineStatus.FAIL,
                risk_score=risk.agent_not_found,
                flags=["AGENT_NOT_FOUND"],
                details={
                    "agent_exists": False,
                    "agent_id": proposal.agent_id,
                    "reason": (
                        "The proposal references an agent that does not exist. "
                        "No authority can be established for it."
                    ),
                },
            )

        details["agent_exists"] = True
        details["agent_id"] = agent.id

        # --- 2. Is the agent active? --------------------------------------
        details["agent_status"] = agent.status
        if agent.status != AgentStatus.ACTIVE:
            flags.append(f"AGENT_{agent.status}")
            violations.append(risk.agent_not_active)

        # --- 3. Is this action type within its mandate? -------------------
        allowed_actions = agent.allowed_actions or []
        details["allowed_actions"] = allowed_actions
        details["requested_action"] = proposal.action_type
        if proposal.action_type not in allowed_actions:
            flags.append("ACTION_TYPE_NOT_PERMITTED")
            violations.append(risk.action_type_not_permitted)

        # --- 4. Per-transaction limit -------------------------------------
        amount = Decimal(str(proposal.amount))
        limit = Decimal(str(agent.max_transaction_limit))
        details["requested_amount"] = str(amount)
        details["max_limit"] = str(limit)

        if amount > limit:
            flags.append("TRANSACTION_LIMIT_EXCEEDED")
            violations.append(risk.transaction_limit_exceeded)
            details["limit_exceeded_by"] = str(amount - limit)
            details["limit_multiple"] = float(amount / limit) if limit > 0 else None
        elif limit > 0 and amount >= limit * Decimal(
            str(policy.approaching_limit_ratio)
        ):
            flags.append("APPROACHING_TRANSACTION_LIMIT")
            violations.append(risk.approaching_transaction_limit)

        # --- 5. Daily cumulative limit ------------------------------------
        spent_today = daily_spend(context)
        daily_limit = Decimal(str(agent.daily_limit))
        projected = spent_today + amount

        details["daily_spend_before"] = str(spent_today)
        details["daily_limit"] = str(daily_limit)
        details["projected_daily_total"] = str(projected)

        if projected > daily_limit:
            flags.append("DAILY_LIMIT_EXCEEDED")
            violations.append(risk.daily_limit_exceeded)
            details["daily_limit_exceeded_by"] = str(projected - daily_limit)
        elif daily_limit > 0 and projected >= daily_limit * Decimal(
            str(policy.approaching_limit_ratio)
        ):
            flags.append("APPROACHING_DAILY_LIMIT")
            violations.append(risk.approaching_daily_limit)

        # --- 6. Currency ---------------------------------------------------
        allowed_currencies = agent.allowed_currencies or []
        details["allowed_currencies"] = allowed_currencies
        details["requested_currency"] = proposal.currency
        if proposal.currency not in allowed_currencies:
            flags.append("CURRENCY_NOT_PERMITTED")
            violations.append(risk.currency_not_permitted)

        # --- 7. Source account authorisation ------------------------------
        permitted_accounts = authorized_account_ids(agent)
        details["authorized_account_ids"] = sorted(permitted_accounts)
        details["requested_source_account_id"] = proposal.source_account_id

        if proposal.source_account_id is None:
            flags.append("SOURCE_ACCOUNT_MISSING")
            violations.append(risk.source_account_missing)
        elif proposal.source_account_id not in permitted_accounts:
            flags.append("UNAUTHORIZED_SOURCE_ACCOUNT")
            violations.append(risk.unauthorized_source_account)

        # --- Funding (not an authority question, but disqualifying) -------
        account = context.source_account
        if account is None:
            if "SOURCE_ACCOUNT_MISSING" not in flags:
                flags.append("SOURCE_ACCOUNT_MISSING")
                violations.append(risk.source_account_missing)
        else:
            balance = Decimal(str(account.balance))
            details["source_account_balance"] = str(balance)
            if balance < amount:
                flags.append("INSUFFICIENT_FUNDS")
                violations.append(risk.insufficient_funds)

        # --- Verdict --------------------------------------------------------
        risk_score = max(violations) if violations else 0.0
        details["violation_count"] = len(violations)

        if risk_score >= policy.fail_at_or_above:
            status = EngineStatus.FAIL
        elif violations:
            status = EngineStatus.WARN
        else:
            status = EngineStatus.PASS

        return EngineResult(
            engine=self.name,
            status=status,
            risk_score=risk_score,
            flags=flags,
            details=details,
        )
