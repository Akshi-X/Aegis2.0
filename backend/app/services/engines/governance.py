"""Governance: turn evidence into a decision.

Structure, which matters more than the current thresholds:

1. **Hard overrides run first.** A disqualifying finding decides the outcome on
   its own. Running these before fusion is what stops a critical signal from
   being averaged into insignificance -- an authority breach weighted at 0.25
   would otherwise contribute 25 points and sail through.
2. **Threshold rules run second**, over the fused score, modulated by the
   agent's trust tier.

Fail-safe under partial coverage
--------------------------------
While engines remain unimplemented, this service will never return EXECUTE. It
can justify refusing an action from the Authority engine alone, but it cannot
justify *authorising* one when six of nine signals are absent. Under partial
coverage a passing action is ESCALATE-ed to a human instead. The rules that
would grant EXECUTE are written and tested; they are simply gated until the
evidence exists to support them.
"""

from __future__ import annotations

from app.core.policy import get_policy
from app.models.enums import GovernanceDecision
from app.services.engines.base import (
    EngineResult,
    EngineStatus,
    EvaluationContext,
)


def _hard_overrides(results: dict[str, EngineResult]) -> list[dict]:
    """Findings severe enough to decide the outcome alone."""
    fired: list[dict] = []

    authority = results.get("authority")
    if authority is not None and authority.status is EngineStatus.FAIL:
        fired.append(
            {
                "rule": "AUTHORITY_FAILURE",
                "decision": GovernanceDecision.BLOCK,
                "reason": (
                    "The agent is not authorised to perform this action: "
                    + ", ".join(authority.flags)
                ),
                "engine": "authority",
            }
        )

    for name, result in results.items():
        if (
            result.contributes
            and result.risk_score is not None
            and result.risk_score >= get_policy().governance.hard_override_risk
            and name != "authority"
        ):
            fired.append(
                {
                    "rule": "CRITICAL_ENGINE_RISK",
                    "decision": GovernanceDecision.BLOCK,
                    "reason": f"{name} reported critical risk {result.risk_score}.",
                    "engine": name,
                }
            )

    return fired


def _threshold_decision(score: float) -> str:
    policy = get_policy().governance
    if score < policy.execute_below:
        return GovernanceDecision.EXECUTE
    if score < policy.constrain_below:
        return GovernanceDecision.CONSTRAIN
    if score < policy.delay_below:
        return GovernanceDecision.DELAY
    return GovernanceDecision.BLOCK


class GovernanceService:
    """Final decision. Implemented, but gated to fail safe while coverage is partial."""

    name = "governance"

    def evaluate(self, context: EvaluationContext) -> EngineResult:
        policy = get_policy().governance
        required_for_autonomy = set(policy.required_engines_for_autonomy)
        results = context.results
        fusion = results.get("risk_fusion")
        trust = results.get("trust")

        fused_score = fusion.risk_score if fusion is not None else None
        trust_tier = (trust.details.get("autonomy_tier") if trust else None) or "UNKNOWN"

        overrides = _hard_overrides(results)
        rules_fired = [override["rule"] for override in overrides]

        # --- 1. Hard overrides ------------------------------------------
        if overrides:
            decision = GovernanceDecision.BLOCK
            reason = overrides[0]["reason"]
            provisional = False

        else:
            reported = {
                name
                for name in required_for_autonomy
                if (r := results.get(name)) is not None and r.contributes
            }
            missing = sorted(required_for_autonomy - reported)

            # --- 2. Coverage gate ----------------------------------------
            if missing:
                # Refusing needs one engine; authorising needs all of them.
                decision = GovernanceDecision.ESCALATE
                reason = (
                    "No disqualifying finding, but "
                    f"{len(missing)} of {len(required_for_autonomy)} security "
                    "engines have not reported. AEGIS-X will not authorise an "
                    "action autonomously on partial evidence, so this is "
                    "escalated for human review."
                )
                rules_fired.append("INSUFFICIENT_ENGINE_COVERAGE")
                provisional = True

            # --- 3. Threshold rules --------------------------------------
            elif fused_score is None:
                decision = GovernanceDecision.ESCALATE
                reason = "No fused risk score available."
                rules_fired.append("NO_FUSED_SCORE")
                provisional = True
            else:
                decision = _threshold_decision(fused_score)
                rules_fired.append("RISK_THRESHOLD")
                provisional = False

                if (
                    decision == GovernanceDecision.EXECUTE
                    and trust_tier not in set(policy.autonomous_tiers)
                ):
                    decision = GovernanceDecision.CONSTRAIN
                    rules_fired.append("TRUST_TIER_DOWNGRADE")

                contributing_engines = []
                for name, result in results.items():
                    if result.status in (EngineStatus.FAIL, EngineStatus.WARN) and result.contributes:
                        if name == 'anomaly' and 'gemini_reasoning' in result.details:
                            contributing_engines.append(f"{name.capitalize()}: {result.details['gemini_reasoning']}")
                        elif name == 'intent' and 'reason' in result.details:
                            contributing_engines.append(f"{name.capitalize()}: {result.details['reason']}")
                        elif result.flags:
                            contributing_engines.append(f"{name.capitalize()} flagged: {', '.join(result.flags)}")

                reason = f"Fused risk {fused_score} with trust tier {trust_tier}."
                if decision != GovernanceDecision.EXECUTE and contributing_engines:
                    reason += " Key Factors -> " + " | ".join(contributing_engines)
        # Governance reports a decision, not a risk score of its own.
        return EngineResult(
            engine=self.name,
            status=(
                EngineStatus.FAIL
                if decision == GovernanceDecision.BLOCK
                else EngineStatus.WARN
                if decision != GovernanceDecision.EXECUTE
                else EngineStatus.PASS
            ),
            risk_score=None,
            flags=rules_fired,
            details={
                "decision": decision,
                "reason": reason,
                "provisional": provisional,
                "fused_risk_score": fused_score,
                "trust_tier": trust_tier,
                "hard_overrides": overrides,
                "rules_fired": rules_fired,
            },
        )
