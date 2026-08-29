"""Blast radius engine.

Every other signal engine asks "how *likely* is this action to be bad?". This
one asks the orthogonal question: "if it *is* bad, how much damage is done?".
Impact, not probability.

Damage is estimated from two exposures and one modifier:

* **Balance exposure** -- the amount as a fraction of the source account's
  balance. Draining a large share of the account is high blast.
* **Authority exposure** -- the amount as a multiple of the agent's daily
  spending authority. A single action worth many days of authority is high
  blast even if the account is deep.

The larger exposure sets the magnitude, which is then scaled by
**recoverability**: money sent to a trusted vendor is likely clawed back
(dampened), while money sent to an account that resolves to nothing is gone
(amplified). Thresholds and multipliers all live in policy.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.core.policy import get_policy
from app.models import BankAccount, Transaction
from app.models.enums import TransactionStatus
from app.services.engines.base import EngineResult, EngineStatus, EvaluationContext

logger = logging.getLogger(__name__)


class BlastRadiusService:
    name = "blast_radius"
    planned_phase = 6
    summary = (
        "Estimates the damage if this action is wrong or malicious, from "
        "amount, account balance, remaining authority, and counterparty risk."
    )

    def evaluate(self, context: EvaluationContext) -> EngineResult:
        policy = get_policy().blast_radius
        proposal = context.proposal
        agent = context.agent
        amount = float(proposal.amount)

        if amount <= 0:
            return EngineResult(
                engine=self.name,
                status=EngineStatus.PASS,
                risk_score=0.0,
                flags=[],
                details={"reason": "Non-positive amount carries no exposure"},
            )

        # -- Exposure 1: fraction of the source account balance ---------------
        balance = float(context.source_account.balance) if context.source_account else 0.0
        # A missing/empty balance cannot dampen the score: treat as fully exposed.
        balance_fraction = amount / balance if balance > 0 else 1.0

        # -- Exposure 2: multiple of the daily spending authority -------------
        daily_limit = float(agent.daily_limit) if agent and agent.daily_limit else 0.0
        authority_fraction = amount / daily_limit if daily_limit > 0 else 1.0

        # Remaining authority today, for explainability and a flag.
        spent_today = self._spent_today(context)
        remaining_daily = max(daily_limit - spent_today, 0.0)

        # Magnitude: the larger exposure, normalised to 0-100 against the level
        # policy calls "maximal".
        balance_magnitude = min(1.0, balance_fraction / policy.balance_fraction_fail) * 100
        authority_magnitude = min(1.0, authority_fraction / policy.authority_fraction_fail) * 100
        magnitude = max(balance_magnitude, authority_magnitude)

        # -- Modifier: recoverability of the destination ----------------------
        factor, recoverability = self._recoverability(context, policy)

        blast_score = round(min(100.0, magnitude * factor), 2)

        flags: list[str] = []
        if balance_fraction >= policy.balance_fraction_fail:
            flags.append("HIGH_BALANCE_EXPOSURE")
        if authority_fraction >= policy.authority_fraction_fail:
            flags.append("EXCEEDS_DAILY_AUTHORITY")
        if daily_limit > 0 and amount > remaining_daily:
            flags.append("EXHAUSTS_REMAINING_AUTHORITY")
        if recoverability in ("unresolved", "untrusted"):
            flags.append("UNRECOVERABLE_DESTINATION")

        if blast_score >= policy.fail_at_or_above:
            status = EngineStatus.FAIL
            flags.append("CRITICAL_BLAST_RADIUS")
        elif blast_score >= policy.warn_at_or_above:
            status = EngineStatus.WARN
        else:
            status = EngineStatus.PASS

        details = {
            "amount": amount,
            "source_balance": round(balance, 2),
            "balance_fraction": round(balance_fraction, 4),
            "daily_limit": round(daily_limit, 2),
            "authority_fraction": round(authority_fraction, 4),
            "spent_today": round(spent_today, 2),
            "remaining_daily_authority": round(remaining_daily, 2),
            "magnitude": round(magnitude, 2),
            "recoverability": recoverability,
            "recoverability_factor": factor,
            "blast_score": blast_score,
        }

        return EngineResult(
            engine=self.name,
            status=status,
            risk_score=blast_score,
            flags=flags,
            details=details,
        )

    def _spent_today(self, context: EvaluationContext) -> float:
        """Total moved out of the source account since midnight (UTC)."""
        if not context.agent or not context.agent.source_account_id:
            return 0.0
        day_start = context.now.replace(hour=0, minute=0, second=0, microsecond=0)
        total = context.db.scalar(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.source_account_id == context.agent.source_account_id,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.timestamp >= day_start,
                Transaction.timestamp <= context.now,
            )
        )
        return float(total or 0.0)

    @staticmethod
    def _recoverability(context: EvaluationContext, policy) -> tuple[float, str]:
        """Classify how likely the funds are to be recovered, and the multiplier."""
        number = context.proposal.recipient_account_number
        counterparty = context.counterparty

        if counterparty is not None:
            if counterparty.trusted:
                return policy.recoverable_factor, "recoverable"
            return policy.untrusted_factor, "untrusted"

        # No allow-list entry: does the account exist at all?
        resolved = False
        if number:
            resolved = (
                context.db.execute(
                    select(BankAccount.id).where(BankAccount.account_number == number)
                ).scalar_one_or_none()
                is not None
            )

        if resolved:
            return policy.unverified_factor, "unverified"
        return policy.unresolved_factor, "unresolved"
