"""Cascade and sequence engine.

The behavioural and counterparty engines each judge a payment in isolation. This
one judges it *in sequence*: a transfer that is unremarkable on its own can be
the fifth in a burst, or one slice of an amount deliberately split to stay under
a limit. It reads the agent's recent ledger activity around ``context.now`` and
looks for four sequence signatures:

* **Rapid repeats** -- many transfers inside a short window.
* **Structuring / splitting** -- several transfers each sitting just under the
  agent's per-transaction limit, together far exceeding it (smurfing).
* **Velocity spike** -- the agent's recent throughput jumps well above the
  baseline throughput learned from its own history.
* **Coordinated cascade** -- several *distinct* source accounts funnelling into
  the same recipient within a short window (a multi-agent movement).

Findings combine by max(), like the other signal engines, so one strong pattern
is never averaged away by quieter ones. A single ordinary proposal against a
quiet ledger scores ~0, which is the correct answer: one action is not a
cascade.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.policy import get_policy
from app.models import Transaction
from app.models.enums import TransactionStatus
from app.services.engines.base import EngineResult, EngineStatus, EvaluationContext

logger = logging.getLogger(__name__)


def _as_utc(ts: datetime) -> datetime:
    """Coerce a ledger timestamp to timezone-aware UTC.

    PostgreSQL (the real target) returns aware datetimes; SQLite returns naive
    ones. Normalising here lets the engine compare against ``context.now``
    without caring which backend produced the row.
    """
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=timezone.utc)


class CascadeService:
    name = "cascade"
    planned_phase = 6
    summary = (
        "Detects suspicious action sequences: transaction splitting, rapid "
        "repeated transfers, sudden velocity changes, and multi-agent coordination."
    )

    def evaluate(self, context: EvaluationContext) -> EngineResult:
        if not context.agent or not context.agent.source_account_id:
            return EngineResult(
                engine=self.name,
                status=EngineStatus.PASS,
                risk_score=0.0,
                flags=[],
                details={"reason": "No agent/source account to sequence"},
            )

        policy = get_policy().cascade
        source_id = context.agent.source_account_id
        now = context.now
        proposal_amount = float(context.proposal.amount)

        # Recent outgoing transfers by this agent, most recent first. The
        # velocity window covers every sub-window we inspect.
        recent = context.db.execute(
            select(Transaction.amount, Transaction.timestamp)
            .where(
                Transaction.source_account_id == source_id,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.timestamp
                >= now - timedelta(minutes=policy.velocity_window_minutes),
                Transaction.timestamp <= now,
            )
            .order_by(Transaction.timestamp.desc())
        ).all()
        recent = [(amount, _as_utc(ts)) for amount, ts in recent]

        flags: list[str] = []
        violations: list[float] = []
        details: dict = {
            "proposal_amount": proposal_amount,
            "recent_events_1h": len(recent),
        }

        self._check_rapid_repeats(policy, now, recent, flags, violations, details)
        self._check_structuring(policy, context, proposal_amount, now, recent, flags, violations, details)
        self._check_velocity(policy, context, source_id, now, recent, flags, violations, details)
        self._check_coordination(policy, context, now, flags, violations, details)

        risk_score = round(max(violations), 2) if violations else 0.0

        if risk_score >= policy.fail_at_or_above:
            status = EngineStatus.FAIL
        elif risk_score >= policy.warn_at_or_above:
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

    def _check_rapid_repeats(self, policy, now, recent, flags, violations, details) -> None:
        window_start = now - timedelta(minutes=policy.burst_window_minutes)
        in_burst = [ts for _, ts in recent if ts >= window_start]
        # +1 for the proposal currently being evaluated.
        burst_count = len(in_burst) + 1
        details["burst_count"] = burst_count
        if burst_count >= policy.rapid_repeat_count:
            flags.append("RAPID_REPEATED_TRANSFERS")
            violations.append(policy.risk_rapid_repeats)

    def _check_structuring(
        self, policy, context, proposal_amount, now, recent, flags, violations, details
    ) -> None:
        limit = float(context.agent.max_transaction_limit or 0)
        if limit <= 0:
            return

        lower = policy.structuring_lower_ratio * limit
        window_start = now - timedelta(minutes=policy.burst_window_minutes)
        # Slices in the burst window that sit just under the per-transaction
        # limit, including the current proposal.
        slices = [
            amt for amt, ts in recent
            if ts >= window_start and lower <= float(amt) <= limit
        ]
        if lower <= proposal_amount <= limit:
            slices.append(proposal_amount)

        total = sum(float(a) for a in slices)
        details["structuring_slices"] = len(slices)
        if len(slices) >= policy.structuring_min_slices and total > limit:
            flags.append("TRANSACTION_STRUCTURING")
            violations.append(policy.risk_structuring)

    def _check_velocity(
        self, policy, context, source_id, now, recent, flags, violations, details
    ) -> None:
        recent_count = len(recent)
        if recent_count < policy.velocity_min_events:
            return

        # Baseline: the agent's mean events per hour over its whole history,
        # derived from total volume spread across the active span.
        span = context.db.execute(
            select(
                func.count(Transaction.id),
                func.min(Transaction.timestamp),
                func.max(Transaction.timestamp),
            ).where(
                Transaction.source_account_id == source_id,
                Transaction.status == TransactionStatus.COMPLETED,
            )
        ).one()
        total_count, first_ts, last_ts = span
        if not total_count or first_ts is None or last_ts is None:
            return

        hours = max((last_ts - first_ts).total_seconds() / 3600.0, 1.0)
        baseline_per_hour = total_count / hours
        details["baseline_per_hour"] = round(baseline_per_hour, 3)
        details["recent_per_hour"] = recent_count  # window is exactly one hour

        if baseline_per_hour > 0 and recent_count >= policy.velocity_spike_factor * baseline_per_hour:
            flags.append("VELOCITY_SPIKE")
            violations.append(policy.risk_velocity_spike)

    def _check_coordination(self, policy, context, now, flags, violations, details) -> None:
        recipient_number = context.proposal.recipient_account_number
        if not recipient_number:
            return

        from app.models import BankAccount

        recipient_id = context.db.execute(
            select(BankAccount.id).where(
                BankAccount.account_number == recipient_number
            )
        ).scalar_one_or_none()
        if recipient_id is None:
            return

        window_start = now - timedelta(minutes=policy.coordination_window_minutes)
        # Distinct sources feeding this recipient in the window, excluding this
        # agent so it is not counted twice when it adds its own proposal below.
        other_sources = context.db.execute(
            select(func.count(func.distinct(Transaction.source_account_id)))
            .where(
                Transaction.destination_account_id == recipient_id,
                Transaction.source_account_id != context.agent.source_account_id,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.timestamp >= window_start,
                Transaction.timestamp <= now,
            )
        ).scalar_one()

        # Other distinct sources plus this agent (the current proposal).
        total_sources = other_sources + 1
        details["coordination_sources"] = total_sources
        if total_sources >= policy.coordination_min_sources:
            flags.append("COORDINATED_CASCADE")
            violations.append(policy.risk_coordinated_cascade)
