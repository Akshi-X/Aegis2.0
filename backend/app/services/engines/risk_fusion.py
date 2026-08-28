"""Risk fusion: combine independent engine signals into one score.

Two properties matter more than the exact weights.

**Only contributing engines count.** An engine that returned no score is
excluded and the remaining weights are renormalised. Treating "did not run" as
"found no risk" would let stub engines silently dilute real findings.

**Correlated engines share a group, combined by max rather than sum.** Financial
DNA and the Isolation Forest read overlapping features -- amount, hour,
recipient familiarity, daily totals -- so adding both into a weighted sum counts
one signal twice and systematically inflates behavioural risk. Grouping is in
place now so those engines drop in later without a rewrite.
"""

from __future__ import annotations

from app.core.policy import get_policy
from app.services.engines.base import (
    EngineResult,
    EngineStatus,
    EvaluationContext,
)


def fuse(results: dict[str, EngineResult]) -> tuple[float | None, dict]:
    """Fuse engine results into a single 0-100 score.

    Returns ``(score, detail)``. The score is None when no engine contributed.
    Pure function of its inputs, so it is unit-testable without a database.
    """
    policy = get_policy().fusion
    group_weights = policy.group_weights
    engine_group = policy.engine_groups

    group_scores: dict[str, float] = {}
    group_sources: dict[str, list[str]] = {}

    for engine_name, group in engine_group.items():
        result = results.get(engine_name)
        if result is None or not result.contributes:
            continue

        score = float(result.risk_score or 0.0)
        # max() within a group: correlated signals must not stack.
        if group not in group_scores or score > group_scores[group]:
            group_scores[group] = score
        group_sources.setdefault(group, []).append(engine_name)

    contributing = sorted(
        name
        for name in engine_group
        if (r := results.get(name)) is not None and r.contributes
    )
    missing = sorted(set(engine_group) - set(contributing))

    if not group_scores:
        return None, {
            "contributing_engines": [],
            "missing_engines": missing,
            "coverage_ratio": 0.0,
            "note": "No engine produced a score; nothing to fuse.",
        }

    active_weight = sum(group_weights[g] for g in group_scores)
    weighted = sum(group_weights[g] * score for g, score in group_scores.items())
    # Renormalise so a partially covered evaluation is not scaled down purely
    # for having fewer engines.
    fused = weighted / active_weight

    contributions = {
        group: {
            "score": round(score, 2),
            "group_weight": group_weights[group],
            "normalised_weight": round(group_weights[group] / active_weight, 4),
            "points_contributed": round(
                group_weights[group] * score / active_weight, 2
            ),
            "engines": sorted(group_sources[group]),
        }
        for group, score in sorted(
            group_scores.items(), key=lambda kv: -group_weights[kv[0]] * kv[1]
        )
    }

    detail = {
        "contributing_engines": contributing,
        "missing_engines": missing,
        "coverage_ratio": round(len(contributing) / len(engine_group), 4),
        "active_group_weight": round(active_weight, 4),
        "weight_renormalised": abs(active_weight - 1.0) > 1e-9,
        "group_contributions": contributions,
    }
    return round(fused, 2), detail


class RiskFusionService:
    """Aggregates signal-engine results. Fully implemented."""

    name = "risk_fusion"

    def evaluate(self, context: EvaluationContext) -> EngineResult:
        policy = get_policy().fusion
        score, detail = fuse(context.results)

        if score is None:
            status = EngineStatus.NOT_IMPLEMENTED
        elif score >= policy.fail_at_or_above:
            status = EngineStatus.FAIL
        elif score >= policy.warn_at_or_above:
            status = EngineStatus.WARN
        else:
            status = EngineStatus.PASS

        flags: list[str] = []
        if detail.get("weight_renormalised"):
            flags.append("PARTIAL_ENGINE_COVERAGE")

        return EngineResult(
            engine=self.name,
            status=status,
            risk_score=score,
            flags=flags,
            details=detail,
        )
