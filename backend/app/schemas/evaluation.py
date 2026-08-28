"""Response contracts for the AEGIS-X evaluation pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import GovernanceDecision
from app.schemas.agent import ActionProposalRead
from app.services.engines.base import EngineResult


class CoverageReport(BaseModel):
    """How much of the pipeline actually reported.

    Surfaced on every evaluation so a low risk score is never mistaken for a
    clean bill of health while engines remain unimplemented.
    """

    engines_total: int
    engines_implemented: int
    implemented: list[str]
    not_implemented: list[str]
    errored: list[str]
    complete: bool


class RiskFactor(BaseModel):
    engine: str
    risk_score: float | None
    status: str
    flags: list[str]


class ActionEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evaluation_id: str
    proposal_id: int
    agent_id: int

    decision: GovernanceDecision
    decision_reason: str
    # True when the decision rests on incomplete evidence.
    provisional: bool

    # None when no engine produced a score -- distinct from a score of zero.
    overall_risk_score: float | None
    trust_score_at_evaluation: float | None

    engine_results: dict[str, EngineResult]
    coverage: CoverageReport
    fusion_detail: dict[str, Any] = Field(default_factory=dict)
    top_factors: list[RiskFactor] = Field(default_factory=list)

    engines_run: int
    latency_ms: float
    created_at: datetime


class EvaluationResponse(BaseModel):
    """One evaluation plus the proposal it assessed."""

    evaluation: ActionEvaluationRead
    proposal: ActionProposalRead
    # Explicit reminder that a decision is not an action.
    next_step: str = (
        "Decision recorded. AEGIS-X does not act on decisions yet; no funds "
        "have moved."
    )
