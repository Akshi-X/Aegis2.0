"""AEGIS-X orchestrator.

Owns the evaluation pipeline: assemble context, run every engine, fuse, decide,
persist. It knows the *order* engines run in and nothing about what any of them
does -- adding or replacing an engine is a change to the registry below, never
to this control flow or to the API.

    ActionProposal
          │
          ▼
    EvaluationContext          (agent, source account, counterparty)
          │
          ▼
    Signal engines             authority, intent, dna, anomaly,
          │                    cascade, counterparty, blast radius
          ▼
    Aggregation engines        risk fusion → trust → governance
          │
          ▼
    ActionEvaluation           persisted, immutable

Execution is deliberately *not* wired up. The orchestrator produces a decision
and records it; acting on that decision is a later phase.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ProposalNotFoundError
from app.models import (
    ActionEvaluation,
    ActionProposal,
    Agent,
    AuditEventType,
    BankAccount,
    Counterparty,
    GovernanceDecision,
    ProposalStatus,
)
from app.services import audit
from app.services.engines import (
    AnomalyService,
    AuthorityService,
    BlastRadiusService,
    CascadeService,
    CounterpartyService,
    EngineResult,
    EngineStatus,
    EvaluationContext,
    FinancialDNAService,
    GovernanceService,
    IntentService,
    RiskFusionService,
    SecurityEngine,
    TrustService,
)

logger = logging.getLogger(__name__)

# Independent risk signals. Order within this tier does not matter; they must
# not read one another's results.
SIGNAL_ENGINES: list[SecurityEngine] = [
    AuthorityService(),
    IntentService(),
    FinancialDNAService(),
    AnomalyService(),
    CascadeService(),
    CounterpartyService(),
    BlastRadiusService(),
]

# Order *does* matter here: fusion needs the signals, governance needs both the
# fused score and the trust tier.
AGGREGATION_ENGINES: list[SecurityEngine] = [
    RiskFusionService(),
    TrustService(),
    GovernanceService(),
]


class AegisOrchestrator:
    """Runs the security evaluation pipeline for one action proposal."""

    def __init__(
        self,
        signal_engines: list[SecurityEngine] | None = None,
        aggregation_engines: list[SecurityEngine] | None = None,
    ) -> None:
        # Injectable so tests can substitute engines, and so a future phase can
        # compose a different pipeline without touching this class.
        self.signal_engines = signal_engines if signal_engines is not None else SIGNAL_ENGINES
        self.aggregation_engines = (
            aggregation_engines
            if aggregation_engines is not None
            else AGGREGATION_ENGINES
        )

    # -- context ---------------------------------------------------------

    def build_context(
        self, db: Session, proposal: ActionProposal
    ) -> EvaluationContext:
        # May be None if the agent was deleted after the proposal was made.
        # That is not an error here: the Authority engine treats a missing
        # agent as a disqualifying finding, so the action is blocked rather
        # than escaping evaluation entirely.
        agent = db.get(Agent, proposal.agent_id)

        source_account = (
            db.get(BankAccount, proposal.source_account_id)
            if proposal.source_account_id is not None
            else None
        )

        counterparty = None
        if proposal.recipient_account_number:
            counterparty = db.execute(
                select(Counterparty).where(
                    Counterparty.account_number == proposal.recipient_account_number
                )
            ).scalar_one_or_none()

        return EvaluationContext(
            db=db,
            proposal=proposal,
            agent=agent,
            now=datetime.now(timezone.utc),
            source_account=source_account,
            counterparty=counterparty,
        )

    # -- engine execution -------------------------------------------------

    def _run_engine(
        self, engine: SecurityEngine, context: EvaluationContext
    ) -> EngineResult:
        """Run one engine, converting a crash into a recorded ERROR result.

        One faulty engine must not take down the evaluation. The failure is
        recorded with a null score so it is excluded from fusion rather than
        being scored as harmless.
        """
        try:
            return engine.evaluate(context)
        except Exception as exc:  # noqa: BLE001 - isolation is the point
            logger.exception("Engine %r failed during evaluation", engine.name)
            return EngineResult(
                engine=engine.name,
                status=EngineStatus.ERROR,
                risk_score=None,
                flags=["ENGINE_ERROR"],
                details={"error": str(exc), "error_type": type(exc).__name__},
            )

    def run_pipeline(self, context: EvaluationContext) -> dict[str, EngineResult]:
        for engine in self.signal_engines:
            context.results[engine.name] = self._run_engine(engine, context)

        # Aggregation engines read context.results, which is why they run in a
        # second, ordered pass.
        for engine in self.aggregation_engines:
            context.results[engine.name] = self._run_engine(engine, context)

        return context.results

    # -- public entry point ----------------------------------------------

    def evaluate(self, db: Session, proposal: ActionProposal) -> ActionEvaluation:
        """Evaluate a proposal and persist the result."""
        started = time.perf_counter()

        context = self.build_context(db, proposal)
        results = self.run_pipeline(context)

        latency_ms = (time.perf_counter() - started) * 1000

        governance = results.get("governance")
        fusion = results.get("risk_fusion")
        trust = results.get("trust")

        governance_detail = governance.details if governance else {}
        decision = governance_detail.get("decision", GovernanceDecision.ESCALATE)

        evaluation = ActionEvaluation(
            proposal_id=proposal.id,
            agent_id=proposal.agent_id,
            decision=decision,
            decision_reason=governance_detail.get("reason", ""),
            provisional=bool(governance_detail.get("provisional", False)),
            overall_risk_score=fusion.risk_score if fusion else None,
            trust_score_at_evaluation=(
                trust.details.get("trust_score") if trust else None
            ),
            engine_results={
                name: result.model_dump(mode="json")
                for name, result in results.items()
            },
            coverage=self._coverage(results),
            fusion_detail=fusion.details if fusion else {},
            top_factors=self._top_factors(results),
            engines_run=len(results),
            latency_ms=round(latency_ms, 2),
        )
        db.add(evaluation)

        # The proposal has now been assessed. It is *not* executed, blocked, or
        # approved here -- acting on a decision is a later phase.
        proposal.status = ProposalStatus.EVALUATED
        db.flush()

        audit.record(
            db,
            event_type=AuditEventType.PROPOSAL_EVALUATED,
            actor="aegis-x",
            agent_id=proposal.agent_id,
            entity_type="action_evaluation",
            entity_id=evaluation.id,
            message=(
                f"Evaluated {proposal.action_id}: {decision}. "
                f"{governance_detail.get('reason', '')}"
            ),
            payload={
                "evaluation_id": evaluation.evaluation_id,
                "action_id": proposal.action_id,
                "decision": decision,
                "provisional": evaluation.provisional,
                "overall_risk_score": evaluation.overall_risk_score,
                "engines_run": evaluation.engines_run,
                "coverage": evaluation.coverage,
                "latency_ms": evaluation.latency_ms,
            },
        )

        db.commit()
        return evaluation

    # -- reporting helpers ------------------------------------------------

    @staticmethod
    def _coverage(results: dict[str, EngineResult]) -> dict:
        """Which engines actually reported. Surfaced so a low risk score is
        never mistaken for a clean bill of health."""
        implemented = sorted(n for n, r in results.items() if r.implemented)
        placeholders = sorted(n for n, r in results.items() if not r.implemented)
        errored = sorted(
            n for n, r in results.items() if r.status is EngineStatus.ERROR
        )

        return {
            "engines_total": len(results),
            "engines_implemented": len(implemented),
            "implemented": implemented,
            "not_implemented": placeholders,
            "errored": errored,
            "complete": not placeholders and not errored,
        }

    @staticmethod
    def _top_factors(results: dict[str, EngineResult]) -> list[dict]:
        """The contributing engines that drove the score, worst first."""
        scored = [
            {
                "engine": name,
                "risk_score": result.risk_score,
                "status": result.status.value,
                "flags": result.flags,
            }
            for name, result in results.items()
            if result.contributes and (result.risk_score or 0) > 0
        ]
        return sorted(scored, key=lambda item: -(item["risk_score"] or 0))[:5]


def get_proposal_for_evaluation(db: Session, action_id: str) -> ActionProposal:
    statement = select(ActionProposal).where(ActionProposal.action_id == action_id)
    proposal = db.execute(statement).scalar_one_or_none()

    if proposal is None and str(action_id).isdigit():
        proposal = db.get(ActionProposal, int(action_id))

    if proposal is None:
        raise ProposalNotFoundError(action_id)
    return proposal


def list_evaluations(
    db: Session, *, proposal_id: int | None = None, limit: int = 100
) -> list[ActionEvaluation]:
    statement = select(ActionEvaluation)
    if proposal_id is not None:
        statement = statement.where(ActionEvaluation.proposal_id == proposal_id)
    statement = statement.order_by(ActionEvaluation.id.desc()).limit(limit)
    return list(db.execute(statement).scalars())
