"""Counterparty intelligence engine.

Answers a different question from the behavioural engines: not "is this unusual
*for this agent*?" but "who is being paid, and what does the money-flow network
say about them?". Two layers of evidence, combined by the same max-of-violations
rule the other signal engines use so a single strong finding is never diluted:

1. **Standing.** Is the recipient on the approved-vendor allow-list, and what is
   its stored risk score? An unresolved recipient -- an account number that maps
   to no bank account at all -- is the strongest signal here: money is leaving
   for a destination the system has never seen.

2. **Graph structure.** A directed money-flow graph is built from the ledger
   with NetworkX and the recipient's position in it is inspected: fan-in (how
   many distinct payers), fan-out (how many distinct onward destinations),
   pass-through / rapid-forwarding behaviour (funds arrive and leave again), and
   proximity to already-flagged nodes. A legitimate vendor is a pure collector
   -- high fan-in, no fan-out -- which is explicitly *not* penalised; a mule
   both collects and forwards.

The engine is read-only and defensive: missing recipient data or an empty ledger
yields a low, explained score rather than an error.
"""

from __future__ import annotations

import logging

import networkx as nx
from sqlalchemy import select

from app.core.policy import get_policy
from app.models import BankAccount, Counterparty, Transaction
from app.models.enums import TransactionStatus
from app.services.engines.base import EngineResult, EngineStatus, EvaluationContext

logger = logging.getLogger(__name__)


class CounterpartyService:
    name = "counterparty"
    planned_phase = 6
    summary = (
        "Graph analysis over the transaction network (NetworkX): fan-in, "
        "fan-out, rapid forwarding, and proximity to flagged nodes."
    )

    def evaluate(self, context: EvaluationContext) -> EngineResult:
        policy = get_policy().counterparty
        proposal = context.proposal

        # Without a destination account number there is no counterparty to
        # assess. That is a finding for the recipient-resolution engines, not
        # this one; here it is simply "nothing to score".
        if not proposal.recipient_account_number:
            return EngineResult(
                engine=self.name,
                status=EngineStatus.PASS,
                risk_score=0.0,
                flags=[],
                details={"reason": "No recipient account number to assess"},
            )

        recipient_account = context.db.execute(
            select(BankAccount).where(
                BankAccount.account_number == proposal.recipient_account_number
            )
        ).scalar_one_or_none()

        counterparty = context.counterparty
        flags: list[str] = []
        violations: list[float] = []
        details: dict = {
            "recipient_account_number": proposal.recipient_account_number,
            "recipient_name": proposal.recipient_name,
            "resolved": recipient_account is not None,
            "on_allow_list": counterparty is not None,
            "trusted": bool(counterparty.trusted) if counterparty else False,
        }

        # -- Layer 1: standing ------------------------------------------------
        if recipient_account is None:
            # Money leaving for an account the ledger has never seen.
            flags.append("UNRESOLVED_RECIPIENT")
            violations.append(policy.risk_unresolved_recipient)
        elif counterparty is None:
            # A real account, but not an approved vendor.
            flags.append("UNVERIFIED_COUNTERPARTY")
            violations.append(policy.risk_unverified_recipient)
        else:
            stored = float(counterparty.risk_score)
            details["stored_risk_score"] = round(stored, 2)
            if not counterparty.trusted:
                flags.append("UNTRUSTED_COUNTERPARTY")
                violations.append(max(policy.risk_untrusted_counterparty, stored))
            else:
                # Trusted vendor: its stored score is the floor, not a violation.
                violations.append(stored)

        # -- Layer 2: money-flow graph ---------------------------------------
        if recipient_account is not None:
            graph_flags, graph_violations, graph_detail = self._analyse_graph(
                context, recipient_account, policy
            )
            flags.extend(graph_flags)
            violations.extend(graph_violations)
            details["graph"] = graph_detail

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

    def _analyse_graph(
        self, context: EvaluationContext, recipient: BankAccount, policy
    ) -> tuple[list[str], list[float], dict]:
        """Inspect the recipient's position in the money-flow graph.

        Edges are aggregated per (source, destination) pair -- the number of
        distinct accounts is small, so the graph is tiny and cheap to rebuild
        even though the ledger has thousands of rows.
        """
        rows = context.db.execute(
            select(
                Transaction.source_account_id,
                Transaction.destination_account_id,
                Transaction.amount,
            ).where(Transaction.status == TransactionStatus.COMPLETED)
        ).all()

        graph = nx.DiGraph()
        for src, dst, amount in rows:
            value = float(amount)
            if graph.has_edge(src, dst):
                graph[src][dst]["weight"] += value
                graph[src][dst]["count"] += 1
            else:
                graph.add_edge(src, dst, weight=value, count=1)

        flags: list[str] = []
        violations: list[float] = []
        node = recipient.id

        if node not in graph:
            # A known account with no ledger history yet. Nothing structural to
            # say; standing (layer 1) already covers it.
            return flags, violations, {"in_ledger": False}

        fan_in = graph.in_degree(node)
        fan_out = graph.out_degree(node)
        received = graph.in_degree(node, weight="weight") or 0.0
        forwarded = graph.out_degree(node, weight="weight") or 0.0
        forwarding_ratio = (forwarded / received) if received > 0 else 0.0

        detail = {
            "in_ledger": True,
            "fan_in": fan_in,
            "fan_out": fan_out,
            "received_total": round(received, 2),
            "forwarded_total": round(forwarded, 2),
            "forwarding_ratio": round(forwarding_ratio, 4),
        }

        # Pass-through / collector-and-forwarder: takes money from several
        # sources and pushes it on to several destinations. A pure vendor has
        # fan_out == 0 and is deliberately untouched here.
        if fan_in >= 2 and fan_out >= policy.fan_out_mule_min:
            flags.append("PASS_THROUGH_ENTITY")
            violations.append(policy.risk_pass_through)
        elif fan_out > 0 and forwarding_ratio >= policy.forwarding_ratio_min:
            # Most of what arrives leaves again: classic layering/mule signal.
            flags.append("RAPID_FORWARDING")
            violations.append(policy.risk_rapid_forwarding)

        # Proximity: does the recipient transact with an account whose
        # counterparty record is high-risk?
        neighbours = set(graph.successors(node)) | set(graph.predecessors(node))
        neighbours.discard(node)
        if neighbours:
            flagged = self._flagged_neighbours(
                context, neighbours, policy.proximity_risk_score
            )
            if flagged:
                flags.append("PROXIMITY_TO_FLAGGED")
                violations.append(policy.risk_proximity_to_flagged)
                detail["flagged_neighbours"] = flagged

        return flags, violations, detail

    @staticmethod
    def _flagged_neighbours(
        context: EvaluationContext, neighbour_ids: set[int], proximity_risk_score: float
    ) -> list[str]:
        """Names of neighbouring accounts that are untrusted or high-risk."""
        rows = context.db.execute(
            select(BankAccount.account_number, BankAccount.account_name)
            .where(BankAccount.id.in_(neighbour_ids))
        ).all()
        by_number = {number: name for number, name in rows}
        if not by_number:
            return []

        counterparties = context.db.execute(
            select(Counterparty).where(
                Counterparty.account_number.in_(by_number.keys())
            )
        ).scalars()

        flagged: list[str] = []
        for cp in counterparties:
            if not cp.trusted or float(cp.risk_score) >= proximity_risk_score:
                flagged.append(by_number.get(cp.account_number, cp.name))
        return flagged
