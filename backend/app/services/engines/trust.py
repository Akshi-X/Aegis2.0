"""Dynamic trust: how much autonomy has this agent earned?

Read-only in this phase. It reports the agent's stored trust score and the
autonomy tier that follows from it; adjusting trust in response to outcomes,
and recording that history, lands with the governance state machine.

Trust deliberately returns **no risk score**. Feeding trust into the risk sum
would double-count it, because governance already consults trust when choosing
thresholds -- and a self-reinforcing loop (a block lowers trust, low trust
raises risk, high risk causes a block) can drive an agent into permanent
suspension after a handful of false positives.
"""

from __future__ import annotations

from app.core.policy import get_policy
from app.services.engines.base import (
    EngineResult,
    EngineStatus,
    EvaluationContext,
)


def autonomy_tier(trust_score: float) -> str:
    """Resolve a trust score to an autonomy tier using the active policy."""
    return get_policy().trust.tier_for(trust_score)


class TrustService:
    """Reports current trust. Adjustment arrives in a later phase."""

    name = "trust"

    def evaluate(self, context: EvaluationContext) -> EngineResult:
        if context.agent is None:
            # No agent, no trust. Authority reports the actual failure.
            return EngineResult(
                engine=self.name,
                status=EngineStatus.FAIL,
                risk_score=None,
                flags=["AGENT_NOT_FOUND"],
                details={"trust_score": None, "autonomy_tier": "UNKNOWN"},
            )

        trust_score = float(context.agent.trust_score or 0.0)
        tier = autonomy_tier(trust_score)

        return EngineResult(
            engine=self.name,
            status=EngineStatus.PASS,
            # Intentionally None: trust modulates governance thresholds, it is
            # not itself a risk signal to be summed.
            risk_score=None,
            flags=[] if tier != "SUSPENDED" else ["AGENT_TRUST_SUSPENDED"],
            details={
                "trust_score": trust_score,
                "autonomy_tier": tier,
                "adjustment_enabled": False,
                "note": (
                    "Read-only. Trust influences decision thresholds rather "
                    "than contributing to the risk score."
                ),
            },
        )
